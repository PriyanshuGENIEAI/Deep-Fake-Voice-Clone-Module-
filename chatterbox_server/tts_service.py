import os
import tempfile
from dataclasses import dataclass
from typing import Generator, Optional

import torch
import torchaudio as ta

from chatterbox.tts import ChatterboxTTS
try:
    from .processing import (
        device_and_map,
        low_compute_defaults,
        split_text_chunks,
        ensure_mono_1xT,
        tensor_to_pcm16_bytes,
        write_streaming_wav,
        postprocess_output,
        trim_prompt,
    )
except Exception:
    # Fallback for direct execution: python chatterbox_server/tts_service.py
    import os as _os, sys as _sys
    _sys.path.append(_os.path.dirname(_os.path.dirname(__file__)))
    from chatterbox_server.processing import (
        device_and_map,
        low_compute_defaults,
        split_text_chunks,
        ensure_mono_1xT,
        tensor_to_pcm16_bytes,
        write_streaming_wav,
        postprocess_output,
        trim_prompt,
    )


@dataclass
class TTSSettings:
    fast_mode: bool = True
    exaggeration: float = 0.8
    cfg_weight: float = 0.15
    prompt_trim_seconds: float = 2.0
    streaming: bool = True
    fade_ms: int = 30
    pitch_semitones: float = 0.0
    time_stretch: float = 1.0


class TTSService:
    def __init__(self):
        low_compute_defaults()
        self.device, self.map_location = device_and_map()
        self.model = ChatterboxTTS.from_pretrained(device=self.device)
        if self.device == "mps":
            try:
                self.model = self.model.to(dtype=torch.float16)
            except Exception:
                pass

    @property
    def sr(self) -> int:
        return self.model.sr

    def warmup(self, settings: TTSSettings, audio_prompt_path: Optional[str]):
        trimmed_prompt = trim_prompt(audio_prompt_path, settings.prompt_trim_seconds, self.sr) if audio_prompt_path else None
        try:
            with torch.inference_mode():
                _ = self.model.generate(
                    ".",
                    audio_prompt_path=trimmed_prompt,
                    exaggeration=settings.exaggeration,
                    cfg_weight=min(0.1, settings.cfg_weight),
                )
        except Exception:
            pass
        return trimmed_prompt

    def synthesize_to_file(
        self,
        text: str,
        audio_prompt_path: Optional[str],
        output_path: str,
        settings: Optional[TTSSettings] = None,
    ) -> str:
        if settings is None:
            settings = TTSSettings()
        trimmed_prompt = self.warmup(settings, audio_prompt_path)
        with torch.inference_mode():
            if settings.streaming:
                chunks = split_text_chunks(text)
                wf = write_streaming_wav(output_path, self.sr)
                fade_samples = max(0, int(self.sr * settings.fade_ms / 1000))
                prev_tail = None
                try:
                    n = max(1, len(chunks))
                    w0 = settings.cfg_weight
                    w1 = min(settings.cfg_weight * 1.2, settings.cfg_weight + 0.2)
                    step = (w1 - w0) / max(1, n - 1)
                    for i, chunk in enumerate(chunks):
                        curr_cfg = w0 + step * i
                        wav = self.model.generate(
                            chunk,
                            audio_prompt_path=trimmed_prompt,
                            exaggeration=settings.exaggeration,
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
                postprocess_output(
                    output_path,
                    self.sr,
                    pitch_semitones=settings.pitch_semitones,
                    time_stretch=settings.time_stretch,
                )
            else:
                wav = self.model.generate(
                    text,
                    audio_prompt_path=trimmed_prompt,
                    exaggeration=settings.exaggeration,
                    cfg_weight=settings.cfg_weight,
                )
                ta.save(output_path, wav, self.sr)
                postprocess_output(
                    output_path,
                    self.sr,
                    pitch_semitones=settings.pitch_semitones,
                    time_stretch=settings.time_stretch,
                )
        return output_path

    def synthesize_bytes(
        self,
        text: str,
        audio_prompt_path: Optional[str],
        settings: Optional[TTSSettings] = None,
    ) -> bytes:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        try:
            self.synthesize_to_file(text, audio_prompt_path, tmp.name, settings)
            with open(tmp.name, "rb") as f:
                return f.read()
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

    def stream_chunks(
        self,
        text: str,
        audio_prompt_path: Optional[str],
        settings: Optional[TTSSettings] = None,
    ) -> Generator[bytes, None, None]:
        if settings is None:
            settings = TTSSettings()
        trimmed_prompt = self.warmup(settings, audio_prompt_path)
        with torch.inference_mode():
            chunks = split_text_chunks(text)
            fade_samples = max(0, int(self.sr * settings.fade_ms / 1000))
            prev_tail = None
            n = max(1, len(chunks))
            w0 = settings.cfg_weight
            w1 = min(settings.cfg_weight * 1.2, settings.cfg_weight + 0.2)
            step = (w1 - w0) / max(1, n - 1)
            for i, chunk in enumerate(chunks):
                curr_cfg = w0 + step * i
                wav = self.model.generate(
                    chunk,
                    audio_prompt_path=trimmed_prompt,
                    exaggeration=settings.exaggeration,
                    cfg_weight=curr_cfg,
                )
                wav = ensure_mono_1xT(wav)
                if fade_samples <= 0:
                    yield tensor_to_pcm16_bytes(wav)
                    continue
                if wav.size(1) <= fade_samples:
                    prev_tail = wav if prev_tail is None else torch.cat([prev_tail, wav], dim=1)
                    continue
                if prev_tail is None:
                    head = wav[:, :-fade_samples]
                    prev_tail = wav[:, -fade_samples:]
                    yield tensor_to_pcm16_bytes(head)
                else:
                    head = wav[:, :fade_samples]
                    rest = wav[:, fade_samples:]
                    fade = torch.linspace(0, 1, fade_samples, device=wav.device).view(1, -1)
                    overlap = prev_tail * (1 - fade) + head * fade
                    yield tensor_to_pcm16_bytes(overlap)
                    if rest.size(1) > fade_samples:
                        mid = rest[:, :-fade_samples]
                        prev_tail = rest[:, -fade_samples:]
                        yield tensor_to_pcm16_bytes(mid)
                    else:
                        prev_tail = rest
            if prev_tail is not None and prev_tail.numel() > 0:
                yield tensor_to_pcm16_bytes(prev_tail)
