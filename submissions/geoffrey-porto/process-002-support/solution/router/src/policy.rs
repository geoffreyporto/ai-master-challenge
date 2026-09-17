//! Política IA × humano — mesma ordem de regras de `support_redesign/boundary.py`.

use std::collections::HashMap;

use serde::{Deserialize, Serialize};

use crate::scores::Scores;

#[derive(Debug, Clone, Deserialize)]
pub struct PolicyConfig {
    pub classes: Vec<String>,
    pub thresholds: HashMap<String, Option<f64>>,
    pub qhat: f64,
    pub min_known_share: f64,
    pub target_precision: f64,
    pub alpha: f64,
    pub human_only: Vec<String>,
    pub confirm_priorities: Vec<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Action {
    Auto,
    Confirmar,
    Humano,
}

#[derive(Debug, Clone, Serialize)]
pub struct Decision {
    pub topic: String,
    pub confidence: f64,
    pub margin: f64,
    pub prediction_set: Vec<String>,
    pub known_share: f64,
    pub action: Action,
    pub reason: String,
}

pub fn decide(policy: &PolicyConfig, scores: &Scores, priority: Option<&str>) -> Decision {
    let proba = &scores.proba;
    let (top_idx, conf) =
        proba
            .iter()
            .copied()
            .enumerate()
            .fold((0, f64::NEG_INFINITY), |best, (i, p)| {
                if p > best.1 { (i, p) } else { best }
            });
    let second = proba
        .iter()
        .enumerate()
        .filter(|(i, _)| *i != top_idx)
        .map(|(_, p)| *p)
        .fold(f64::NEG_INFINITY, f64::max);
    let topic = policy.classes[top_idx].clone();
    let floor = 1.0 - policy.qhat;
    let prediction_set: Vec<String> = proba
        .iter()
        .zip(&policy.classes)
        .filter(|(p, _)| **p >= floor)
        .map(|(_, c)| c.clone())
        .collect();
    let threshold = policy.thresholds.get(&topic).copied().flatten();

    let (action, reason) = if scores.known_share < policy.min_known_share {
        (
            Action::Humano,
            format!(
                "fora do domínio: {:.0}% dos termos conhecidos",
                scores.known_share * 100.0
            ),
        )
    } else if prediction_set.len() != 1 {
        (
            Action::Humano,
            format!("conjunto conformal com {} filas", prediction_set.len()),
        )
    } else if policy.human_only.contains(&topic) {
        (Action::Humano, format!("fila {topic} é só-humano"))
    } else if let Some(thr) = threshold {
        if conf < thr {
            (
                Action::Humano,
                format!("confiança {conf:.3} abaixo do limiar {thr:.3}"),
            )
        } else if priority.is_some_and(|p| policy.confirm_priorities.iter().any(|c| c == p)) {
            (
                Action::Confirmar,
                format!(
                    "prioridade {} exige confirmação humana",
                    priority.unwrap_or_default()
                ),
            )
        } else {
            (
                Action::Auto,
                format!("confiança {conf:.3} ≥ limiar {thr:.3}"),
            )
        }
    } else {
        (
            Action::Humano,
            format!("fila {topic} não atinge a precisão-alvo na validação"),
        )
    };

    Decision {
        topic,
        confidence: conf,
        margin: conf - second,
        prediction_set,
        known_share: scores.known_share,
        action,
        reason,
    }
}
