import base64
import os
import tempfile
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse, Response
import uvicorn

from .tts_service import TTSService, TTSSettings

app = FastAPI(title="Chatterbox TTS API", version="0.1.0")
svc = TTSService()


@app.post("/synthesize")
async def synthesize(
    text: str,
    audio_prompt_path: Optional[str] = None,
    audio_prompt_b64: Optional[str] = None,
    fast_mode: bool = True,
    exaggeration: float = 0.8,
    cfg_weight: float = 0.15,
    prompt_trim_seconds: float = 2.0,
    streaming: bool = False,
    return_base64: bool = True,
    pitch_semitones: float = 0.0,
    time_stretch: float = 1.0,
):
    settings = TTSSettings(
        fast_mode=fast_mode,
        exaggeration=exaggeration,
        cfg_weight=cfg_weight,
        prompt_trim_seconds=prompt_trim_seconds,
        streaming=streaming,
        pitch_semitones=pitch_semitones,
        time_stretch=time_stretch,
    )
    prompt_path = audio_prompt_path
    tmp_prompt = None
    try:
        if audio_prompt_b64 and not prompt_path:
            data = base64.b64decode(audio_prompt_b64)
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.write(data)
            tmp.close()
            tmp_prompt = tmp.name
            prompt_path = tmp_prompt
        if return_base64:
            audio_bytes = svc.synthesize_bytes(text, prompt_path, settings)
            return JSONResponse({"audio_b64": base64.b64encode(audio_bytes).decode("utf-8"), "sr": svc.sr})
        else:
            tmp_out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp_out.close()
            svc.synthesize_to_file(text, prompt_path, tmp_out.name, settings)
            return JSONResponse({"file_path": tmp_out.name, "sr": svc.sr})
    finally:
        if tmp_prompt and os.path.exists(tmp_prompt):
            try:
                os.unlink(tmp_prompt)
            except Exception:
                pass


@app.post("/synthesize_upload")
async def synthesize_upload(
    text: str = Form(...),
    file: UploadFile = File(...),
    fast_mode: bool = Form(True),
    exaggeration: float = Form(0.8),
    cfg_weight: float = Form(0.15),
    prompt_trim_seconds: float = Form(2.0),
    streaming: bool = Form(False),
    return_base64: bool = Form(True),
    pitch_semitones: float = Form(0.0),
    time_stretch: float = Form(1.0),
):
    tmp = tempfile.NamedTemporaryFile(suffix=os.path.splitext(file.filename)[1] or ".wav", delete=False)
    tmp.write(await file.read())
    tmp.close()
    try:
        return await synthesize(
            text=text,
            audio_prompt_path=tmp.name,
            audio_prompt_b64=None,
            fast_mode=fast_mode,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            prompt_trim_seconds=prompt_trim_seconds,
            streaming=streaming,
            return_base64=return_base64,
            pitch_semitones=pitch_semitones,
            time_stretch=time_stretch,
        )
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


@app.post("/stream_raw")
async def stream_raw(
    text: str,
    audio_prompt_path: Optional[str] = None,
    audio_prompt_b64: Optional[str] = None,
    fast_mode: bool = True,
    exaggeration: float = 0.8,
    cfg_weight: float = 0.15,
    prompt_trim_seconds: float = 2.0,
):
    settings = TTSSettings(
        fast_mode=fast_mode,
        exaggeration=exaggeration,
        cfg_weight=cfg_weight,
        prompt_trim_seconds=prompt_trim_seconds,
        streaming=True,
    )
    prompt_path = audio_prompt_path
    tmp_prompt = None
    try:
        if audio_prompt_b64 and not prompt_path:
            data = base64.b64decode(audio_prompt_b64)
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.write(data)
            tmp.close()
            tmp_prompt = tmp.name
            prompt_path = tmp_prompt
        gen = svc.stream_chunks(text, prompt_path, settings)
        headers = {
            "X-Sample-Rate": str(svc.sr),
            "X-Format": "PCM16 mono",
        }
        return StreamingResponse(gen, media_type="audio/L16", headers=headers)
    finally:
        if tmp_prompt and os.path.exists(tmp_prompt):
            try:
                os.unlink(tmp_prompt)
            except Exception:
                pass


def main():
    host = os.environ.get("CHATTERBOX_API_HOST", "127.0.0.1")
    port = int(os.environ.get("CHATTERBOX_API_PORT", "8000"))
    uvicorn.run("chatterbox_server.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
