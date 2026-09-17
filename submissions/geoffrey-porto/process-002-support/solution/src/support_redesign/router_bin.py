"""Lançador do roteador Rust pré-compilado: `python -m support_redesign.router_bin`.

Escolhe o binário de `router/dist/` para o sistema e a CPU atuais — o avaliador
não precisa de Rust nem de `cargo`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from support_redesign.config import SOLUTION_ROOT

DIST = SOLUTION_ROOT / "router" / "dist"
MODEL = DIST / "router_model.json.gz"
DEFAULT_ADDR = "127.0.0.1:8080"
_ARCH = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x86_64", "amd64": "x86_64"}
_OS = {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}
STARTED: list[subprocess.Popen[bytes]] = []


class NoBinaryError(RuntimeError):
    """Não há binário pronto para esta plataforma."""


def platform_dir(system: str | None = None, machine: str | None = None) -> str:
    os_name = _OS.get(system or platform.system())
    arch = _ARCH.get((machine or platform.machine()).lower())
    if not os_name or not arch:
        raise NoBinaryError(f"plataforma sem binário: {system} {machine}")
    return f"{os_name}-{arch}"


def binary_path(system: str | None = None, machine: str | None = None) -> Path:
    name = (
        "support-router.exe"
        if (system or platform.system()) == "Windows"
        else "support-router"
    )
    path = DIST / platform_dir(system, machine) / name
    if not path.is_file():
        raise NoBinaryError(f"binário ausente: {path}")
    return path


def checksums() -> dict[str, str]:
    lines = (DIST / "SHA256SUMS").read_text().splitlines()
    return {
        name.strip(): digest for digest, name in (ln.split(maxsplit=1) for ln in lines)
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def health(addr: str = DEFAULT_ADDR, timeout: float = 0.5) -> dict | None:
    try:
        with urllib.request.urlopen(f"http://{addr}/health", timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read())
    except urllib.error.URLError, TimeoutError, ValueError, ConnectionError:
        return None


def start(addr: str = DEFAULT_ADDR, wait_s: float = 20.0) -> subprocess.Popen[bytes]:
    """Inicia o binário em segundo plano e espera o /health responder."""
    binary = binary_path()
    if os.name != "nt" and not os.access(binary, os.X_OK):
        binary.chmod(0o755)
    proc = subprocess.Popen(
        [str(binary), "--model", str(MODEL), "--addr", addr],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    STARTED.append(proc)
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        if health(addr):
            return proc
        if proc.poll() is not None:
            err = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
            raise RuntimeError(f"roteador saiu com código {proc.returncode}: {err}")
        time.sleep(0.2)
    proc.terminate()
    raise TimeoutError(f"roteador não respondeu em {wait_s}s")


def ensure_running(addr: str = DEFAULT_ADDR) -> tuple[bool, str]:
    """(no ar?, mensagem). Nunca levanta exceção: o app segue sem o Rust."""
    if health(addr):
        return True, f"roteador já estava no ar em {addr}"
    try:
        start(addr)
    except (NoBinaryError, RuntimeError, TimeoutError, OSError) as err:
        return False, (
            f"{err}. Compile com: cargo +1.98.1 run --release "
            "--manifest-path router/Cargo.toml"
        )
    return True, f"roteador iniciado em {addr} ({platform_dir()})"


def stop_started() -> None:
    while STARTED:
        proc = STARTED.pop()
        proc.terminate()
        proc.wait(timeout=10)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--addr", default=DEFAULT_ADDR)
    args = parser.parse_args()
    binary = binary_path()
    expected = checksums().get(str(binary.relative_to(DIST)).replace(os.sep, "/"))
    if expected != sha256(binary):
        sys.exit(f"checksum não confere para {binary}")
    print(f"roteador {platform_dir()} em http://{args.addr} (Ctrl+C para parar)")
    try:
        subprocess.run(
            [str(binary), "--model", str(MODEL), "--addr", args.addr], check=False
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
