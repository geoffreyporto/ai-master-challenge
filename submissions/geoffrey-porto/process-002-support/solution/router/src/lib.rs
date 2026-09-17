//! Roteador HTTP de tickets: `POST /route` e `GET /health`.

pub mod model;
pub mod policy;
pub mod scores;

use std::sync::Arc;

use axum::extract::rejection::JsonRejection;
use axum::extract::{DefaultBodyLimit, State};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use serde::{Deserialize, Serialize};
use serde_json::json;

use crate::model::RouterModel;
use crate::policy::{Decision, decide};

pub const MAX_TEXT_CHARS: usize = 20_000;
const MAX_BODY_BYTES: usize = 128 * 1024;

#[derive(Debug, Deserialize)]
pub struct RouteRequest {
    pub text: String,
    #[serde(default)]
    pub priority: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct RouteResponse {
    #[serde(flatten)]
    pub decision: Decision,
    pub model: &'static str,
}

#[derive(Debug, thiserror::Error)]
pub enum ApiError {
    #[error("o texto do ticket está vazio")]
    EmptyText,
    #[error("o texto tem {0} caracteres; o limite é {MAX_TEXT_CHARS}")]
    TooLong(usize),
    #[error("corpo inválido: {0}")]
    BadBody(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let status = match self {
            Self::EmptyText | Self::BadBody(_) => StatusCode::UNPROCESSABLE_ENTITY,
            Self::TooLong(_) => StatusCode::PAYLOAD_TOO_LARGE,
        };
        (status, Json(json!({ "error": self.to_string() }))).into_response()
    }
}

pub fn app(model: Arc<RouterModel>) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/route", post(route))
        .layer(DefaultBodyLimit::max(MAX_BODY_BYTES))
        .with_state(model)
}

async fn health(State(model): State<Arc<RouterModel>>) -> Json<serde_json::Value> {
    Json(json!({
        "status": "ok",
        "classes": model.classes.len(),
        "terms": model.n_terms(),
    }))
}

async fn route(
    State(model): State<Arc<RouterModel>>,
    body: Result<Json<RouteRequest>, JsonRejection>,
) -> Result<Json<RouteResponse>, ApiError> {
    let Json(req) = body.map_err(|e| ApiError::BadBody(e.body_text()))?;
    let chars = req.text.chars().count();
    if chars > MAX_TEXT_CHARS {
        return Err(ApiError::TooLong(chars));
    }
    if req.text.trim().is_empty() {
        return Err(ApiError::EmptyText);
    }
    let scores = model.score(&req.text);
    let decision = decide(&model.policy, &scores, req.priority.as_deref());
    Ok(Json(RouteResponse {
        decision,
        model: "tfidf-lr-v1",
    }))
}
