"""CLI: `uv run python -m churn_diag [--data-dir DIR] [--out DIR] [--top N]`."""

from __future__ import annotations

import argparse
from pathlib import Path

from churn_diag.config import CS_TOP_N, DEFAULT_OUT_DIR, Settings, resolve_data_dir
from churn_diag.pipeline import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico de churn RavenStack")
    parser.add_argument(
        "--data-dir", help="pasta com os 5 CSVs (ou RAVENSTACK_DATA_DIR)"
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="pasta de saída")
    parser.add_argument(
        "--top", type=int, default=CS_TOP_N, help="contas na lista do CS"
    )
    args = parser.parse_args(argv)
    settings = Settings(resolve_data_dir(args.data_dir), Path(args.out), args.top)
    result = run(settings)
    r = result.report
    print(f"✔ outputs em {settings.out_dir}")
    print(
        f"  churn de MRR: {r['mrr_churn_ref_avg_pct']}%/mês (jan–set) → "
        f"{r['mrr_churn_dec24_pct']}% (dez/24)"
    )
    print(f"  4º tri: {r['q4_ratio_x']}× o esperado pelo mix de idade")
    print(
        f"  lista do CS: {r['cs_top_n']} contas, US$ {r['cs_top_expected_loss_k']:.0f} mil "
        "de MRR em risco em 90 dias"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
