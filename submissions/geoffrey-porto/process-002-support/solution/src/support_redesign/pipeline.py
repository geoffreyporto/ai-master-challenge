"""Orquestra as features e grava outputs/ (métricas, artefatos do app e do roteador)."""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from support_redesign import (
    audit,
    boundary,
    cross,
    diagnosis,
    export,
    public_page,
    retrieval,
    roi,
)
from support_redesign.classifier import (
    Model2VecLR,
    TfidfLR,
    evaluate,
    label_index,
    pick_production,
)
from support_redesign.config import (
    ASSUMPTIONS_FILE,
    OUTPUTS_DIR,
    RECALL_KS,
    SEED,
    SOLUTION_ROOT,
    resolve_data_dir,
)
from support_redesign.io import load_d1, load_d2, split_d2

MODELS_DIR = OUTPUTS_DIR / "models"
GOLDEN_FILE = OUTPUTS_DIR / "golden" / "holdout.jsonl"
ROUTER_MODEL = OUTPUTS_DIR / "models" / "router_model.json"
DIST_DIR = SOLUTION_ROOT / "router" / "dist"
DIST_MODEL = DIST_DIR / "router_model.json.gz"
HOSTED_DIR = OUTPUTS_DIR / "pioneer"


def pct(x: float, digits: int = 1) -> str:
    return f"{100 * x:.{digits}f}%".replace(".", ",")


def num(x: float, digits: int = 0) -> str:
    s = f"{x:,.{digits}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


@dataclass
class Artifacts:
    metrics: dict[str, Any]
    segments: pl.DataFrame
    scored_d1: pl.DataFrame


def fit_policy_for(
    clf: TfidfLR, va_x: list[str], va_y: list[str]
) -> tuple[boundary.Policy, np.ndarray, np.ndarray]:
    p_val = clf.predict_proba(va_x)
    y_val = label_index(clf.classes_, va_y)
    policy = boundary.fit_policy(p_val, y_val, clf.classes_, clf.known_share(va_x))
    return policy, p_val, y_val


