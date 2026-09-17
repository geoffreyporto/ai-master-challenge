//! Saída do modelo consumida pela política (módulo próprio evita ciclo model ↔ policy).

/// Pontuação de um texto: probabilidade por fila e fração de n-gramas conhecidos.
#[derive(Debug, Clone)]
pub struct Scores {
    pub proba: Vec<f64>,
    pub known_share: f64,
}
