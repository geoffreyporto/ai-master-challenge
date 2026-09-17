"""Normalização e analisador de n-gramas compartilhados por treino, app e roteador.

O roteador Rust reimplementa exatamente estas regras (router/src/model.rs); a
paridade é testada no hold-out inteiro.
"""

from __future__ import annotations

import re

PLACEHOLDER_RE = re.compile(r"\{[^{}]*\}")
_NON_LETTER_RE = re.compile(r"[^a-z]+")


def normalize(text: str) -> str:
    """Minúsculas, sem {placeholders}, só letras ASCII a-z separadas por um espaço."""
    lowered = PLACEHOLDER_RE.sub(" ", text.lower())
    return _NON_LETTER_RE.sub(" ", lowered).strip()


def tokens(text: str) -> list[str]:
    return [t for t in normalize(text).split(" ") if len(t) >= 2]


def analyzer(text: str) -> list[str]:
    """Unigramas e bigramas sobre os tokens normalizados."""
    toks = tokens(text)
    return toks + [f"{a} {b}" for a, b in zip(toks, toks[1:], strict=False)]
