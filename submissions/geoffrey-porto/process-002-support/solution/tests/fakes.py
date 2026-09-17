"""Cliente Pioneer falso para testar comportamento sem rede."""

from __future__ import annotations

import re
from typing import Any

from support_redesign.pioneer import PioneerUnavailableError

EMAIL = re.compile(r"[\w.]+@[\w.]+")
NAME = re.compile(r"my name is ([A-Z][a-z]+ [A-Z][a-z]+)")


class FakeClient:
    def __init__(
        self,
        down: set[str] | None = None,
        reply: str = "We will help you.",
        fail_privacy: bool = False,
    ) -> None:
        self.down = down or set()
        self.reply = reply
        self.fail_privacy = fail_privacy
        self.calls: list[tuple[str, str]] = []

    def infer(self, model_id: str, text: str, schema: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((model_id, text))
        if model_id in self.down or (self.fail_privacy and "privacy" in model_id):
            raise PioneerUnavailableError(model_id)
        if "classifications" in schema:
            return {
                "result": {"topic_group": {"label": "hardware", "confidence": 0.9}},
                "model_used": model_id,
                "latency_ms": 1.0,
                "token_usage": 3,
            }
        ents: dict[str, list[dict[str, Any]]] = {}
        for label, rx in (("email", EMAIL), ("person", NAME)):
            for m in rx.finditer(text):
                g = 1 if label == "person" else 0
                ents.setdefault(label, []).append(
                    {
                        "text": m.group(g),
                        "start": m.start(g),
                        "end": m.end(g),
                        "confidence": 0.99,
                    }
                )
        return {"result": {"entities": ents}}

    def chat(
        self, model: str, messages: list[dict[str, str]], max_tokens: int = 1200
    ) -> dict[str, Any]:
        self.calls.append((model, "\n".join(m["content"] for m in messages)))
        return {
            "content": self.reply,
            "finish_reason": "stop",
            "tokens": 10,
            "client_ms": 5.0,
        }
