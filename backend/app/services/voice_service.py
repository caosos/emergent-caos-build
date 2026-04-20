"""Voice I/O service (STT + TTS).

Preference order:
1. Direct OpenAI API if `OPENAI_API_KEY` is set in env — unlocks the newer
   `gpt-4o-mini-tts` / `gpt-4o-mini-transcribe` models and bypasses the
   Emergent proxy (which as of Apr 2026 is returning 401 on audio routes
   because the upstream project key is invalid).
2. Emergent Universal Key via `emergentintegrations` (fallback, limited to
   whisper-1 / tts-1 / tts-1-hd).

Whenever direct OpenAI is available, we use it. The Emergent path is only
exercised if the user hasn't supplied their own key.
"""
import base64
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import UploadFile
from emergentintegrations.llm.openai import OpenAISpeechToText, OpenAITextToSpeech


# Model preference — "mini" is the current 2026 OpenAI default; gpt-5.2 isn't
# available on audio routes, gpt-4o-* are. We fall back to legacy models if the
# newer ones aren't accessible on the caller's key.
OPENAI_TTS_MODELS = ["gpt-4o-mini-tts", "tts-1", "tts-1-hd"]
OPENAI_STT_MODELS = ["gpt-4o-mini-transcribe", "whisper-1"]


def _direct_openai_available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


async def _direct_tts(text: str, voice: str, speed: float, preferred_model: str) -> dict:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    tried: list[str] = []
    ordered = [preferred_model] + [m for m in OPENAI_TTS_MODELS if m != preferred_model]
    for model in ordered:
        tried.append(model)
        try:
            response = await client.audio.speech.create(
                model=model,
                voice=voice,
                input=text[:4096],
                speed=max(0.25, min(4.0, speed)),
            )
            audio_bytes = response.read()
            return {
                "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
                "content_type": "audio/mpeg",
                "voice": voice,
                "model": model,
                "speed": speed,
                "route": "direct_openai",
            }
        except Exception as error:
            if model == ordered[-1]:
                raise RuntimeError(f"All TTS models failed (tried {tried}): {str(error)[:240]}") from error
            continue
    raise RuntimeError("No TTS model succeeded")


async def _direct_stt(file_path: str, language: str | None, prompt: str | None, preferred_model: str) -> dict:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    tried: list[str] = []
    ordered = [preferred_model] + [m for m in OPENAI_STT_MODELS if m != preferred_model]
    last_error = None
    for model in ordered:
        tried.append(model)
        try:
            with open(file_path, "rb") as audio_fh:
                # gpt-4o-mini-transcribe only supports response_format="json" or "text"
                kwargs: dict = {"model": model, "file": audio_fh, "response_format": "json"}
                if language:
                    kwargs["language"] = language
                if prompt:
                    kwargs["prompt"] = prompt[:200]
                if model == "whisper-1":
                    kwargs["temperature"] = 0.0
                result = await client.audio.transcriptions.create(**kwargs)
            text = getattr(result, "text", "") or ""
            return {
                "text": text.strip(),
                "model_used": model,
                "fallback_used": model != preferred_model,
                "route": "direct_openai",
            }
        except Exception as error:
            last_error = error
            continue
    raise RuntimeError(f"All STT models failed (tried {tried}): {str(last_error)[:240]}")


async def generate_tts_base64(text: str, voice: str = "nova", speed: float = 1.0, model: str = "gpt-4o-mini-tts") -> dict:
    if _direct_openai_available():
        return await _direct_tts(text, voice, speed, model if model in OPENAI_TTS_MODELS else "gpt-4o-mini-tts")
    # Legacy Emergent path (proxy-limited to tts-1/tts-1-hd)
    safe_model = model if model in ("tts-1", "tts-1-hd") else "tts-1"
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    audio_b64 = await tts.generate_speech_base64(text=text[:4096], model=safe_model, voice=voice, speed=speed)
    return {
        "audio_base64": audio_b64,
        "content_type": "audio/mpeg",
        "voice": voice,
        "model": safe_model,
        "speed": speed,
        "route": "emergent_proxy",
    }


async def transcribe_upload(
    file: UploadFile,
    model: str = "gpt-4o-mini-transcribe",
    fallback_model: str = "whisper-1",
    language: str | None = "en",
    prompt: str | None = None,
) -> dict:
    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp.write(await file.read())
        temp_path = temp.name
    try:
        if _direct_openai_available():
            preferred = model if model in OPENAI_STT_MODELS else "gpt-4o-mini-transcribe"
            try:
                return await _direct_stt(temp_path, language or None, prompt, preferred)
            except Exception as error:
                return {
                    "text": "",
                    "model_used": preferred,
                    "fallback_used": False,
                    "error": str(error)[:400],
                    "route": "direct_openai_failed",
                }
        # Legacy Emergent path (whisper-1 only; may 401 if upstream key is rotated)
        stt = OpenAISpeechToText(api_key=os.environ["EMERGENT_LLM_KEY"])
        try:
            with open(temp_path, "rb") as audio_fh:
                result = await stt.transcribe(
                    file=audio_fh, model="whisper-1", response_format="json",
                    language=language or None, prompt=(prompt[:200] if prompt else None),
                    temperature=0.0,
                )
            text = getattr(result, "text", None) or (result.get("text", "") if isinstance(result, dict) else "")
            return {"text": (text or "").strip(), "model_used": "whisper-1", "fallback_used": False, "route": "emergent_proxy"}
        except Exception as error:
            return {
                "text": "", "model_used": "whisper-1", "fallback_used": False,
                "error": str(error)[:400], "route": "emergent_proxy_failed",
                "platform_note": "Emergent audio proxy is returning auth errors — set OPENAI_API_KEY in /app/backend/.env for a direct path.",
            }
    finally:
        Path(temp_path).unlink(missing_ok=True)
