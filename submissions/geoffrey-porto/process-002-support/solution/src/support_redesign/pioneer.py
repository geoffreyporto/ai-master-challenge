"""Transporte do Pioneer: autenticação, retentativas e cache. Sem IDs de modelo (P-012).

Medido em 2026-09-16: modelos grandes respondem 503 enquanto aquecem (usar
Retry-After); classificação só devolve top-1 + confiança; o LLM gasta tokens
raciocinando antes de responder (max_tokens precisa de folga).
"""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx

from support_redesign.config import SOLUTION_ROOT

BASE_URL = "https://api.pioneer.ai"
_ENV_LINE = re.compile(r"^\s*PIONEER_API_KEY\s*[:=]\s*['\"]?([^'\"\s]+)", re.MULTILINE)
RETRY_STATUS = {429, 500, 502, 503, 504}
DEFAULT_ENV_FILE = SOLUTION_ROOT / ".env"  # git-ignorado; nunca versionar


class PioneerKeyMissingError(RuntimeError):
    """Sem PIONEER_API_KEY nem PIONEER_ENV_FILE."""


class PioneerUnavailableError(RuntimeError):
    """Modelo não respondeu depois das retentativas."""


def load_key(default_env_file: Path = DEFAULT_ENV_FILE) -> str:
    """Ordem: PIONEER_API_KEY, arquivo em PIONEER_ENV_FILE, `solution/.env`."""
    if key := os.environ.get("PIONEER_API_KEY"):
        return key
    env_file = os.environ.get("PIONEER_ENV_FILE")
    candidates = [Path(env_file)] if env_file else [default_env_file]
    for path in candidates:
        if path.is_file() and (m := _ENV_LINE.search(path.read_text())):
            return m.group(1)
    raise PioneerKeyMissingError(
        "Defina PIONEER_API_KEY, PIONEER_ENV_FILE ou crie solution/.env "
        "com a linha PIONEER_API_KEY=..."
    )


class PioneerClient:
    def __init__(self, key: str | None = None, retries: int = 8, timeout: float = 90.0):
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers={"X-API-Key": key or load_key()},
            timeout=timeout,
            limits=httpx.Limits(max_connections=64, max_keepalive_connections=64),
        )
        self.retries = retries

    def close(self) -> None:
        self._http.close()

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(self.retries):
            try:
                resp = self._http.post(path, json=payload)
            except httpx.TransportError:
                time.sleep(min(2**attempt, 30))
                continue
            if resp.status_code in (402, 403):
                raise RuntimeError(
                    f"Pioneer sem crédito/permissão ({resp.status_code})"
                )
            if resp.status_code in RETRY_STATUS:
                time.sleep(float(resp.headers.get("retry-after", min(2**attempt, 30))))
                continue
            resp.raise_for_status()
            return resp.json()
        raise PioneerUnavailableError(
            f"{payload.get('model_id') or payload.get('model')}"
        )

    def infer(self, model_id: str, text: str, schema: dict[str, Any]) -> dict[str, Any]:
        start = time.perf_counter()
        out = self._post(
            "/inference",
            {"model_id": model_id, "text": text, "schema": schema, "store": False},
        )
        out["client_ms"] = 1000 * (time.perf_counter() - start)
        return out

    def chat(
        self, model: str, messages: list[dict[str, str]], max_tokens: int = 1200
    ) -> dict[str, Any]:
        start = time.perf_counter()
        out = self._post(
            "/v1/chat/completions",
            {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "store": False,
            },
        )
        return {
            "content": (out["choices"][0]["message"].get("content") or "").strip(),
            "finish_reason": out["choices"][0].get("finish_reason"),
            "tokens": int(out.get("usage", {}).get("total_tokens", 0)),
            "client_ms": 1000 * (time.perf_counter() - start),
        }


def run_cached(
    items: Sequence[tuple[str, Any]],
    fn: Callable[[Any], dict[str, Any]],
    cache_file: Path,
    workers: int = 32,
    chunk: int = 500,
) -> dict[str, dict[str, Any]]:
    """Aplica `fn` a cada item ainda fora do cache; grava o cache a cada bloco."""
    cache: dict[str, dict[str, Any]] = {}
    if cache_file.is_file():
        cache = json.loads(cache_file.read_text())
    todo = [(k, v) for k, v in items if k not in cache]
    if todo:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(workers) as pool:
            for start in range(0, len(todo), chunk):
                batch = todo[start : start + chunk]
                for k, res in zip(
                    (k for k, _ in batch),
                    pool.map(lambda kv: fn(kv[1]), batch),
                    strict=True,
                ):
                    cache[k] = res
                cache_file.write_text(
                    json.dumps(dict(sorted(cache.items())), ensure_ascii=False)
                )
    return {k: cache[k] for k, _ in items}
