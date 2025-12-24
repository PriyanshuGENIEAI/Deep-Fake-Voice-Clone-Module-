import os
import re
import wave
import tempfile
import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS
import hashlib

# Prefer safe MPS CPU fallback rather than erroring
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

# Device detection (Mac with M1/M2/M3/M4 preferred)
device = "mps" if torch.backends.mps.is_available() else "cpu"
map_location = torch.device(device)

# Low-compute defaults
try:
    torch.set_num_threads(1)
except Exception:
    pass
try:
    torch.set_num_interop_threads(1)
except Exception:
    pass
try:
    torch.set_float32_matmul_precision("high")
except Exception:
    pass

# Ensure loaded weights map to the selected device
torch_load_original = torch.load

def patched_torch_load(*args, **kwargs):
    if "map_location" not in kwargs:
        kwargs["map_location"] = map_location
    return torch_load_original(*args, **kwargs)

torch.load = patched_torch_load


def split_text_chunks(s: str, max_len: int = 250, min_len: int = 20):
    chunks = []
    buf = ""
    for part in re.split(r"([.!?,;:])", s):
        if not part:
            continue
        buf += part
        if part in ".!?,;:":
            if buf.strip():
                chunks.append(buf.strip())
                buf = ""
        elif len(buf) >= max_len:
            chunks.append(buf.strip())
            buf = ""
    if buf.strip():
        chunks.append(buf.strip())
    # merge too-short chunks to reduce overhead and improve continuity
    merged = []
    for ch in chunks:
        if merged and len(ch) < min_len:
            merged[-1] = (merged[-1] + " " + ch).strip()
        else:
            merged.append(ch)
    return merged


def trim_prompt(path: str, seconds: float | None, target_sr: int | None = None):
    if not path or not os.path.exists(path) or not seconds or seconds <= 0:
        return path
    try:
        st = os.stat(path)
        cache_key = f"{os.path.abspath(path)}|{st.st_mtime_ns}|{seconds}|{target_sr}|v3"
        hexkey = hashlib.sha1(cache_key.encode()).hexdigest()
        cache_path = os.path.join(tempfile.gettempdir(), f"chatterbox_promptcache_{hexkey}.wav")
        if os.path.exists(cache_path):
            return cache_path
    except Exception:
        cache_path = None
    wav, sr = ta.load(path)
    if wav.dim() == 2 and wav.size(0) > 1:
        wav = wav.mean(dim=0, keepdim=True)
    if target_sr and target_sr > 0 and target_sr != sr:
        wav = ta.functional.resample(wav, sr, target_sr)
        sr = target_sr
    max_frames = int(sr * seconds)
    try:
        from torchaudio import sox_effects as sox
        effects = [
            ["highpass", "60"],
            ["lowpass", "12000"],
            ["equalizer", "7000", "1.0q", "-6"],
        ]
        wav, sr = sox.apply_effects_tensor(wav, sr, effects)
    except Exception:
        pass
    if wav.size(1) > max_frames:
        hop = max(1, int(sr * 0.01))
        win = max_frames
        best_e = None
        best_i = 0
        for i in range(0, wav.size(1) - win + 1, hop):
            seg = wav[:, i:i+win]
            e = float(seg.square().mean())
            if best_e is None or e > best_e:
                best_e = e
                best_i = i
        wav = wav[:, best_i:best_i+win]
    # simple energy-based trim of leading/trailing silence
    frame_len = max(1, int(sr * 0.02))
    hop = max(1, int(sr * 0.01))
    energies = []
    for i in range(0, wav.size(1) - frame_len + 1, hop):
        frame = wav[0, i:i+frame_len]
        energies.append(float((frame.square().mean() + 1e-9).log10()))
    if energies:
        mx = max(energies)
        thr = mx - 1.5  # approx -15 dB from peak energy
        start_idx = 0
        for j, e in enumerate(energies):
            if e >= thr:
                start_idx = j * hop
                break
        end_idx = wav.size(1)
        for j in range(len(energies)-1, -1, -1):
            if energies[j] >= thr:
                end_idx = min(end_idx, j * hop + frame_len)
                break
        wav = wav[:, start_idx:end_idx]
    # peak normalize to -1 dBFS
    peak = float(wav.abs().max()) if wav.numel() > 0 else 0.0
    if peak > 0:
        wav = wav / peak * 10**(-1/20)
    if cache_path:
        ta.save(cache_path, wav, sr)
        return cache_path
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    ta.save(tmp.name, wav, sr)
    return tmp.name


def write_streaming_wav(output_path: str, sr: int):
    wf = wave.open(output_path, "wb")
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sr)
    return wf


def tensor_to_pcm16_bytes(x: torch.Tensor) -> bytes:
    if x is None:
        return b""
    # Expect shape (1, T) or (T,) or (C, T)
    if x.dim() == 2:
        if x.size(0) == 1:
            x = x.squeeze(0)
        else:
            x = x.mean(dim=0)
    x = torch.clamp(x, -1.0, 1.0)
    return (x * 32767.0).to(torch.int16).cpu().numpy().tobytes()

