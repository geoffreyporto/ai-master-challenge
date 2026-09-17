"""README: nenhum número digitado à mão."""

from __future__ import annotations

import re

from support_redesign.config import README_FILE

MARK = re.compile(r"<!--m:([a-z0-9_]+)-->([^\s|*)]+)")


def test_every_marked_number_matches_the_pipeline(metrics):
    """@principle:P-003"""
    text = README_FILE.read_text()
    marks = MARK.findall(text)
    assert len(marks) >= 15, "README sem números marcados"
    report = metrics["report"]
    wrong = [
        (k, v, report.get(k)) for k, v in marks if report.get(k) != v.rstrip(".,;:")
    ]
    assert not wrong, f"números divergentes (chave, README, pipeline): {wrong}"
