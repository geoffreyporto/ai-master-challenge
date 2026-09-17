//! AC-027 / AC-029: contrato HTTP do roteador.

#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::path::PathBuf;
use std::sync::{Arc, OnceLock};

use axum::body::Body;
use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use support_router::model::RouterModel;
use support_router::{MAX_TEXT_CHARS, app};
use tower::ServiceExt;

fn model() -> Arc<RouterModel> {
    static MODEL: OnceLock<Arc<RouterModel>> = OnceLock::new();
    MODEL
        .get_or_init(|| {
            let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join("../outputs/models/router_model.json");
            Arc::new(RouterModel::load(&path).expect("rode o pipeline antes"))
        })
        .clone()
}

async fn call(req: Request<Body>) -> (StatusCode, Value) {
    let resp = app(model()).oneshot(req).await.unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

fn post(body: impl Into<Body>) -> Request<Body> {
    Request::post("/route")
        .header("content-type", "application/json")
        .body(body.into())
        .unwrap()
}

#[tokio::test]
async fn health_is_ok() {
    let (status, body) = call(Request::get("/health").body(Body::empty()).unwrap()).await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");
    assert_eq!(body["classes"], 8);
}

#[tokio::test]
async fn route_returns_topic_confidence_and_action() {
    let text = "laptop screen broken please replace monitor cable dock not working";
    let (status, body) = call(post(json!({"text": text}).to_string())).await;
    assert_eq!(status, StatusCode::OK);
    for key in [
        "topic",
        "confidence",
        "margin",
        "prediction_set",
        "action",
        "reason",
    ] {
        assert!(body.get(key).is_some(), "falta {key}: {body}");
    }
    assert!(["auto", "confirmar", "humano"].contains(&body["action"].as_str().unwrap()));
}

#[tokio::test]
async fn critical_priority_never_goes_straight_to_auto() {
    let text = "laptop screen broken please replace monitor cable dock not working";
    let (_, body) = call(post(
        json!({"text": text, "priority": "Critical"}).to_string(),
    ))
    .await;
    assert_ne!(body["action"], "auto");
}

#[tokio::test]
async fn rejects_invalid_input_and_keeps_serving() {
    let (s1, b1) = call(post(json!({"text": "   "}).to_string())).await;
    assert_eq!(s1, StatusCode::UNPROCESSABLE_ENTITY);
    assert!(b1["error"].is_string());

    let long = "a".repeat(MAX_TEXT_CHARS + 1);
    let (s2, _) = call(post(json!({"text": long}).to_string())).await;
    assert_eq!(s2, StatusCode::PAYLOAD_TOO_LARGE);

    let (s3, b3) = call(post("{not json")).await;
    assert!(s3.is_client_error());
    assert!(b3["error"].is_string());

    let (s4, _) = call(post(vec![b'x'; 300 * 1024])).await;
    assert!(s4.is_client_error());

    let (s5, _) = call(Request::get("/health").body(Body::empty()).unwrap()).await;
    assert_eq!(s5, StatusCode::OK);
}
