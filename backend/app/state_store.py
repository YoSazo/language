from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.config import Settings
from backend.app.text_utils import extract_japanese_words


class StateStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.data_dir = settings.data_dir
        self.sessions_dir = self.data_dir / "sessions"
        self.vocab_path = self.data_dir / "vocab.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._vocab = self._load_json(self.vocab_path, default={})

    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save_vocab(self) -> None:
        with self.vocab_path.open("w", encoding="utf-8") as handle:
            json.dump(self._vocab, handle, ensure_ascii=False, indent=2)

    def update_vocab_from_text(self, text: str) -> None:
        for word in extract_japanese_words(text):
            self._vocab[word] = self._vocab.get(word, 0) + 1
        self._save_vocab()

    def known_word_count(self, threshold: int = 5) -> int:
        return sum(1 for count in self._vocab.values() if count >= threshold)

    def total_word_count(self) -> int:
        return len(self._vocab)

    def log_event(self, session_id: str, event: dict[str, Any]) -> None:
        path = self.sessions_dir / f"{session_id}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