def ensure_mono_1xT(x: torch.Tensor) -> torch.Tensor:
    if x is None:
        return x
    if x.dim() == 1:
        x = x.unsqueeze(0)
    if x.dim() == 2 and x.size(0) > 1:
        x = x.mean(dim=0, keepdim=True)
    return x

def postprocess_output(path: str, target_sr: int):
    try:
        wav, sr = ta.load(path)
        if wav.dim() == 2 and wav.size(0) > 1:
            wav = wav.mean(dim=0, keepdim=True)
        if sr != target_sr:
            wav = ta.functional.resample(wav, sr, target_sr)
            sr = target_sr
        try:
            from torchaudio import sox_effects as sox
            effects = [
                ["gain", "-n"],
                ["compand", "0.02,0.10", "-60,-40,-20,-10,0,-5", "-8", "-7", "0.02"],
                ["highpass", "60"],
                ["lowpass", "11060"],
                ["equalizer", "7000", "1.0q", "-4"],
            ]
            wav, sr = sox.apply_effects_tensor(wav, sr, effects)
        except Exception:
            peak = float(wav.abs().max()) if wav.numel() > 0 else 0.0
            if peak > 0:
                wav = wav / peak * 10**(-1/20)
        ta.save(path, wav, sr)
    except Exception:
        pass


def main():
    model = ChatterboxTTS.from_pretrained(device=device)
    # Try lighter dtype on MPS for speed (safe fallback on failure)
    if device == "mps":
        try:
            model = model.to(dtype=torch.float16)
        except Exception:
            pass

    text = "hi I m Voice clone Module Devlped by Priyanshu tiwari."
    audio_prompt_path = "Waveroom Online Record Thu Dec 25 2025 2_40_50 microphone.wav"

    output_path = "test-2.wav"
    streaming = True
    fast_mode = True  # set True for lowest latency, False for best quality
    if fast_mode:
        exaggeration = 0.8
        cfg_weight = 0.15
        prompt_trim_seconds = 2.0
    else:
        exaggeration = 1.0
        cfg_weight = 0.25
        prompt_trim_seconds = 3.5

    trimmed_prompt = trim_prompt(audio_prompt_path, prompt_trim_seconds, model.sr)
    try:
        _ = model.generate(
            ".",
            audio_prompt_path=trimmed_prompt,
            exaggeration=exaggeration,
            cfg_weight=min(0.1, cfg_weight),
        )
    except Exception:
        pass

    with torch.inference_mode():
        if streaming:
            chunks = split_text_chunks(text)
            wf = write_streaming_wav(output_path, model.sr)
            fade_ms = 30
            fade_samples = max(0, int(model.sr * fade_ms / 1000))
            prev_tail = None
            try:
                n = max(1, len(chunks))
                w0 = cfg_weight
                w1 = min(cfg_weight * 1.2, cfg_weight + 0.2)
                step = (w1 - w0) / max(1, n - 1)
                for i, chunk in enumerate(chunks):
                    curr_cfg = w0 + step * i
                    wav = model.generate(
                        chunk,
                        audio_prompt_path=trimmed_prompt,
                        exaggeration=exaggeration,
                        cfg_weight=curr_cfg,
                    )
                    wav = ensure_mono_1xT(wav)
                    if fade_samples <= 0:
                        wf.writeframes(tensor_to_pcm16_bytes(wav))
                        continue
                    if wav.size(1) <= fade_samples:
                        prev_tail = wav if prev_tail is None else torch.cat([prev_tail, wav], dim=1)
                        continue
                    if prev_tail is None:
                        head = wav[:, :-fade_samples]
                        prev_tail = wav[:, -fade_samples:]
                        wf.writeframes(tensor_to_pcm16_bytes(head))
                    else:
                        head = wav[:, :fade_samples]
                        rest = wav[:, fade_samples:]
                        fade = torch.linspace(0, 1, fade_samples, device=wav.device).view(1, -1)
                        overlap = prev_tail * (1 - fade) + head * fade
                        wf.writeframes(tensor_to_pcm16_bytes(overlap))
                        if rest.size(1) > fade_samples:
                            mid = rest[:, :-fade_samples]
                            prev_tail = rest[:, -fade_samples:]
                            wf.writeframes(tensor_to_pcm16_bytes(mid))
                        else:
                            prev_tail = rest
                if prev_tail is not None and prev_tail.numel() > 0:
                    wf.writeframes(tensor_to_pcm16_bytes(prev_tail))
            finally:
                wf.close()
            postprocess_output(output_path, model.sr)
        else:
            wav = model.generate(
                text,
                audio_prompt_path=trimmed_prompt,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight,
            )
            ta.save(output_path, wav, model.sr)
            postprocess_output(output_path, model.sr)

    if trimmed_prompt != audio_prompt_path and trimmed_prompt and os.path.exists(trimmed_prompt):
        try:
            os.unlink(trimmed_prompt)
        except Exception:
            pass


if __name__ == "__main__":
    main()
