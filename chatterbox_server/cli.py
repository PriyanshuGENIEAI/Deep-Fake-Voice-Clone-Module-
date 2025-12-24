import argparse
import os
from typing import Optional

from .tts_service import TTSService, TTSSettings


def main() -> None:
    p = argparse.ArgumentParser(description="Chatterbox TTS CLI")
    p.add_argument("text", help="Text to synthesize")
    p.add_argument("--prompt", dest="prompt", help="Path to voice prompt (wav/mp3)")
    p.add_argument("--out", dest="out", default=os.path.join(os.getcwd(), "out.wav"), help="Output wav path")
    p.add_argument("--fast", dest="fast", action="store_true", help="Enable fast mode")
    p.add_argument("--exaggeration", type=float, default=0.8)
    p.add_argument("--cfg", dest="cfg_weight", type=float, default=0.15)
    p.add_argument("--trim", dest="prompt_trim_seconds", type=float, default=2.0)
    p.add_argument("--stream", dest="stream", action="store_true", help="Stream chunks to file")
    p.add_argument("--fade", dest="fade_ms", type=int, default=30)
    p.add_argument("--pitch", dest="pitch_semitones", type=float, default=0.0)
    p.add_argument("--tempo", dest="time_stretch", type=float, default=1.0)
    args = p.parse_args()

    svc = TTSService()
    settings = TTSSettings(
        fast_mode=bool(args.fast),
        exaggeration=float(args.exaggeration),
        cfg_weight=float(args.cfg_weight),
        prompt_trim_seconds=float(args.prompt_trim_seconds),
        streaming=bool(args.stream),
        fade_ms=int(args.fade_ms),
        pitch_semitones=float(args.pitch_semitones),
        time_stretch=float(args.time_stretch),
    )

    path = svc.synthesize_to_file(args.text, args.prompt, args.out, settings)
    print(f"Saved: {path}")


if __name__ == "__main__":
    main()
