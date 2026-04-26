from __future__ import annotations

from typing import Any

from ollama import Client

from backend.app.config import Settings
from backend.app.text_utils import strip_think_tags


class OllamaUnavailableError(RuntimeError):
    pass


class OllamaService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = Client(host=settings.ollama_host)
        self.chat_model = settings.preferred_chat_models[0]
        self.utility_model = settings.utility_model
        self.refresh_model_selection()

    def refresh_model_selection(self) -> None:
        installed = self._installed_models()
        if not installed:
            self.chat_model = self.settings.preferred_chat_models[0]
            self.utility_model = self.settings.utility_model
            return

        for candidate in self.settings.preferred_chat_models:
            if candidate in installed:
                self.chat_model = candidate
                break
        else:
            self.chat_model = installed[0]

        if self.settings.utility_model in installed:
            self.utility_model = self.settings.utility_model
        else:
            self.utility_model = self.chat_model

    def _installed_models(self) -> list[str]:
        try:
            raw = self.client.list()
        except Exception:
            return []

        if hasattr(raw, "model_dump"):
            payload = raw.model_dump()
        elif isinstance(raw, dict):
            payload = raw
        else:
            payload = {}

        models = payload.get("models", [])
        names: list[str] = []
        for item in models:
            if isinstance(item, dict):
                name = item.get("model") or item.get("name")
                if name:
                    names.append(name)
        return names

    def _extract_content(self, response: Any) -> str:
        if hasattr(response, "message"):
            message = response.message
            content = getattr(message, "content", "")
            return strip_think_tags(content)
        if isinstance(response, dict):
            message = response.get("message", {})
            return strip_think_tags(message.get("content", ""))
        return ""

    def chat(
        self,
        *,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        num_predict: int = 160,
    ) -> tuple[str, str]:
        chosen_model = model or self.chat_model
        kwargs: dict[str, Any] = {
            "model": chosen_model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        }
        try:
            response = self.client.chat(**kwargs)
        except TypeError:
            kwargs.pop("think", None)
            response = self.client.chat(**kwargs)
        except Exception as exc:
            raise OllamaUnavailableError(
                f"Could not reach Ollama at {self.settings.ollama_host}. Make sure Ollama is running."
            ) from exc

        return self._extract_content(response), chosen_model

    def single_shot(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float = 0.3,
        num_predict: int = 120,
    ) -> tuple[str, str]:
        return self.chat(
            model=model or self.utility_model,
            temperature=temperature,
            num_predict=num_predict,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

