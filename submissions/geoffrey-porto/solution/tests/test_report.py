"""Rastreabilidade do relatório: nenhum número marcado é digitado à mão (P-003).

Marcação no RELATORIO.md: `<!--m:chave-->valor` (formato pt-BR: ponto = milhar,
vírgula = decimal). O valor exibido pode ser arredondado, nunca inventado: a
tolerância é meia unidade da última casa exibida.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import polars as pl
import pytest

from churn_diag.config import CS_TOP_N, SOLUTION_ROOT
from churn_diag.loader import Tables
from churn_diag.pipeline import Result, analyse

REPORT = SOLUTION_ROOT / "RELATORIO.md"
SUBMISSION_README = SOLUTION_ROOT.parent / "README.md"
FEATURE_MATRIX = SOLUTION_ROOT.parent / "docs" / "04-matriz-de-features.md"
DML_DOC = SOLUTION_ROOT.parent / "docs" / "06-casos-dml.md"
QUESTIONS_DOC = SOLUTION_ROOT.parent / "docs" / "07-perguntas-incomodas.md"
METRICS = SOLUTION_ROOT / "outputs" / "metrics.json"
MARK = re.compile(r"<!--m:([a-z0-9_]+)-->\s*(?:US\$\s*)?([−-]?\d[\d.]*(?:,\d+)?)")
TOP10 = re.compile(r"<!--top10:start-->(.*?)<!--top10:end-->", re.S)


def parse_br(raw: str) -> tuple[float, int]:
    """'1.234,5' → (1234.5, 1 casa); '−83,2' → (-83.2, 1)."""
    raw = raw.replace("−", "-")
    decimals = len(raw.split(",")[1]) if "," in raw else 0
    return float(raw.replace(".", "").replace(",", ".")), decimals


@pytest.fixture(scope="module")
def fresh(real_tables: Tables) -> Result:
    return analyse(real_tables, CS_TOP_N)


def test_parse_br_handles_thousands_and_decimals() -> None:
    """@spec:AC-018 — o parser entende o formato pt-BR do relatório."""
    assert parse_br("10.160") == (10160.0, 0)
    assert parse_br("0,83") == (0.83, 2)
    assert parse_br("−83,2") == (-83.2, 1)


@pytest.mark.parametrize(
    ("doc", "min_marks"),
    [
        (REPORT, 60),
        (SUBMISSION_README, 15),
        (FEATURE_MATRIX, 15),
        (DML_DOC, 8),
        (QUESTIONS_DOC, 60),
    ],
)
def test_every_marked_number_matches_the_pipeline(
    fresh: Result, doc: Path, min_marks: int
) -> None:
    """@spec:AC-018 @principle:P-003 — cada número marcado = valor do pipeline."""
    text = doc.read_text(encoding="utf-8")
    marks = MARK.findall(text)
    assert len(marks) >= min_marks, f"{doc.name} deveria marcar os números-chave"
    committed = json.loads(METRICS.read_text(encoding="utf-8"))["report"]
    assert committed == fresh.report, (
        "outputs/metrics.json desatualizado: rode o pipeline"
    )
    wrong = []
    for key, raw in marks:
        assert key in fresh.report, f"chave inexistente no pipeline: {key}"
        value, decimals = parse_br(raw)
        if abs(value - fresh.report[key]) > 0.5 * 10**-decimals + 1e-9:
            wrong.append(f"{key}: relatório {raw} ≠ pipeline {fresh.report[key]}")
    assert not wrong, "\n".join(wrong)


def test_top10_table_matches_cs_list(fresh: Result) -> None:
    """@spec:AC-018 @principle:P-003 — a tabela das 10 contas é a lista do CS."""
    block = TOP10.search(REPORT.read_text(encoding="utf-8")).group(1)
    rows = [r for r in block.splitlines() if re.match(r"\|\s*\d+\s*\|", r)]
    ids = [re.search(r"`(A-[0-9a-f]+)`", r).group(1) for r in rows]
    losses = [parse_br(r.rstrip(" |").split("|")[-1].strip())[0] for r in rows]
    top = fresh.tables["cs_priority_accounts"].head(10)
    assert ids == top["account_id"].to_list()
    assert losses == top["expected_loss_90d"].cast(pl.Float64).to_list()
