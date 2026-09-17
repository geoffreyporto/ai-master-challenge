"""Máscara de PII antes do LLM e guardrail depois dele (feature privacidade-guardrails)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import polars as pl

from support_redesign.config import (
    PII_LABELS,
    PII_MIN_CONFIDENCE,
    PII_SAMPLE_SIZE,
    PIONEER_GUARDRAIL,
    PIONEER_PRIVACY,
    SEED,
)
from support_redesign.pioneer import PioneerClient

SCHEMA = {"entities": list(PII_LABELS)}
OUR_PLACEHOLDER = re.compile(r"^\[[A-Z_]+\]$")
PRONOUNS = frozenset(
    "i me my mine you your yours yourself we us our ours he him his she her hers "
    "they them their theirs it its".split()
)


@dataclass(frozen=True)
class PiiScan:
    text: str
    entities: list[dict[str, Any]] = field(default_factory=list)

    @property
    def found(self) -> bool:
        return bool(self.entities)


def _spans(out: dict[str, Any]) -> list[dict[str, Any]]:
    spans = []
    for label, items in (out.get("result", {}).get("entities") or {}).items():
        for it in items:
            conf = float(it.get("confidence", 0.0))
            ignored = (
                OUR_PLACEHOLDER.match(it["text"])
                or it["text"].strip().lower() in PRONOUNS
            )
            if conf >= PII_MIN_CONFIDENCE and not ignored:
                spans.append(
                    {
                        "label": label,
                        "start": int(it["start"]),
                        "end": int(it["end"]),
                        "text": it["text"],
                        "confidence": round(conf, 3),
                    }
                )
    return sorted(spans, key=lambda s: s["start"])


def mask(client: PioneerClient, text: str) -> PiiScan:
    """Troca cada span de PII por `[RÓTULO]`. Erro aqui impede qualquer envio ao LLM."""
    spans = _spans(client.infer(PIONEER_PRIVACY, text, SCHEMA))
    out, cursor = [], 0
    for s in spans:
        if s["start"] < cursor:
            continue
        out.append(text[cursor : s["start"]])
        out.append(f"[{s['label'].upper().replace(' ', '_')}]")
        cursor = s["end"]
    out.append(text[cursor:])
    return PiiScan("".join(out), [{"label": s["label"]} for s in spans])


def guard(client: PioneerClient, text: str) -> PiiScan:
    """Guardrail de saída: qualquer PII encontrada bloqueia o rascunho."""
    spans = _spans(client.infer(PIONEER_GUARDRAIL, text, SCHEMA))
    return PiiScan(
        text,
        [
            {"label": s["label"], "text": s["text"], "confidence": s["confidence"]}
            for s in spans
        ],
    )


def with_customer_pii(description: str, name: str, email: str) -> str:
    return f"Hello, my name is {name} and you can reach me at {email}. {description}"


def pii_sample(
    d1: pl.DataFrame, n: int = PII_SAMPLE_SIZE, seed: int = SEED
) -> pl.DataFrame:
    return d1.sample(n=n, seed=seed, shuffle=True).select(
        "Ticket ID", "Customer Name", "Customer Email", "Ticket Description"
    )


def masking_recall(
    rows: list[dict[str, Any]], masked: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    names = [
        r["Customer Name"] not in masked[str(r["Ticket ID"])]["text"] for r in rows
    ]
    emails = [
        r["Customer Email"] not in masked[str(r["Ticket ID"])]["text"] for r in rows
    ]
    return {
        "n": len(rows),
        "name_recall": sum(names) / len(rows),
        "email_recall": sum(emails) / len(rows),
    }
