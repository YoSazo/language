from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _load_local_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


@dataclass(slots=True)
class Settings:
    host: str
    port: int
    ollama_host: str
    preferred_chat_models: tuple[str, ...]
    utility_model: str
    whisper_model_size: str
    whisper_device: str
    whisper_compute_type: str
    max_conversation_turns: int
    assistant_name: str
    data_dir: Path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_local_env()
    base_dir = Path(__file__).resolve().parent.parent
    return Settings(
        host=os.getenv("JAPANESE_COACH_HOST", "0.0.0.0"),
        port=int(os.getenv("JAPANESE_COACH_PORT", "8765")),
        ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
        preferred_chat_models=_split_csv(
            os.getenv(
                "PREFERRED_CHAT_MODELS",
                "qwen2.5:7b,gemma3:4b,qwen3.5:4b",
            )
        ),
        utility_model=os.getenv("UTILITY_MODEL", "qwen3.5:0.8b"),
        whisper_model_size=os.getenv("WHISPER_MODEL_SIZE", "small"),
        whisper_device=os.getenv("WHISPER_DEVICE", "cuda"),
        whisper_compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "float16"),
        max_conversation_turns=int(os.getenv("MAX_CONVERSATION_TURNS", "14")),
        assistant_name=os.getenv("ASSISTANT_NAME", "Yuki"),
        data_dir=Path(os.getenv("DATA_DIR", str(base_dir / "data"))),
    )
