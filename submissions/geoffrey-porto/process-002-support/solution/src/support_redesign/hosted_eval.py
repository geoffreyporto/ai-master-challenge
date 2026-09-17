"""Avaliação dos modelos hospedados no Pioneer, com cache em outputs/pioneer/.

O cliente só é criado se algum cache estiver incompleto; com os caches
presentes, o pipeline e os testes rodam sem chave e sem rede.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from support_redesign import boundary, drafting, hosted, privacy
from support_redesign.boundary import Decision
from support_redesign.classifier import TfidfLR
from support_redesign.config import DRAFT_SAMPLE_SIZE, TARGET_PRECISION
from support_redesign.pioneer import PioneerClient, run_cached

GUARD_PROBES = {
    "limpo": "Thank you for reaching out. We will confirm the next steps shortly.",
    "com_pii": "Please call John Carter at +1 555 010 7788 or write to jcarter@example.org.",
}


@dataclass
class HostedInputs:
    clf: TfidfLR
    split_val: pl.DataFrame
    split_test: pl.DataFrame
    dec_val: Sequence[Decision]
    dec_test: Sequence[Decision]
    y_val: np.ndarray
    y_test: np.ndarray
    d1: pl.DataFrame
    similar: Callable[[str], list[str]]


class HostedCacheIncompleteError(RuntimeError):
    """Faltam resultados hospedados no cache e a rede não foi autorizada."""


class LazyClient:
    def __init__(self, offline: bool = False) -> None:
        self._client: PioneerClient | None = None
        self.offline = offline

    def __call__(self) -> PioneerClient:
        if self.offline:
            raise HostedCacheIncompleteError(
                "Cache do Pioneer incompleto para este modelo; rode "
                "`python -m support_redesign --pioneer` (com chave) para completar."
            )
        if self._client is None:
            self._client = PioneerClient()
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()


def run_hosted(
    inp: HostedInputs, cache_dir: Path, offline: bool = False
) -> dict[str, Any]:
    get = LazyClient(offline)
    try:
        return _run(inp, cache_dir, get)
    finally:
        get.close()


def _run(inp: HostedInputs, cache_dir: Path, get: LazyClient) -> dict[str, Any]:
    classes = inp.clf.classes_
    test, val = inp.split_test, inp.split_val
    te_ids = [str(i) for i in test["row_id"].to_list()]

    b2 = run_cached(
        list(zip(te_ids, test["Document"].to_list(), strict=True)),
        lambda t: hosted.classify(get(), t),
        cache_dir / "b2_test.json",
    )
    b2_eval = hosted.evaluate_top1(
        "B2 GLiNER2 multi-large (fallback large) zero-shot",
        [b2[i] for i in te_ids],
        test["Topic_group"].to_list(),
    )

    val_elig = boundary.second_opinion_eligible(inp.dec_val)
    val_rows = val[val_elig]
    b2_val = run_cached(
        list(
            zip(
                map(str, val_rows["row_id"].to_list()),
                val_rows["Document"].to_list(),
                strict=True,
            )
        ),
        lambda t: hosted.classify(get(), t),
        cache_dir / "b2_val_eligible.json",
    )
    val_labels = {
        i: b2_val[str(r)]["label"]
        for i, r in zip(val_elig, val_rows["row_id"], strict=True)
    }
    so_val = boundary.second_opinion(
        inp.dec_val, inp.y_val, classes, val_labels, TARGET_PRECISION
    )
    test_labels = {i: b2[k]["label"] for i, k in enumerate(te_ids)}
    so_test = boundary.second_opinion(
        inp.dec_test, inp.y_test, classes, test_labels, TARGET_PRECISION
    )
    so_test["enabled"] = so_val["enabled"]

    sample = hosted.stratified_sample(test)
    s_ids = [str(i) for i in sample["row_id"].to_list()]
    llm = run_cached(
        list(zip(s_ids, sample["Document"].to_list(), strict=True)),
        lambda t: hosted.classify_llm(get(), t),
        cache_dir / "llm_sample.json",
        workers=16,
    )
    s_labels = sample["Topic_group"].to_list()
    b0_proba = inp.clf.predict_proba(sample["Document"].to_list())
    b0_rows = [
        {
            "label": classes[int(p.argmax())],
            "confidence": float(p.max()),
            "client_ms": 0.0,
        }
        for p in b0_proba
    ]
    llm_sample = {
        "n": len(s_ids),
        "llm": hosted.evaluate_top1(
            "B3 DeepSeek-V4-Flash", [llm[i] for i in s_ids], s_labels
        ),
        "b0": hosted.evaluate_top1("B0 TF-IDF + LR", b0_rows, s_labels),
        "b2": hosted.evaluate_top1("B2 GLiNER2", [b2[i] for i in s_ids], s_labels),
    }

    pii_rows = privacy.pii_sample(inp.d1).to_dicts()
    pii_texts = {
        str(r["Ticket ID"]): privacy.with_customer_pii(
            r["Ticket Description"], r["Customer Name"], r["Customer Email"]
        )
        for r in pii_rows
    }
    masked = run_cached(
        list(pii_texts.items()),
        lambda t: {"text": (m := privacy.mask(get(), t)).text, "entities": m.entities},
        cache_dir / "masking.json",
        workers=16,
    )
    guard_probe = run_cached(
        list(GUARD_PROBES.items()),
        lambda t: {
            "found": (g := privacy.guard(get(), t)).found,
            "entities": g.entities,
        },
        cache_dir / "guard_probe.json",
    )

    draft_rows = pii_rows[:DRAFT_SAMPLE_SIZE]

    def make_draft(text: str) -> dict[str, Any]:
        queue = classes[int(inp.clf.predict_proba([text])[0].argmax())]
        return drafting.draft_reply(get(), text, queue, inp.similar(text)).to_json()

    drafts = run_cached(
        [(str(r["Ticket ID"]), pii_texts[str(r["Ticket ID"])]) for r in draft_rows],
        make_draft,
        cache_dir / "drafts.json",
        workers=8,
    )
    return {
        "b2_test": b2_eval,
        "second_opinion": {"val": so_val, "test": so_test},
        "llm_sample": llm_sample,
        "privacy": privacy.masking_recall(pii_rows, masked),
        "guard_probe": guard_probe,
        "drafts": drafting.draft_report(draft_rows, drafts),
        "draft_examples": [drafts[str(r["Ticket ID"])] for r in draft_rows[:3]],
    }
