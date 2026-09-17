"""Binários prontos: o avaliador roda o roteador sem Rust instalado."""

from __future__ import annotations

import gzip
import json

import pytest
from conftest import free_addr

from support_redesign import router_bin
from support_redesign.pipeline import DIST_MODEL, GOLDEN_FILE, ROUTER_MODEL

PLATFORMS = {
    ("Darwin", "arm64"): "macos-arm64",
    ("Darwin", "x86_64"): "macos-x86_64",
    ("Linux", "x86_64"): "linux-x86_64",
    ("Linux", "aarch64"): "linux-arm64",
    ("Windows", "AMD64"): "windows-x86_64",
}


def test_every_supported_platform_has_a_binary():
    """@spec:AC-038"""
    for (system, machine), folder in PLATFORMS.items():
        assert router_bin.platform_dir(system, machine) == folder
        assert router_bin.binary_path(system, machine).is_file()
    with pytest.raises(router_bin.NoBinaryError):
        router_bin.platform_dir("SunOS", "sparc")


def test_shipped_files_match_checksums_and_pipeline_model(metrics):
    """@spec:AC-038 @principle:P-005"""
    sums = router_bin.checksums()
    assert set(sums) == {
        "router_model.json.gz",
        *(
            f"{f}/support-router{'.exe' if f.startswith('windows') else ''}"
            for f in PLATFORMS.values()
        ),
    }
    for name, digest in sums.items():
        assert router_bin.sha256(router_bin.DIST / name) == digest, name
    assert gzip.decompress(DIST_MODEL.read_bytes()) == ROUTER_MODEL.read_bytes()


@pytest.fixture
def served(metrics):
    addr = free_addr()
    router_bin.start(addr)
    yield addr
    router_bin.stop_started()


def test_host_binary_decides_like_python(served):
    """@spec:AC-038 @principle:P-005"""
    import urllib.request

    assert router_bin.health(served)["classes"] == 8
    lines = GOLDEN_FILE.read_text().splitlines()[:300]
    for line in lines:
        g = json.loads(line)
        req = urllib.request.Request(
            f"http://{served}/route",
            data=json.dumps({"text": g["text"]}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
            out = json.loads(resp.read())
        assert (out["topic"], out["action"]) == (g["topic"], g["action"])


def test_missing_binary_degrades_gracefully(monkeypatch):
    """@spec:AC-039"""
    monkeypatch.setattr(router_bin, "health", lambda *a, **k: None)

    def no_binary(*_a, **_k):
        raise router_bin.NoBinaryError("sem binário")

    monkeypatch.setattr(router_bin, "binary_path", no_binary)
    ok, msg = router_bin.ensure_running("127.0.0.1:18099")
    assert ok is False
    assert "cargo +1.98.1" in msg
