//! AC-028 / P-005: o roteador decide igual ao Python em todo o hold-out.

#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::io::BufRead;
use std::path::PathBuf;

use serde::Deserialize;
use support_router::model::RouterModel;
use support_router::policy::{Action, decide};

#[derive(Deserialize)]
struct Golden {
    text: String,
    proba: Vec<f64>,
    topic: String,
    action: String,
}

fn outputs() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../outputs")
}

fn action_name(a: Action) -> &'static str {
    match a {
        Action::Auto => "auto",
        Action::Confirmar => "confirmar",
        Action::Humano => "humano",
    }
}

#[test]
fn rust_matches_python_on_full_holdout() {
    let model = RouterModel::load(&outputs().join("models/router_model.json"))
        .expect("rode `uv run python -m support_redesign` antes");
    let file = std::fs::File::open(outputs().join("golden/holdout.jsonl")).expect("golden ausente");
    let mut n = 0usize;
    let mut max_diff = 0.0f64;
    for line in std::io::BufReader::new(file).lines() {
        let g: Golden = serde_json::from_str(&line.expect("linha")).expect("json");
        let scores = model.score(&g.text);
        let d = decide(&model.policy, &scores, None);
        assert_eq!(d.topic, g.topic, "fila diverge em: {}", g.text);
        assert_eq!(
            action_name(d.action),
            g.action,
            "ação diverge em: {}",
            g.text
        );
        for (a, b) in scores.proba.iter().zip(&g.proba) {
            max_diff = max_diff.max((a - b).abs());
        }
        n += 1;
    }
    assert!(n > 9_000, "hold-out incompleto: {n}");
    assert!(
        max_diff < 1e-9,
        "diferença máxima de probabilidade {max_diff}"
    );
    println!("paridade: {n} tickets, max |Δp| = {max_diff:e}");
}

#[test]
fn shipped_gzip_model_scores_like_the_pipeline_model() {
    let json = RouterModel::load(&outputs().join("models/router_model.json")).expect("json");
    let gz_path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("dist/router_model.json.gz");
    let gz = RouterModel::load(&gz_path).expect("rode o pipeline para gerar dist/");
    let file = std::fs::File::open(outputs().join("golden/holdout.jsonl")).expect("golden");
    for line in std::io::BufReader::new(file).lines().take(500) {
        let g: Golden = serde_json::from_str(&line.expect("linha")).expect("json");
        assert_eq!(json.score(&g.text).proba, gz.score(&g.text).proba);
    }
    println!("modelo dist confere com o pipeline");
}
