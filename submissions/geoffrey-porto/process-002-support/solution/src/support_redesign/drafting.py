"""Rascunho de primeira resposta: máscara → LLM → guardrail (feature rascunho-resposta).

Este módulo só produz texto para o agente revisar; não existe função de envio.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, Literal

from support_redesign.config import PIONEER_LLM
from support_redesign.pioneer import PioneerClient
from support_redesign.privacy import guard, mask

SYSTEM = (
    "You are a support agent assistant. Write a short, polite first reply (max 90 words) "
    "to the customer ticket. Placeholders like [PERSON] or [EMAIL] stand for private data: "
    "never guess or invent names, emails, phone numbers or addresses. Do not greet by "
    "name, do not sign, and do not mention job titles, roles or team names. Ask for the "
    "missing details you need. Do not promise refunds or access changes: say that we "
    "will confirm the next steps."
)


@dataclass(frozen=True)
class Draft:
    status: Literal["requer_aprovacao"]
    model: str
    queue: str
    masked_input: str
    text: str
    guardrail_ok: bool
    guardrail_entities: list[dict[str, Any]]
    tokens: int
    client_ms: float

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def build_messages(
    masked_text: str, queue: str, similar: Sequence[str]
) -> list[dict[str, str]]:
    context = "\n".join(f"- {s[:200]}" for s in similar[:3]) or "- (none)"
    user = (
        f"Predicted queue: {queue}\n"
        f"Similar past tickets (context only):\n{context}\n\n"
        f"Customer ticket:\n{masked_text}"
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def draft_reply(
    client: PioneerClient, text: str, queue: str, similar: Sequence[str]
) -> Draft:
    masked = mask(
        client, text
    )  # se falhar, a exceção sobe e o LLM não é chamado (P-013)
    out = client.chat(PIONEER_LLM, build_messages(masked.text, queue, similar))
    verdict = guard(client, out["content"]) if out["content"] else None
    return Draft(
        status="requer_aprovacao",
        model=PIONEER_LLM,
        queue=queue,
        masked_input=masked.text,
        text=out["content"],
        guardrail_ok=bool(out["content"]) and verdict is not None and not verdict.found,
        guardrail_entities=verdict.entities if verdict else [],
        tokens=out["tokens"],
        client_ms=out["client_ms"],
    )


def draft_report(
    rows: Sequence[dict[str, Any]], drafts: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    leaks = 0
    for r in rows:
        d = drafts[str(r["Ticket ID"])]
        blob = d["text"] + d["masked_input"]
        leaks += r["Customer Name"] in blob or r["Customer Email"] in blob
    values = [drafts[str(r["Ticket ID"])] for r in rows]
    ms = sorted(d["client_ms"] for d in values)
    return {
        "n": len(rows),
        "pii_leaks": leaks,
        "guardrail_pass_rate": sum(d["guardrail_ok"] for d in values) / len(values),
        "empty_drafts": sum(not d["text"] for d in values),
        "median_client_ms": ms[len(ms) // 2],
        "tokens_total": sum(d["tokens"] for d in values),
        "all_require_approval": all(d["status"] == "requer_aprovacao" for d in values),
    }
