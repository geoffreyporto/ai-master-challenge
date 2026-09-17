//! AC-044: os caminhos da Vercel servem o mesmo modelo embutido.

#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::io::BufRead;
use std::path::PathBuf;
use std::sync::Arc;

use axum::body::Body;
use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use serde_json::{Value, json};
use support_router::app_at;
use support_router::model::RouterModel;
use tower::ServiceExt;

static MODEL_GZ: &[u8] = include_bytes!("../dist/router_model.json.gz");

async fn call(app: axum::Router, req: Request<Body>) -> (StatusCode, Value) {
    let resp = app.oneshot(req).await.unwrap();
    let status = resp.status();
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    (
        status,
        serde_json::from_slice(&bytes).unwrap_or(Value::Null),
    )
}

#[tokio::test]
async fn vercel_paths_decide_like_the_golden() {
    let model = Arc::new(RouterModel::from_gz_bytes(MODEL_GZ).expect("modelo embutido"));
    let app = app_at(model, "/api/route", "/api/route/health");
    let (status, body) = call(
        app.clone(),
        Request::get("/api/route/health")
            .body(Body::empty())
            .unwrap(),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");

    let golden = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../outputs/golden/holdout.jsonl");
    let file = std::fs::File::open(golden).expect("golden");
    let mut n = 0;
    for line in std::io::BufReader::new(file).lines().take(300) {
        let g: Value = serde_json::from_str(&line.unwrap()).unwrap();
        let req = Request::post("/api/route")
            .header("content-type", "application/json")
            .body(Body::from(json!({"text": g["text"]}).to_string()))
            .unwrap();
        let (status, out) = call(app.clone(), req).await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(out["topic"], g["topic"]);
        assert_eq!(out["action"], g["action"]);
        n += 1;
    }
    assert_eq!(n, 300);
    println!("vercel: {n} tickets iguais ao golden");
}
