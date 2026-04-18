import base64
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import UploadFile
from emergentintegrations.llm.openai import OpenAISpeechToText, OpenAITextToSpeech


async def generate_tts_base64(text: str, voice: str = "nova", speed: float = 1.0, model: str = "tts-1-hd") -> dict:
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    audio_bytes = await tts.generate_speech(text=text[:4096], model=model, voice=voice, speed=speed, response_format="mp3")
    return {
        "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
        "content_type": "audio/mpeg",
        "voice": voice,
        "model": model,
        "speed": speed,
    }


async def transcribe_upload(file: UploadFile) -> dict:
    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp.write(await file.read())
        temp_path = temp.name
    try:
        stt = OpenAISpeechToText(api_key=os.environ["EMERGENT_LLM_KEY"])
        result = await stt.transcribe(Path(temp_path), model="whisper-1", response_format="verbose_json")
        text = getattr(result, "text", None) or result.get("text", "")
        return {"text": text, "raw": result}
    finally:
        Path(temp_path).unlink(missing_ok=True)