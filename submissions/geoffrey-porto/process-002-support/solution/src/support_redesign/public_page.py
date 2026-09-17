"""Dados da página estática da Vercel, derivados só de `outputs/metrics.json` (P-003)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from support_redesign.config import ASSUMPTIONS_FILE, SOLUTION_ROOT
from support_redesign.roi import load_assumptions

PUBLIC_DATA = SOLUTION_ROOT / "router" / "public" / "data.json"
LINKS = {
    "app": "https://support-redesign-g4.streamlit.app",
    "pr": "https://github.com/Gestao-Quatro-Ponto-Zero/ai-master-challenge/pull/130",
    "codigo": "https://github.com/geoffreyporto/ai-master-challenge/tree/submission/"
    "geoffrey-porto/submissions/geoffrey-porto/process-002-support",
}


def build(metrics: dict[str, Any], assumptions: dict[str, Any]) -> dict[str, Any]:
    test = metrics["classifier"]["test"]
    bench = [
        {
            "modelo": v["model"],
            "n": v["n"],
            "macro_f1": v["macro_f1"],
            "acuracia": v["accuracy"],
        }
        for v in test.values()
    ]
    hosted = metrics.get("hosted")
    if hosted:
        llm = hosted["llm_sample"]["llm"]
        bench.append(
            {
                "modelo": f"{llm['model']} (amostra)",
                "n": llm["n"],
                "macro_f1": llm["macro_f1"],
                "acuracia": llm["accuracy"],
            }
        )
    bt = metrics["boundary"]["test"]
    return {
        "report": metrics["report"],
        "benchmark": bench,
        "boundary": {
            "coverage_auto": bt["coverage_auto"],
            "precision_auto": bt["precision_auto"],
            "human_share": bt["human_share"],
            "risk_coverage": metrics["boundary"]["risk_coverage"],
            "human_examples": metrics["boundary"]["human_examples"],
        },
        "roi": {
            "tickets_per_year": assumptions["tickets_per_year"]["valor"],
            "triage_minutes": assumptions["triage_minutes_per_ticket"]["valor"]["base"],
            "rework_minutes": assumptions["rework_minutes_per_misroute"]["valor"][
                "base"
            ],
            "cost_per_hour": assumptions["loaded_cost_brl_per_hour"]["valor"]["base"],
            "coverage_auto": bt["coverage_auto"],
            "precision_auto": bt["precision_auto"],
            "bands": metrics["roi"],
        },
        "links": LINKS,
    }


def write(metrics_file: Path, out: Path = PUBLIC_DATA) -> None:
    metrics = json.loads(metrics_file.read_text())
    data = build(metrics, load_assumptions(ASSUMPTIONS_FILE))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
