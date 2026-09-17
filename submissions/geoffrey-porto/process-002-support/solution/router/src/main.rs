//! `support-router [--model PATH] [--addr HOST:PORT]`
//!
//! Sem `--model`, procura nesta ordem: `ROUTER_MODEL`, `router_model.json.gz`
//! ao lado do executável ou uma pasta acima (layout de `dist/`), e o modelo
//! gerado pelo pipeline em `outputs/models/`.

use std::path::PathBuf;
use std::sync::Arc;

use support_router::app;
use support_router::model::RouterModel;

const DEFAULT_ADDR: &str = "127.0.0.1:8080";
const DIST_MODEL: &str = "router_model.json.gz";

fn arg_value(args: &[String], flag: &str) -> Option<String> {
    args.iter()
        .position(|a| a == flag)
        .and_then(|i| args.get(i + 1).cloned())
}

fn model_candidates(args: &[String]) -> Vec<PathBuf> {
    let mut out: Vec<PathBuf> = Vec::new();
    if let Some(p) = arg_value(args, "--model") {
        return vec![PathBuf::from(p)];
    }
    if let Ok(p) = std::env::var("ROUTER_MODEL") {
        out.push(PathBuf::from(p));
    }
    if let Some(dir) = std::env::current_exe()
        .ok()
        .and_then(|e| e.parent().map(PathBuf::from))
    {
        out.push(dir.join(DIST_MODEL));
        out.push(dir.join("..").join(DIST_MODEL));
    }
    out.push(
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("dist")
            .join(DIST_MODEL),
    );
    out.push(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../outputs/models/router_model.json"));
    out
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--help" || a == "-h") {
        println!("uso: support-router [--model CAMINHO] [--addr HOST:PORTA]");
        return Ok(());
    }
    let candidates = model_candidates(&args);
    let path = candidates
        .iter()
        .find(|p| p.is_file())
        .ok_or_else(|| format!("modelo não encontrado; procurei em {candidates:?}"))?;
    let addr = arg_value(&args, "--addr")
        .or_else(|| std::env::var("ROUTER_ADDR").ok())
        .unwrap_or_else(|| DEFAULT_ADDR.to_string());
    let model = Arc::new(RouterModel::load(path)?);
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    println!(
        "roteador em http://{addr} ({} termos, {} filas, modelo {})",
        model.n_terms(),
        model.classes.len(),
        path.display()
    );
    axum::serve(listener, app(model))
        .with_graceful_shutdown(async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;
    Ok(())
}
