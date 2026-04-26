from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ActiveTurn:
    mode: str
    english_hint: str | None = None
    target_text: str | None = None
    audio_chunks: list[bytes] = field(default_factory=list)


@dataclass(slots=True)
class SessionState:
    session_id: str
    conversation: list[dict[str, str]] = field(default_factory=list)
    last_ai_text: str = ""
    last_user_text: str = ""
    pending_assist_phrase: str | None = None
    pattern_counts: dict[str, int] = field(default_factory=dict)
    current_turn: ActiveTurn | None = None

    def trim_history(self, max_turns: int) -> None:
        max_messages = max_turns * 2
        if len(self.conversation) > max_messages:
            self.conversation = self.conversation[-max_messages:]

