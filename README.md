# Chatterbox TTS Service (Mac-Optimized)

A modular, low-compute Text-to-Speech service built on `ChatterboxTTS` with a production-friendly API. Optimized for Apple Silicon (M1/M2/M3/M4) using MPS with CPU fallback.

## Features
- Low-compute defaults (1 thread, interop=1, MPS when available, optional FP16)
- Energy-trimmed, denoised and cached voice prompt preprocessing for better cloning
- Sentence-based chunking with short-chunk merging to reduce overhead
- Overlap-add crossfade for smoother streaming continuity
- Postprocessing (gain/compand/EQ) for clarity and loudness
- FastAPI endpoints for easy backend integration (JSON or multipart)

## Install
Torch and torchaudio wheels vary by platform. If installing from scratch:
- First install a compatible Torch/torchaudio for your system (see pytorch.org)
- Then install the API package dependencies

Example (you may already have torch/torchaudio):

```
# recommend a virtualenv
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
# install torch+torchaudio for your system first (visit pytorch.org for the right command)
# pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# install API deps
pip install fastapi uvicorn[standard]
# or install the package (will attempt to install torch+torchaudio if missing)
pip install -e .
```

## Run the API
```
python -m scripts.run_api
# or
chatterbox-api  # console script
```
Environment variables:
- CHATTERBOX_API_HOST: default 127.0.0.1
- CHATTERBOX_API_PORT: default 8000

OpenAPI docs: http://localhost:8000/docs

## Run the GUI (PyQt6)
The GUI records a prompt (WAV/MP3), lets you type text, and generates speech with controls for speed/quality, pitch, and tempo.

Install extra dep (if not installed through setup.py):
```
pip install PyQt6
```

Launch:
```
chatterbox-gui
# or
python -m chatterbox_gui.gui
```

Controls:
- Prompt: browse existing audio or record from microphone (WAV/MP3). Recording uses 16k mono by default.
- Text: enter text to speak.
- Parameters:
  - Fast mode: low latency preset (exaggeration 0.8, cfg 0.15, trim ~2s).
  - Exaggeration, CFG weight, Prompt trim seconds.
  - Stream chunks, Fade ms.
  - Pitch (semitones), Tempo (time-stretch) for postprocessing.
- Output: choose target WAV and Generate; playback inside the app.

## API
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
  "return_base64": true
}
```
Response when return_base64=true:
```
{
  "audio_b64": "...",
  "sr": 24000
}
```
Response when return_base64=false:
```
{
  "file_path": "/tmp/tmpabcd.wav",
  "sr": 24000
}
```

### POST /synthesize_upload (multipart/form-data)
Form fields:
- text: string
- file: binary (audio prompt)
- fast_mode, exaggeration, cfg_weight, prompt_trim_seconds, streaming, return_base64

Returns same structure as /synthesize.

## Using the Python service directly
```python
from chatterbox_server.tts_service import TTSService, TTSSettings

svc = TTSService()
settings = TTSSettings(fast_mode=True, cfg_weight=0.15, exaggeration=0.8, prompt_trim_seconds=2.0)
audio_bytes = svc.synthesize_bytes("hello world", "/path/to/prompt.wav", settings)
with open("out.wav", "wb") as f:
    f.write(audio_bytes)
```

## Notes on performance and quality
- For lowest latency: fast_mode=true (exaggeration≈0.8, cfg≈0.15, trim≈2s).
- For better clone accuracy: fast_mode=false (exaggeration≈1.0, cfg≈0.25, trim≈3.5s).
- Prompts: use clean, close-mic speech. The service automatically picks a high-energy window and trims silence.
- MPS is enabled by default when available; CPU fallback is automatic via PYTORCH_ENABLE_MPS_FALLBACK=1.

## Project layout
- chatterbox_server/
  - processing.py: audio prep/post & streaming helpers
  - tts_service.py: service class with synthesize methods
  - api.py: FastAPI app with endpoints
- scripts/run_api.py: API runner
- setup.py: package config
- README.md: this file
- example_for_mac_optimized.py: standalone example script

## License
MIT (replace with your project’s license if different)
