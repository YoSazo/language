from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from backend.app.config import get_settings
from backend.app.ollama_service import OllamaService, OllamaUnavailableError
from backend.app.session_types import ActiveTurn, SessionState
from backend.app.state_store import StateStore
from backend.app.stt_service import WhisperService
from backend.app.tutor import JapaneseTutor

settings = get_settings()
store = StateStore(settings)
stt = WhisperService(settings)
ollama = OllamaService(settings)
tutor = JapaneseTutor(settings, store, ollama)

app = FastAPI(title="Japanese Coach Backend")
active_sessions: dict[str, SessionState] = {}


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "ok": True,
        "chat_model": ollama.chat_model,
        "utility_model": ollama.utility_model,
        "whisper_model": settings.whisper_model_size,
        "known_words": store.known_word_count(),
        "total_words": store.total_word_count(),
    }


async def _send_json(websocket: WebSocket, payload: dict[str, object]) -> None:
    await websocket.send_text(json.dumps(payload, ensure_ascii=False))


async def _send_error(websocket: WebSocket, message: str) -> None:
    await _send_json(websocket, {"type": "error", "message": message})


async def _process_turn(websocket: WebSocket, session: SessionState, turn: ActiveTurn) -> None:
    raw_audio = b"".join(turn.audio_chunks)
    if not raw_audio:
        await _send_error(websocket, "No audio arrived for that turn.")
        return

    await _send_json(websocket, {"type": "status", "stage": "transcribing"})
    language_hint = "en" if turn.mode == "translate_help" else "ja"
    transcript = await asyncio.to_thread(stt.transcribe_pcm16, raw_audio, language_hint)
    if not transcript:
        await _send_error(websocket, "I could not hear a clear sentence. Try again a little closer to the mic.")
        return

    await _send_json(websocket, {"type": "status", "stage": "thinking"})
    try:
        if turn.mode == "conversation":
            result = await asyncio.to_thread(tutor.conversation_turn, session, transcript)
        elif turn.mode == "translate_help":
            result = await asyncio.to_thread(tutor.translate_help, session, transcript)
        elif turn.mode == "shadowing":
            target = turn.target_text or session.last_ai_text
            if not target:
                await _send_error(websocket, "There is no target line yet to shadow.")
                return
            result = await asyncio.to_thread(tutor.shadow_last_line, session, transcript, target)
        else:
            await _send_error(websocket, f"Unknown mode: {turn.mode}")
            return
    except OllamaUnavailableError as exc:
        await _send_error(websocket, str(exc))
        return

    result["knownWords"] = store.known_word_count()
    result["totalWords"] = store.total_word_count()
    await _send_json(websocket, result)
    await _send_json(websocket, {"type": "status", "stage": "idle"})


async def _handle_text_message(websocket: WebSocket, session: SessionState, payload: dict[str, object]) -> None:
    message_type = payload.get("type")

    if message_type == "hello":
        greeting = tutor.greeting()
        session.last_ai_text = greeting
        session.conversation.append({"role": "assistant", "content": greeting})
        store.update_vocab_from_text(greeting)
        await _send_json(
            websocket,
            {
                "type": "session_ready",
                "sessionId": session.session_id,
                "greeting": greeting,
                "chatModel": ollama.chat_model,
                "utilityModel": ollama.utility_model,
                "whisperModel": settings.whisper_model_size,
                "knownWords": store.known_word_count(),
                "totalWords": store.total_word_count(),
            },
        )
        return

    if message_type == "start_turn":
        mode = str(payload.get("mode", "conversation"))
        session.current_turn = ActiveTurn(
            mode=mode,
            english_hint=str(payload.get("english_hint")) if payload.get("english_hint") else None,
            target_text=str(payload.get("target_text")) if payload.get("target_text") else None,
        )
        await _send_json(websocket, {"type": "status", "stage": "listening", "mode": mode})
        return

    if message_type == "end_audio":
        if session.current_turn is None:
            await _send_error(websocket, "No active turn to finish.")
            return
        turn = session.current_turn
        session.current_turn = None
        await _process_turn(websocket, session, turn)
        return

    if message_type == "explain_last":
        try:
            await _send_json(websocket, {"type": "status", "stage": "thinking"})
            result = await asyncio.to_thread(tutor.explain_last, session)
            await _send_json(websocket, result)
            await _send_json(websocket, {"type": "status", "stage": "idle"})
        except OllamaUnavailableError as exc:
            await _send_error(websocket, str(exc))
        return

    if message_type == "repeat_last":
        await _send_json(
            websocket,
            {
                "type": "repeat_result",
                "assistantJapanese": session.last_ai_text,
            },
        )
        return

    if message_type == "ping":
        await _send_json(websocket, {"type": "pong"})
        return

    await _send_error(websocket, f"Unsupported message type: {message_type}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    session = SessionState(session_id=str(uuid.uuid4()))
    active_sessions[session.session_id] = session
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break

            text = message.get("text")
            raw_bytes = message.get("bytes")

            if text is not None:
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    await _send_error(websocket, "Malformed JSON from client.")
                    continue
                await _handle_text_message(websocket, session, payload)
                continue

            if raw_bytes is not None:
                if session.current_turn is None:
                    await _send_error(websocket, "Received audio without an active turn.")
                else:
                    session.current_turn.audio_chunks.append(raw_bytes)
    except WebSocketDisconnect:
        pass
    finally:
        active_sessions.pop(session.session_id, None)

