from __future__ import annotations

import difflib
import re
from typing import Iterable

try:
    import fugashi
except Exception:  # pragma: no cover - optional dependency fallback
    fugashi = None


_tagger = fugashi.Tagger() if fugashi else None
_skip_pos = {"助詞", "助動詞", "記号", "補助記号", "空白"}
_jp_pattern = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]+")
_punct_pattern = re.compile(r"[^\w\u3040-\u30ff\u3400-\u9fff]")


def strip_think_tags(text: str) -> str:
    text = re.sub(r"<think>[\s\S]*?</think>", "", text)
    text = re.sub(r"<think>[\s\S]*", "", text)
    return text.strip()


def contains_japanese(text: str) -> bool:
    return bool(_jp_pattern.search(text))


def katakana_to_hiragana(text: str) -> str:
    chars: list[str] = []
    for char in text:
        code = ord(char)
        if 0x30A1 <= code <= 0x30F6:
            chars.append(chr(code - 0x60))
        else:
            chars.append(char)
    return "".join(chars)


def normalize_japanese_text(text: str) -> str:
    lowered = katakana_to_hiragana(text or "").lower()
    lowered = lowered.replace("　", "")
    lowered = _punct_pattern.sub("", lowered)
    return lowered


def extract_japanese_words(text: str) -> list[str]:
    if not text:
        return []

    if _tagger:
        try:
            words: list[str] = []
            for token in _tagger(text):
                pos = token.feature.pos1 if token.feature.pos1 else ""
                if pos in _skip_pos:
                    continue
                lemma = token.feature.lemma if token.feature.lemma else token.surface
                if contains_japanese(lemma):
                    words.append(lemma)
            if words:
                return words
        except Exception:
            pass

    return _jp_pattern.findall(text)


def similarity_score(expected: str, heard: str) -> int:
    expected_norm = normalize_japanese_text(expected)
    heard_norm = normalize_japanese_text(heard)
    if not expected_norm or not heard_norm:
        return 0
    ratio = difflib.SequenceMatcher(None, expected_norm, heard_norm).ratio()
    return int(round(ratio * 100))


def pronunciation_feedback(expected: str, heard: str) -> tuple[int, str]:
    expected_norm = normalize_japanese_text(expected)
    heard_norm = normalize_japanese_text(heard)
    score = similarity_score(expected, heard)

    if not heard_norm:
        return 0, "I could not hear a clear repeat. Try saying the whole line once, a little slower."

    if expected_norm == heard_norm:
        return 100, "That was spot on. Keep the same rhythm and say it a touch more confidently."

    if score >= 90:
        return score, "Very close. Your wording matched well, so focus on smoother rhythm on the next try."

    if score >= 75:
        return score, "Close, but part of the line changed. Slow down and copy the sentence chunk by chunk."

    matcher = difflib.SequenceMatcher(None, expected_norm, heard_norm)
    mismatch_note = "A few sounds or words shifted away from the target."
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        expected_chunk = expected_norm[i1:i2]
        heard_chunk = heard_norm[j1:j2]
        if tag == "delete":
            mismatch_note = f"You dropped this part near the middle: {expected_chunk}"
        elif tag == "insert":
            mismatch_note = f"You added an extra bit here: {heard_chunk}"
        else:
            mismatch_note = f"This part changed: expected {expected_chunk}, heard {heard_chunk}"
        break

    return score, f"{mismatch_note} Repeat more slowly and match the original rhythm first."


def join_known_patterns(pattern_counts: dict[str, int], limit: int = 20) -> str:
    items = sorted(pattern_counts.items(), key=lambda item: item[1], reverse=True)
    top = [word for word, _ in items[:limit]]
    return ", ".join(top) if top else "none yet"


def count_unique_words(words: Iterable[str]) -> int:
    return len({word for word in words if word})

