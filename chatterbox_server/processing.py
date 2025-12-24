import os
import re
import wave
import tempfile
import hashlib
from typing import List, Optional

import torch
import torchaudio as ta

# Prefer safe MPS CPU fallback
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")


def device_and_map():
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    map_location = torch.device(device)
    return device, map_location


def low_compute_defaults():
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


def split_text_chunks(s: str, max_len: int = 250, min_len: int = 20) -> List[str]:
    chunks: List[str] = []
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
    merged: List[str] = []
    for ch in chunks:
        if merged and len(ch) < min_len:
            merged[-1] = (merged[-1] + " " + ch).strip()
        else:
            merged.append(ch)
    return merged


def ensure_mono_1xT(x: torch.Tensor) -> torch.Tensor:
    if x is None:
        return x
    if x.dim() == 1:
        x = x.unsqueeze(0)
    if x.dim() == 2 and x.size(0) > 1:
        x = x.mean(dim=0, keepdim=True)
    return x


def tensor_to_pcm16_bytes(x: torch.Tensor) -> bytes:
    if x is None:
        return b""
    if x.dim() == 2:
        if x.size(0) == 1:
            x = x.squeeze(0)
        else:
            x = x.mean(dim=0)
    x = torch.clamp(x, -1.0, 1.0)
    return (x * 32767.0).to(torch.int16).cpu().numpy().tobytes()


def write_streaming_wav(output_path: str, sr: int):
    wf = wave.open(output_path, "wb")
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sr)
    return wf


def postprocess_output(path: str, target_sr: int, *, pitch_semitones: float = 0.0, time_stretch: float = 1.0) -> None:
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
                ["lowpass", "12000"],
                ["equalizer", "7000", "1.0q", "-4"],
            ]
            if abs(pitch_semitones) > 0.01:
                effects.append(["pitch", str(int(pitch_semitones * 100))])
            if abs(time_stretch - 1.0) > 0.01:
                # sox tempo preserves pitch, values >1.0 speed up
                effects.append(["tempo", str(max(0.5, min(2.0, time_stretch)))])
            wav, sr = sox.apply_effects_tensor(wav, sr, effects)
        except Exception:
            peak = float(wav.abs().max()) if wav.numel() > 0 else 0.0
            if peak > 0:
                wav = wav / peak * 10 ** (-1 / 20)
        ta.save(path, wav, sr)
    except Exception:
        pass


def _prompt_cache_path(source_path: str, seconds: float, target_sr: Optional[int]) -> Optional[str]:
    try:
        st = os.stat(source_path)
        cache_key = f"{os.path.abspath(source_path)}|{st.st_mtime_ns}|{seconds}|{target_sr}|v3"
        hexkey = hashlib.sha1(cache_key.encode()).hexdigest()
        return os.path.join(tempfile.gettempdir(), f"chatterbox_promptcache_{hexkey}.wav")
    except Exception:
        return None


def trim_prompt(path: str, seconds: Optional[float], target_sr: Optional[int]) -> str:
    if not path or not os.path.exists(path) or not seconds or seconds <= 0:
        return path
    cache_path = _prompt_cache_path(path, seconds, target_sr)
    if cache_path and os.path.exists(cache_path):
        return cache_path
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
            seg = wav[:, i : i + win]
            e = float(seg.square().mean())
            if best_e is None or e > best_e:
                best_e = e
                best_i = i
        wav = wav[:, best_i : best_i + win]
    # trim silence borders
    frame_len = max(1, int(sr * 0.02))
    hop = max(1, int(sr * 0.01))
    energies = []
    for i in range(0, wav.size(1) - frame_len + 1, hop):
        frame = wav[0, i : i + frame_len]
        energies.append(float((frame.square().mean() + 1e-9).log10()))
    if energies:
        mx = max(energies)
        thr = mx - 1.5
        start_idx = 0
        for j, e in enumerate(energies):
            if e >= thr:
                start_idx = j * hop
                break
        end_idx = wav.size(1)
        for j in range(len(energies) - 1, -1, -1):
            if energies[j] >= thr:
                end_idx = min(end_idx, j * hop + frame_len)
                break
        wav = wav[:, start_idx:end_idx]
    peak = float(wav.abs().max()) if wav.numel() > 0 else 0.0
    if peak > 0:
        wav = wav / peak * 10 ** (-1 / 20)
    if cache_path:
        ta.save(cache_path, wav, sr)
        return cache_path
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    ta.save(tmp.name, wav, sr)
    return tmp.name
