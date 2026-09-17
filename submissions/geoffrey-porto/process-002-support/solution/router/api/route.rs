//! Função da Vercel: `POST /api/route` e `GET /api/route/health`.
//!
//! Mesmos handlers do roteador local (`app_at`); o modelo gzip vai embutido no
//! binário para a função não depender de arquivos no bundle.

use std::sync::Arc;

use support_router::app_at;
use support_router::model::RouterModel;
use tower::ServiceBuilder;
use vercel_runtime::Error;
use vercel_runtime::axum::VercelLayer;

static MODEL_GZ: &[u8] = include_bytes!("../dist/router_model.json.gz");

#[tokio::main]
async fn main() -> Result<(), Error> {
    let model = Arc::new(RouterModel::from_gz_bytes(MODEL_GZ)?);
    let router = app_at(model, "/api/route", "/api/route/health");
    let service = ServiceBuilder::new()
        .layer(VercelLayer::new())
        .service(router);
    vercel_runtime::run(service).await
}
