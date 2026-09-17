//! TF-IDF + regressão logística exportados pelo Python (`support_redesign.export`).
//!
//! Normalização e n-gramas replicam `support_redesign/text.py` regra por regra;
//! a paridade é testada no hold-out inteiro (`tests/parity.rs`).

use std::collections::HashMap;
use std::io::Read;
use std::path::Path;

use serde::Deserialize;

use crate::policy::PolicyConfig;
pub use crate::scores::Scores;

#[derive(Debug, thiserror::Error)]
pub enum ModelError {
    #[error("não foi possível ler o modelo em {path}: {source}")]
    Read {
        path: String,
        source: std::io::Error,
    },
    #[error("modelo inválido: {0}")]
    Parse(#[from] serde_json::Error),
    #[error("modelo inconsistente: {0}")]
    Shape(String),
}

#[derive(Deserialize)]
struct RawModel {
    format: String,
    classes: Vec<String>,
    terms: Vec<String>,
    idf: Vec<f64>,
    coef: Vec<Vec<f64>>,
    intercept: Vec<f64>,
    policy: PolicyConfig,
}

pub struct RouterModel {
    pub classes: Vec<String>,
    pub policy: PolicyConfig,
    term_index: HashMap<String, usize>,
    idf: Vec<f64>,
    coef: Vec<Vec<f64>>,
    intercept: Vec<f64>,
}

impl RouterModel {
    pub fn load(path: &Path) -> Result<Self, ModelError> {
        let read_err = |source| ModelError::Read {
            path: path.display().to_string(),
            source,
        };
        let file = std::fs::File::open(path).map_err(read_err)?;
        let mut raw = String::new();
        if path.extension().is_some_and(|e| e == "gz") {
            flate2::read::GzDecoder::new(file)
                .read_to_string(&mut raw)
                .map_err(read_err)?;
        } else {
            std::io::BufReader::new(file)
                .read_to_string(&mut raw)
                .map_err(read_err)?;
        }
        Self::from_json(&raw)
    }

    /// Modelo gzip já em memória (ex.: embutido no binário com `include_bytes!`).
    pub fn from_gz_bytes(bytes: &[u8]) -> Result<Self, ModelError> {
        let mut raw = String::new();
        flate2::read::GzDecoder::new(bytes)
            .read_to_string(&mut raw)
            .map_err(|source| ModelError::Read {
                path: "<embutido>".into(),
                source,
            })?;
        Self::from_json(&raw)
    }

    pub fn from_json(raw: &str) -> Result<Self, ModelError> {
        let m: RawModel = serde_json::from_str(raw)?;
        if m.format != "tfidf-lr-v1" {
            return Err(ModelError::Shape(format!(
                "formato {} desconhecido",
                m.format
            )));
        }
        let n_terms = m.terms.len();
        let n_classes = m.classes.len();
        if m.idf.len() != n_terms
            || m.coef.len() != n_classes
            || m.intercept.len() != n_classes
            || m.coef.iter().any(|row| row.len() != n_terms)
            || m.policy.classes != m.classes
        {
            return Err(ModelError::Shape(
                "dimensões de idf/coef/intercept/classes não batem".into(),
            ));
        }
        let term_index = m
            .terms
            .into_iter()
            .enumerate()
            .map(|(i, t)| (t, i))
            .collect();
        Ok(Self {
            classes: m.classes,
            policy: m.policy,
            term_index,
            idf: m.idf,
            coef: m.coef,
            intercept: m.intercept,
        })
    }

    pub fn n_terms(&self) -> usize {
        self.idf.len()
    }

    pub fn score(&self, text: &str) -> Scores {
        let grams = analyzer(text);
        let mut counts: HashMap<usize, f64> = HashMap::new();
        let mut known = 0usize;
        for g in &grams {
            if let Some(&i) = self.term_index.get(g) {
                known += 1;
                *counts.entry(i).or_insert(0.0) += 1.0;
            }
        }
        let mut weights: Vec<(usize, f64)> = counts
            .into_iter()
            .map(|(i, c)| (i, (1.0 + c.ln()) * self.idf[i]))
            .collect();
        weights.sort_unstable_by_key(|(i, _)| *i);
        let norm = weights.iter().map(|(_, w)| w * w).sum::<f64>().sqrt();
        if norm > 0.0 {
            for (_, w) in &mut weights {
                *w /= norm;
            }
        }
        let logits: Vec<f64> = self
            .coef
            .iter()
            .zip(&self.intercept)
            .map(|(row, b)| weights.iter().map(|(i, w)| row[*i] * w).sum::<f64>() + b)
            .collect();
        let known_share = if grams.is_empty() {
            0.0
        } else {
            known as f64 / grams.len() as f64
        };
        Scores {
            proba: softmax(&logits),
            known_share,
        }
    }
}

fn softmax(logits: &[f64]) -> Vec<f64> {
    let max = logits.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let exps: Vec<f64> = logits.iter().map(|z| (z - max).exp()).collect();
    let total: f64 = exps.iter().sum();
    exps.iter().map(|e| e / total).collect()
}

/// Remove `{...}` sem chaves internas, como o regex `\{[^{}]*\}` do Python.
fn strip_placeholders(text: &str) -> String {
    let chars: Vec<char> = text.chars().collect();
    let mut out = String::with_capacity(text.len());
    let mut i = 0;
    while i < chars.len() {
        if chars[i] == '{' {
            let close = chars[i + 1..]
                .iter()
                .position(|&c| c == '{' || c == '}')
                .filter(|&off| chars[i + 1 + off] == '}');
            if let Some(off) = close {
                out.push(' ');
                i += off + 2;
                continue;
            }
        }
        out.push(chars[i]);
        i += 1;
    }
    out
}

pub fn normalize(text: &str) -> String {
    let stripped = strip_placeholders(&text.to_lowercase());
    let letters: String = stripped
        .chars()
        .map(|c| if c.is_ascii_lowercase() { c } else { ' ' })
        .collect();
    letters.split_whitespace().collect::<Vec<_>>().join(" ")
}

pub fn analyzer(text: &str) -> Vec<String> {
    let norm = normalize(text);
    let toks: Vec<&str> = norm.split(' ').filter(|t| t.len() >= 2).collect();
    let mut grams: Vec<String> = toks.iter().map(|t| (*t).to_string()).collect();
    grams.extend(toks.windows(2).map(|w| format!("{} {}", w[0], w[1])));
    grams
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalize_matches_python_rules() {
        assert_eq!(
            normalize("I'm having an issue with the {product_purchased}. Error 404!"),
            "i m having an issue with the error"
        );
        assert_eq!(normalize("{a{b}c}"), "a c");
        assert_eq!(normalize("   "), "");
    }

    #[test]
    fn analyzer_builds_unigrams_then_bigrams() {
        assert_eq!(
            analyzer("VPN a down now"),
            vec!["vpn", "down", "now", "vpn down", "down now"]
        );
    }
}
