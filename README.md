# Custom Chatterbox TTS (Voice Cloning Module) (Mac-Optimized, Modular API + GUI)

A modular, low-compute Text-to-Speech service built on `ChatterboxTTS`. Optimized for Apple Silicon (M1/M2/M3/M4) using MPS with CPU fallback. Includes:
- FastAPI service for backend integration
- PyQt/PySide GUI for recording prompts and generating audio
- CLI for quick synthesis

## Quickstart
1) Create and activate a virtualenv
```
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```
2) Install Torch/Torchaudio that match your platform (see https://pytorch.org/get-started/locally/)
```
# Example CPU-only wheels (adjust for your system):
# python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```
3) Install this package (API/Service)
```
python -m pip install -e .
```
4) Choose ONE GUI backend (optional, only for GUI)
```
# Option A (recommended): PySide6
python -m pip install -e .[pyside]

# Option B: pinned PyQt6 versions
python -m pip install -e .[gui]
```
5) Verify imports
```
python -c "from chatterbox_gui.qt_compat import BACKEND; print('GUI backend:', BACKEND)"
python -c "import torch, torchaudio; print('Torch OK')"
```

## Project structure
```
chatterbox_server/
  __init__.py
  __main__.py            # enables: python -m chatterbox_server
  api.py                 # FastAPI app and endpoints
  cli.py                 # CLI tool (python -m chatterbox_server.cli)
  processing.py          # audio prep/post, chunking, streaming helpers
  tts_service.py         # service class (synthesize_to_file/bytes/stream)
chatterbox_gui/
  __init__.py
  gui.py                 # Qt GUI (PyQt6 or PySide6 via qt_compat)
  qt_compat.py           # selects PyQt6 or PySide6 and aliases signals
  recorder.py            # microphone recorder helper
scripts/
  run_api.py             # simple API runner
gui.py                   # top-level GUI launcher
Dockerfile               # container build for API
requirements.txt         # base runtime deps
setup.py                 # package config and console scripts
README.md
```

## Run the API
Use the console script or module execution (don’t run api.py directly):
```
chatterbox-api
# or
python -m chatterbox_server
# or
python -m scripts.run_api
```
Environment variables:
- CHATTERBOX_API_HOST (default 127.0.0.1)
- CHATTERBOX_API_PORT (default 8000)

OpenAPI docs: http://127.0.0.1:8000/docs

## Run the GUI
```
# Top-level launcher
python gui.py

# Or console script (after install)
chatterbox-gui

# Or direct module
python -m chatterbox_gui.gui
```
Features:
- Record prompt (WAV/MP3), or browse an existing prompt file.
- Enter text to synthesize.
- Controls: Fast mode, Exaggeration, CFG weight, Prompt trim seconds, Stream chunks, Fade (ms), Pitch (semitones), Tempo (time-stretch).
- Save output WAV and play it in-app.

## Command-line usage (CLI)
```
python -m chatterbox_server.cli "hello world" \
  --prompt "/path/prompt.wav" \
  --out out.wav --fast --pitch 2 --tempo 1.1
```
Options: --exaggeration, --cfg, --trim, --stream, --fade, --pitch, --tempo

## API usage
### POST /synthesize (application/json)
Request body:
```
{
  "text": "your text",
  "audio_prompt_path": "/path/to/prompt.wav",          # optional
  "audio_prompt_b64": "...base64 wav...",               # optional alternative
  "fast_mode": true,
  "exaggeration": 0.8,
  "cfg_weight": 0.15,
  "prompt_trim_seconds": 2.0,
  "streaming": false,
  "return_base64": true,
  "pitch_semitones": 0.0,
  "time_stretch": 1.0
}
```
Response when return_base64=true:
```
{ "audio_b64": "...", "sr": 24000 }
```
Response when return_base64=false:
```
{ "file_path": "/tmp/tmpabcd.wav", "sr": 24000 }
```

### POST /synthesize_upload (multipart/form-data)
Fields: text, file, fast_mode, exaggeration, cfg_weight, prompt_trim_seconds, streaming, return_base64, pitch_semitones, time_stretch

### POST /stream_raw
Streams raw PCM16 mono frames for low-latency pipelines. Response headers include X-Sample-Rate.

## Docker
```
docker build -t chatterbox .
docker run -p 8000:8000 chatterbox
# Optional CPU wheels for torch:
docker build --build-arg TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu -t chatterbox .
```

## Troubleshooting
- Relative import error: attempted relative import with no known parent package
  - Don’t run files inside packages directly. Use:
    - API: chatterbox-api or python -m chatterbox_server
    - CLI: python -m chatterbox_server.cli
    - GUI: python gui.py or chatterbox-gui

- Qt import error or symbol not found (macOS)
  - Use only ONE toolkit in your venv (not both):
    - PySide6 (recommended): `pip install -e .[pyside]`
    - or pinned PyQt6: `pip install -e .[gui]`
  - Verify: `python -c "from chatterbox_gui.qt_compat import BACKEND; print(BACKEND)"`
  - For MP3 support, install ffmpeg (macOS): `brew install ffmpeg`

- Prompt quality
  - Use clean, close-mic speech. The service denoises/EQs, trims silence, and picks a high-energy window.
  - For better cloning: set fast_mode=false, prompt_trim_seconds=3.5–5.0, cfg_weight≈0.25–0.35, exaggeration≈1.0.

## Performance notes
- Low-compute defaults (threads=1, interop=1, optional FP16 on MPS)
- Sentence chunking + crossfaded streaming
- Postprocessing (gain/compand/EQ) for clarity and loudness

## License
MIT (replace with your project’s license if different)
