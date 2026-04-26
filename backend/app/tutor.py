from __future__ import annotations

from datetime import datetime, UTC

from backend.app.config import Settings
from backend.app.ollama_service import OllamaService
from backend.app.session_types import SessionState
from backend.app.state_store import StateStore
from backend.app.text_utils import (
    extract_japanese_words,
    join_known_patterns,
    pronunciation_feedback,
)


def _level_guidance(known_count: int) -> str:
    if known_count < 100:
        return "Complete beginner. Use short everyday Japanese. Keep most replies to 1 sentence and 8 words or less."
    if known_count < 500:
        return "Elementary learner. Use friendly short Japanese with simple past and present tense."
    if known_count < 1500:
        return "Pre-intermediate learner. Use natural casual Japanese, but keep replies compact and clear."
    return "Intermediate learner. Use natural casual Japanese and keep the conversation flowing."


def build_conversation_prompt(settings: Settings, known_count: int, pattern_counts: dict[str, int]) -> str:
    level = _level_guidance(known_count)
    patterns = join_known_patterns(pattern_counts)
    return f"""You are {settings.assistant_name}, a warm Japanese friend helping the learner become conversational fast.
Only speak Japanese. Never use English. Never use romaji.
Keep replies short: 1 to 3 sentences max, and usually closer to 1 or 2.
{level}
The learner should mostly practice speaking and listening, not reading or grammar lectures.
Pattern exposure so far: {patterns}

If the user's message includes [HOTKEY_ASSIST: ...], it means they used English help to build that idea.
React naturally, then reinforce the same grammar pattern with a slightly different follow-up question.

If the learner says something unnatural, do not lecture. Just model the natural Japanese in your reply.
Sound casual, kind, and encouraging, like a real friend texting and talking."""


TRANSLATE_PROMPT = """Translate the English phrase into natural casual Japanese that a real person would actually say.
Return only the Japanese line.
No English. No romaji. No explanation."""


EXPLAIN_PROMPT = """Explain the Japanese line in concise English for a speaking-first learner.
Format exactly like this:
EN: <natural English meaning>
NOTE: <one short speaking tip>
Keep both lines short."""


class JapaneseTutor:
    def __init__(self, settings: Settings, store: StateStore, ollama: OllamaService) -> None:
        self.settings = settings
        self.store = store
        self.ollama = ollama

    def greeting(self) -> str:
        return "よ、ユキだよ。日本語で話そう。今日は何してた？"

    def explain_last(self, session: SessionState) -> dict[str, str]:
        if not session.last_ai_text:
            return {
                "type": "explain_result",
                "japanese": "",
                "english": "",
                "note": "There is no previous reply yet.",
            }

        raw, model = self.ollama.single_shot(
            system=EXPLAIN_PROMPT,
            user=session.last_ai_text,
            temperature=0.2,
            num_predict=100,
        )
        english = ""
        note = ""
        for line in raw.splitlines():
            if line.startswith("EN:"):
                english = line[3:].strip()
            elif line.startswith("NOTE:"):
                note = line[5:].strip()

        if not english:
            english = raw.strip()
        if not note:
            note = "Listen once, then repeat the whole line naturally."

        return {
            "type": "explain_result",
            "japanese": session.last_ai_text,
            "english": english,
            "note": note,
            "model": model,
        }

    def translate_help(self, session: SessionState, english_text: str) -> dict[str, str]:
        japanese, model = self.ollama.single_shot(
            system=TRANSLATE_PROMPT,
            user=english_text,
            temperature=0.25,
            num_predict=80,
        )
        session.pending_assist_phrase = japanese
        self.store.update_vocab_from_text(japanese)
        self.store.log_event(
            session.session_id,
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "type": "translate_help",
                "english": english_text,
                "japanese": japanese,
                "model": model,
            },
        )
        return {
            "type": "turn_result",
            "mode": "translate_help",
            "transcript": english_text,
            "assistantJapanese": japanese,
            "assistantEnglishHint": english_text,
            "model": model,
        }

    def shadow_last_line(self, session: SessionState, spoken_text: str, target_text: str) -> dict[str, str | int]:
        score, feedback = pronunciation_feedback(target_text, spoken_text)
        self.store.log_event(
            session.session_id,
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "type": "shadow",
                "target": target_text,
                "heard": spoken_text,
                "score": score,
            },
        )
        return {
            "type": "turn_result",
            "mode": "shadowing",
            "transcript": spoken_text,
            "assistantJapanese": target_text,
            "pronunciationScore": score,
            "pronunciationFeedback": feedback,
        }

    def conversation_turn(self, session: SessionState, user_text: str) -> dict[str, str]:
        self.store.update_vocab_from_text(user_text)
        known_count = self.store.known_word_count()
        tagged_message = user_text

        if session.pending_assist_phrase:
            tagged_message = f"{user_text} [HOTKEY_ASSIST: {session.pending_assist_phrase}]"
            words = extract_japanese_words(session.pending_assist_phrase)
            if words:
                session.pattern_counts[words[0]] = session.pattern_counts.get(words[0], 0) + 1

        messages = [{"role": "system", "content": build_conversation_prompt(self.settings, known_count, session.pattern_counts)}]
        messages.extend(session.conversation)
        messages.append({"role": "user", "content": tagged_message})

        reply, model = self.ollama.chat(
            messages=messages,
            temperature=0.68,
            num_predict=140,
        )
        session.conversation.append({"role": "user", "content": tagged_message})
        session.conversation.append({"role": "assistant", "content": reply})
        session.trim_history(self.settings.max_conversation_turns)
        session.last_user_text = user_text
        session.last_ai_text = reply
        session.pending_assist_phrase = None

        self.store.update_vocab_from_text(reply)
        self.store.log_event(
            session.session_id,
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "type": "conversation_turn",
                "user": user_text,
                "assistant": reply,
                "model": model,
            },
        )
        return {
            "type": "turn_result",
            "mode": "conversation",
            "transcript": user_text,
            "assistantJapanese": reply,
            "model": model,
        }

