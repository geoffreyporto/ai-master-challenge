"""Pytest → TAP para o onp-spec (sem dependência extra).

O `onp-spec verify` lê linhas TAP (`ok N - título`) e procura `@spec:AC-xxx` /
`@principle:P-xxx` no título. Aqui o título = nodeid + tags extraídas da
docstring do teste. Com `--tap`, as linhas saem no fim da sessão (depois do
progresso do pytest, para não quebrar a linha).
"""

from __future__ import annotations

import re

import pytest

from churn_diag.config import DataDirNotFoundError, resolve_data_dir
from churn_diag.loader import Tables, load_tables

TAG_RE = re.compile(r"@(?:spec:AC|principle:P)-\d{3,}")
_RANK = {"skipped": 0, "passed": 1, "failed": 2}


class TapEmitter:
    """Plugin: guarda o pior resultado por teste e imprime TAP no final."""

    def __init__(self) -> None:
        self.titles: dict[str, str] = {}
        self.results: dict[str, str] = {}

    def pytest_collection_modifyitems(self, items: list[pytest.Item]) -> None:
        for item in items:
            doc = getattr(getattr(item, "obj", None), "__doc__", None) or ""
            tags = " ".join(dict.fromkeys(TAG_RE.findall(doc)))
            self.titles[item.nodeid] = f"{item.nodeid} {tags}".strip()

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when != "call" and report.outcome == "passed":
            return  # setup/teardown ok não decidem nada
        prev = self.results.get(report.nodeid)
        if prev is None or _RANK[report.outcome] > _RANK[prev]:
            self.results[report.nodeid] = report.outcome

    def pytest_terminal_summary(self, terminalreporter) -> None:
        write = terminalreporter.write_line
        write("TAP version 13")
        write(f"1..{len(self.results)}")
        for n, (nodeid, outcome) in enumerate(self.results.items(), start=1):
            title = self.titles.get(nodeid, nodeid)
            status = "not ok" if outcome == "failed" else "ok"
            skip = " # SKIP" if outcome == "skipped" else ""
            write(f"{status} {n} - {title}{skip}")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--tap", action="store_true", help="emite TAP para o onp-spec")


def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--tap"):
        config.pluginmanager.register(TapEmitter(), "tap-emitter")


@pytest.fixture(scope="session")
def real_tables() -> Tables:
    """As tabelas reais. Sem os CSVs, o teste FALHA (skip não é prova)."""
    try:
        return load_tables(resolve_data_dir())
    except DataDirNotFoundError as exc:
        pytest.fail(str(exc))
