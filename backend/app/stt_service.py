from __future__ import annotations

from threading import Lock

import numpy as np
from faster_whisper import WhisperModel

from backend.app.config import Settings


class WhisperService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model: WhisperModel | None = None
        self._lock = Lock()

    def _load_model(self) -> WhisperModel:
        with self._lock:
            if self._model is not None:
                return self._model
            try:
                self._model = WhisperModel(
                    self.settings.whisper_model_size,
                    device=self.settings.whisper_device,
                    compute_type=self.settings.whisper_compute_type,
                )
            except Exception:
                self._model = WhisperModel(
                    self.settings.whisper_model_size,
                    device="cpu",
                    compute_type="int8",
                )
            return self._model

    def transcribe_pcm16(self, pcm_bytes: bytes, language_hint: str | None = None) -> str:
        if not pcm_bytes:
            return ""

        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if audio.size < 1600:
            return ""

        model = self._load_model()
        segments, _ = model.transcribe(
            audio,
            language=language_hint,
            beam_size=2,
            vad_filter=True,
            condition_on_previous_text=False,
            without_timestamps=True,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text

