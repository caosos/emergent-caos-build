import base64
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import UploadFile
from emergentintegrations.llm.openai import OpenAISpeechToText, OpenAITextToSpeech


async def generate_tts_base64(text: str, voice: str = "nova", speed: float = 1.0, model: str = "tts-1") -> dict:
    # Coerce known-bad models to the proxy-reliable default. tts-1 is the emergent-reliable
    # path per integration playbook (tts-1-hd intermittently 500s on the proxy).
    safe_model = model if model in ("tts-1", "tts-1-hd") else "tts-1"
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    try:
        audio_b64 = await tts.generate_speech_base64(
            text=text[:4096],
            model=safe_model,
            voice=voice,
            speed=speed,
        )
        return {
            "audio_base64": audio_b64,
            "content_type": "audio/mpeg",
            "voice": voice,
            "model": safe_model,
            "speed": speed,
        }
    except Exception as primary_error:
        if safe_model != "tts-1":
            try:
                audio_b64 = await tts.generate_speech_base64(text=text[:4096], model="tts-1", voice=voice, speed=speed)
                return {
                    "audio_base64": audio_b64,
                    "content_type": "audio/mpeg",
                    "voice": voice,
                    "model": "tts-1",
                    "speed": speed,
                    "fallback_used": True,
                }
            except Exception:
                pass
        raise primary_error


async def transcribe_upload(
    file: UploadFile,
    model: str = "whisper-1",
    fallback_model: str = "whisper-1",
    language: str | None = "en",
    prompt: str | None = None,
) -> dict:
    # Emergent Universal Key only supports whisper-1 for STT. Any other model name
    # is silently coerced to whisper-1 here (frontend may still request others).
    # See: OPENAI_SPEECH_TO_TEXT_INTEGRATION_PLAYBOOK — only whisper-1 is available.
    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp.write(await file.read())
        temp_path = temp.name
    try:
        stt = OpenAISpeechToText(api_key=os.environ["EMERGENT_LLM_KEY"])
        safe_prompt = (prompt[:200] if prompt else None)
        try:
            with open(temp_path, "rb") as audio_fh:
                result = await stt.transcribe(
                    file=audio_fh,
                    model="whisper-1",
                    response_format="json",
                    language=language or None,
                    prompt=safe_prompt,
                    temperature=0.0,
                )
            text = getattr(result, "text", None) or (result.get("text", "") if isinstance(result, dict) else "")
            return {
                "text": (text or "").strip(),
                "model_used": "whisper-1",
                "fallback_used": model != "whisper-1",
            }
        except Exception as error:
            # Surface the real error — don't pretend transcription succeeded with empty text.
            # As of Apr 2026 the Emergent proxy's upstream `sk-proj-...` key for audio routes
            # has been returning HTTP 401 ("Incorrect API key provided"); previously we
            # masked this as `{"text":""}` which made debugging impossible.
            error_text = str(error)[:400]
            return {
                "text": "",
                "model_used": "whisper-1",
                "fallback_used": False,
                "error": error_text,
                "platform_note": "Emergent audio proxy is currently returning auth errors — upstream OpenAI key issue. TTS/STT is blocked until Emergent rotates the upstream key. Support ticket sent.",
            }
    finally:
        Path(temp_path).unlink(missing_ok=True)