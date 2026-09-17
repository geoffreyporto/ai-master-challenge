"""`python -m support_redesign [--pioneer]`: roda o pipeline inteiro."""

from __future__ import annotations

import argparse
import json

from support_redesign.pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pioneer",
        action="store_true",
        help="chama o GLiNER2 no Pioneer para o hold-out (usa cache)",
    )
    args = parser.parse_args()
    artifacts = run(use_pioneer=args.pioneer)
    print(json.dumps(artifacts.metrics["report"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