def save_serving(
    clf: TfidfLR,
    policy: boundary.Policy,
    index: retrieval.SimilarIndex,
    train: pl.DataFrame,
) -> None:
    """O que o app precisa para servir: modelo + política e o índice de similares."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with (MODELS_DIR / "b0.pkl").open("wb") as fh:
        pickle.dump({"clf": clf, "policy": policy}, fh)
    np.save(MODELS_DIR / "index_embeddings.npy", index.matrix)
    train.select("row_id", "Document", "Topic_group").write_parquet(
        MODELS_DIR / "index_rows.parquet"
    )
    (MODELS_DIR / "index_ids.json").write_text(
        json.dumps(sorted(train["row_id"].to_list()))
    )


def build_serving() -> None:
    """Bootstrap leve (ex.: Streamlit Cloud): treina só o que o app serve.

    Não recalcula métricas, benchmark nem chama o Pioneer — `metrics.json` e os
    caches hospedados já vêm versionados.
    """
    np.random.seed(SEED)
    split = split_d2(load_d2(resolve_data_dir()))
    tr_x, tr_y = split.train["Document"].to_list(), split.train["Topic_group"].to_list()
    clf = TfidfLR().fit(tr_x, tr_y)
    policy, _, _ = fit_policy_for(
        clf, split.val["Document"].to_list(), split.val["Topic_group"].to_list()
    )
    encoder = Model2VecLR()
    index = retrieval.SimilarIndex(
        encoder.embed(tr_x), tr_y, tr_x, split.train["row_id"].to_list()
    )
    save_serving(clf, policy, index, split.train)


def run(outputs: Path = OUTPUTS_DIR, use_pioneer: bool = False) -> Artifacts:
    np.random.seed(SEED)
    data_dir = resolve_data_dir()
    d1, d2 = load_d1(data_dir), load_d2(data_dir)
    split = split_d2(d2)
    tr_x, tr_y = split.train["Document"].to_list(), split.train["Topic_group"].to_list()
    va_x, va_y = split.val["Document"].to_list(), split.val["Topic_group"].to_list()
    te_x, te_y = split.test["Document"].to_list(), split.test["Topic_group"].to_list()

    audit_out = {
        "d1": audit.audit_d1(d1),
        "d2": audit.audit_d2(d2),
        "readme_divergences": audit.readme_divergences(d1),
    }
    diag = diagnosis.diagnose(d1)

    b0 = TfidfLR().fit(tr_x, tr_y)
    b1 = Model2VecLR().fit(tr_x, tr_y)
    models = {b0.name: b0, b1.name: b1}
    val_eval = {m.name: evaluate(m, va_x, va_y) for m in models.values()}
    test_eval = {m.name: evaluate(m, te_x, te_y) for m in models.values()}
    production = pick_production({k: v["macro_f1"] for k, v in val_eval.items()})
    if production != b0.name:
        raise RuntimeError(
            f"{production} venceu na validação; o roteador Rust só exporta B0."
        )
    clf = b0

    policy, p_val, y_val = fit_policy_for(clf, va_x, va_y)
    p_test = clf.predict_proba(te_x)
    y_test = label_index(clf.classes_, te_y)
    known_test = clf.known_share(te_x)
    dec_test = boundary.decide_all(policy, p_test, known=known_test)
    bound = {
        "policy": policy.to_json(),
        "test": boundary.policy_report(policy, p_test, y_test, dec_test),
        "risk_coverage": boundary.risk_coverage(p_test, y_test),
        "human_examples": boundary.human_examples(te_x, te_y, dec_test),
    }

    index = retrieval.SimilarIndex(
        b1.embed(tr_x), tr_y, tr_x, split.train["row_id"].to_list()
    )
    test_emb = b1.embed(te_x)
    retr = {
        "model": b1.name,
        "index_size": len(tr_x),
        "recall": retrieval.recall_at_k(index, test_emb, te_y, RECALL_KS),
        "chance": retrieval.chance_recall_at_k(tr_y, te_y, RECALL_KS),
        "index_ids": sorted(split.train["row_id"].to_list()),
    }

    scored_d1, _ = cross.score_d1(clf, policy, d1)
    hosted_out = None
    if use_pioneer or (HOSTED_DIR / "b2_test.json").is_file():
        from support_redesign.hosted_eval import HostedInputs, run_hosted

        dec_val = boundary.decide_all(policy, p_val, known=clf.known_share(va_x))

        def similar(text: str) -> list[str]:
            idx, _ = index.search(b1.embed([text]), 3)
            return [index.texts[i] for i in idx[0]]

        hosted_out = run_hosted(
            HostedInputs(
                clf,
                split.val,
                split.test,
                dec_val,
                dec_test,
                y_val,
                y_test,
                d1,
                similar,
            ),
            HOSTED_DIR,
            offline=not use_pioneer,
        )
        test_eval[hosted_out["b2_test"]["model"]] = hosted_out["b2_test"]

    shift = cross.domain_shift(scored_d1, p_test.max(axis=1), dec_test)
    shift["median_known_d1"] = float(scored_d1["known_share"].median() or 0.0)
    shift["median_known_d2_test"] = float(np.median(known_test))

    assumptions = roi.load_assumptions(ASSUMPTIONS_FILE)
    roi_out = roi.roi(
        assumptions, bound["test"]["coverage_auto"], bound["test"]["precision_auto"]
    )

    metrics: dict[str, Any] = {
        "split": {
            "train": split.train.height,
            "val": split.val.height,
            "test": split.test.height,
        },
        "audit": audit_out,
        "diagnosis": {k: v for k, v in diag.items() if k != "segments"},
        "classifier": {"production": production, "val": val_eval, "test": test_eval},
        "boundary": bound,
        "retrieval": {k: v for k, v in retr.items() if k != "index_ids"},
        "cross": shift,
        "roi": roi_out,
        "hosted": hosted_out,
    }
    metrics["report"] = report_numbers(metrics)

    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2)
    )
    public_page.write(outputs / "metrics.json")
    diag["segments"].write_parquet(outputs / "segments.parquet")
    scored_d1.write_parquet(outputs / "d1_scored.parquet")
    split.test.write_parquet(outputs / "d2_test.parquet")

    save_serving(clf, policy, index, split.train)
    export.export_router_model(clf, policy, ROUTER_MODEL)
    export.export_dist_model(ROUTER_MODEL, DIST_MODEL)
    export.export_golden(te_x, p_test, dec_test, GOLDEN_FILE)
    return Artifacts(metrics, diag["segments"], scored_d1)


def report_numbers(m: dict[str, Any]) -> dict[str, str]:
    """Números citados no README, já formatados (P-003)."""
    ev1 = m["audit"]["d1"]["evidence"]
    b0 = m["classifier"]["test"]["B0 TF-IDF + LR"]
    b1 = m["classifier"]["test"]["B1 Model2Vec + LR"]
    bt = m["boundary"]["test"]
    base = m["roi"]["base"]
    out = {
        "d1_rows": num(ev1["rows"]),
        "d1_negative_share": pct(ev1["negative_interval_share"]),
        "d1_placeholder_share": pct(ev1["product_placeholder_share"], 0),
        "d1_min_uniform_p": num(min(ev1["uniform_chi2_p"].values()), 2),
        "d1_min_kw_p": num(min(t["p"] for t in m["diagnosis"]["tests"].values()), 2),
        "csat_mde": num(m["diagnosis"]["mde"]["mde_points"], 2),
        "csat_max_diff": num(m["diagnosis"]["mde"]["observed_max_diff"], 2),
        "csat_pseudo_r2": num(m["diagnosis"]["ordinal"]["pseudo_r2"], 4),
        "d2_rows": num(m["audit"]["d2"]["evidence"]["rows"]),
        "test_n": num(m["split"]["test"]),
        "b0_macro_f1": num(b0["macro_f1"], 3),
        "b0_accuracy": num(b0["accuracy"], 3),
        "b0_ece": num(b0["ece"], 3),
        "b0_ms": num(b0["ms_per_ticket"], 2),
        "b1_macro_f1": num(b1["macro_f1"], 3),
        "b1_ms": num(b1["ms_per_ticket"], 3),
        "coverage_auto": pct(bt["coverage_auto"]),
        "precision_auto": pct(bt["precision_auto"]),
        "human_share": pct(bt["human_share"]),
        "conformal_coverage": pct(bt["conformal_coverage"]),
        "recall_at_5": pct(m["retrieval"]["recall"]["recall@5"]),
        "chance_at_5": pct(m["retrieval"]["chance"]["recall@5"]),
        "recall_at_1": pct(m["retrieval"]["recall"]["recall@1"]),
        "d1_human_share": pct(m["cross"]["human_share_d1"]),
        "d1_auto_share": pct(m["cross"]["auto_share_d1"]),
        "roi_net_hours_base": num(base["net_hours_month"]),
        "roi_net_brl_year_base": num(base["net_brl_year"]),
        "roi_net_hours_low": num(m["roi"]["baixa"]["net_hours_month"]),
        "roi_net_hours_high": num(m["roi"]["alta"]["net_hours_month"]),
    }
    h = m.get("hosted")
    if h:
        b2, so, ls = h["b2_test"], h["second_opinion"], h["llm_sample"]
        out |= {
            "b2_macro_f1": num(b2["macro_f1"], 3),
            "b2_accuracy": num(b2["accuracy"], 3),
            "b2_fallback": num(b2["fallback_used"]),
            "b2_unanswered": num(b2["unparsed"]),
            "so_val_precision": pct(so["val"]["precision"] or 0.0),
            "so_test_precision": pct(so["test"]["precision"] or 0.0),
            "so_test_extra": pct(so["test"]["extra_coverage"]),
            "llm_n": num(ls["n"]),
            "llm_macro_f1": num(ls["llm"]["macro_f1"], 3),
            "llm_b0_macro_f1": num(ls["b0"]["macro_f1"], 3),
            "llm_b2_macro_f1": num(ls["b2"]["macro_f1"], 3),
            "llm_ms": num(ls["llm"]["median_client_ms"]),
            "pii_n": num(h["privacy"]["n"]),
            "pii_name_recall": pct(h["privacy"]["name_recall"]),
            "pii_email_recall": pct(h["privacy"]["email_recall"]),
            "draft_n": num(h["drafts"]["n"]),
            "draft_leaks": num(h["drafts"]["pii_leaks"]),
            "draft_guard_pass": pct(h["drafts"]["guardrail_pass_rate"]),
            "draft_ms": num(h["drafts"]["median_client_ms"]),
        }
    return out
