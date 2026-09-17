#!/usr/bin/env bash
# Gera os binários prontos do roteador em dist/ (só na máquina do autor).
# macOS: rustup nativo. Linux (musl estático) e Windows (gnu): container oficial rust.
# O modelo dist/router_model.json.gz vem do pipeline (`python -m support_redesign`).
set -euo pipefail
cd "$(dirname "$0")"

TC=1.98.1
DIST=dist
IMAGE="rust:${TC}"

[[ -f "$DIST/router_model.json.gz" ]] || { echo "rode o pipeline antes (falta $DIST/router_model.json.gz)"; exit 1; }

rustup toolchain install "$TC" --profile minimal -t aarch64-apple-darwin -t x86_64-apple-darwin
for target in aarch64-apple-darwin x86_64-apple-darwin; do
  cargo "+$TC" build --release --locked --bin support-router --target "$target"
done

docker run --rm --platform linux/amd64 -v "$PWD":/src -w /src \
  -e CARGO_TARGET_DIR=/src/target/docker-amd64 "$IMAGE" bash -euc '
    apt-get update -qq && apt-get install -y -qq gcc-mingw-w64-x86-64 >/dev/null
    rustup target add x86_64-unknown-linux-musl x86_64-pc-windows-gnu
    cargo build --release --locked --bin support-router --target x86_64-unknown-linux-musl
    cargo build --release --locked --bin support-router --target x86_64-pc-windows-gnu'

docker run --rm --platform linux/arm64 -v "$PWD":/src -w /src \
  -e CARGO_TARGET_DIR=/src/target/docker-arm64 "$IMAGE" bash -euc '
    rustup target add aarch64-unknown-linux-musl
    cargo build --release --locked --bin support-router --target aarch64-unknown-linux-musl'

place() {  # origem destino
  mkdir -p "$(dirname "$2")"
  rm -f "$2"  # arquivo novo: sobrescrever no lugar invalida a assinatura em cache do macOS (SIGKILL)
  cp "$1" "$2"
  chmod +x "$2"
}
place target/aarch64-apple-darwin/release/support-router "$DIST/macos-arm64/support-router"
place target/x86_64-apple-darwin/release/support-router "$DIST/macos-x86_64/support-router"
place target/docker-amd64/x86_64-unknown-linux-musl/release/support-router "$DIST/linux-x86_64/support-router"
place target/docker-arm64/aarch64-unknown-linux-musl/release/support-router "$DIST/linux-arm64/support-router"
place target/docker-amd64/x86_64-pc-windows-gnu/release/support-router.exe "$DIST/windows-x86_64/support-router.exe"

(cd "$DIST" && shasum -a 256 router_model.json.gz */support-router* > SHA256SUMS)
cat "$DIST/SHA256SUMS"
