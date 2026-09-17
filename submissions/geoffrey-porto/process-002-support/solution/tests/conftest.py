"""Pytest → TAP para o onp-spec e fixtures com os dados reais.

`onp-spec verify` lê linhas TAP e procura `@spec:AC-xxx` / `@principle:P-xxx`
no título; o título é o nodeid + as tags da docstring do teste.
"""

from __future__ import annotations

import json
import re
import socket
from typing import Any

import polars as pl
import pytest

from support_redesign.config import OUTPUTS_DIR, DataDirNotFoundError, resolve_data_dir
from support_redesign.io import Split, load_d1, load_d2, split_d2

TAG_RE = re.compile(r"@(?:spec:AC|principle:P)-\d{3,}")
_RANK = {"skipped": 0, "passed": 1, "failed": 2}


def free_addr() -> str:
    """Porta livre escolhida pelo sistema, para o teste não colidir com nada."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return f"127.0.0.1:{s.getsockname()[1]}"


class TapEmitter:
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
            return
        prev = self.results.get(report.nodeid)
        if prev is None or _RANK[report.outcome] > _RANK[prev]:
            self.results[report.nodeid] = report.outcome

    def pytest_terminal_summary(self, terminalreporter) -> None:
        write = terminalreporter.write_line
        write("TAP version 13")
        write(f"1..{len(self.results)}")
        for n, (nodeid, outcome) in enumerate(self.results.items(), start=1):
            status = "not ok" if outcome == "failed" else "ok"
            skip = " # SKIP" if outcome == "skipped" else ""
            write(f"{status} {n} - {self.titles.get(nodeid, nodeid)}{skip}")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--tap", action="store_true", help="emite TAP para o onp-spec")


def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--tap"):
        config.pluginmanager.register(TapEmitter(), "tap-emitter")


def _data_dir():
    try:
        return resolve_data_dir()
    except DataDirNotFoundError as exc:  # sem dados o teste FALHA: skip não é prova
        pytest.fail(str(exc))


@pytest.fixture(scope="session")
def d1() -> pl.DataFrame:
    return load_d1(_data_dir())


@pytest.fixture(scope="session")
def d2() -> pl.DataFrame:
    return load_d2(_data_dir())


@pytest.fixture(scope="session")
def split(d2: pl.DataFrame) -> Split:
    return split_d2(d2)


@pytest.fixture(scope="session")
def metrics() -> dict[str, Any]:
    """Roda o pipeline inteiro uma vez por sessão: a prova vem de uma execução fresca."""
    from support_redesign.pipeline import run

    run()
    return json.loads((OUTPUTS_DIR / "metrics.json").read_text())


@pytest.fixture(scope="session")
def production(metrics: dict[str, Any]) -> dict[str, Any]:
    import pickle

    with (OUTPUTS_DIR / "models" / "b0.pkl").open("rb") as fh:
        return pickle.load(fh)  # noqa: S301 — artefato gerado pelo próprio pipeline
