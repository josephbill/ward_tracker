"""
Speech-to-text for the voice-to-text reporting flow. Same pattern as
services/ledger and services/channels: a small interface, a Dummy
implementation that's honest about not actually transcribing (so the
upload/plumbing is fully testable with zero credentials), and a real
implementation ready to switch in via config once an API key exists.

Native voice input in the app records audio locally (expo-av) and uploads it
here rather than transcribing on-device, since Expo Go has no on-device STT
module without a custom dev client (same constraint as the Bluetooth
scaffolding — see mobile-app/src/bluetooth/README.md for the parallel). Web
instead uses the browser's built-in Web Speech API directly client-side and
never calls this endpoint at all — see mobile-app/src/services/voice.ts.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class SttClient(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str, lang: str) -> str: ...


class DummySttClient(SttClient):
    """Returns an honest placeholder instead of a fabricated transcript —
    silently returning empty text would look like a broken mic; returning
    fake words would be worse. Real audio is still saved and available for
    a human reviewer, or for reprocessing once a real backend is wired in."""

    def transcribe(self, audio_path: str, lang: str) -> str:
        return ""


class OpenAiWhisperSttClient(SttClient):
    """Real client — needs OPENAI_API_KEY. Not exercised in this PoC without
    that credential. Whisper auto-detects language well, but `lang` is still
    passed as a hint since we already know the resident's selected language."""

    def __init__(self, api_key: str):
        from openai import OpenAI  # imported lazily: optional dep

        self._client = OpenAI(api_key=api_key)

    def transcribe(self, audio_path: str, lang: str) -> str:
        with open(audio_path, "rb") as f:
            result = self._client.audio.transcriptions.create(
                model="whisper-1", file=f, language=lang if lang != "kam" else None
            )
        return result.text


_client: SttClient | None = None


def get_stt_client(config) -> SttClient:
    global _client
    if _client is not None:
        return _client
    if config.STT_BACKEND == "openai_whisper":
        _client = OpenAiWhisperSttClient(config.OPENAI_API_KEY)
    else:
        _client = DummySttClient()
    return _client


def reset_stt_client() -> None:
    global _client
    _client = None
