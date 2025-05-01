//! src/routes/metrics.rs
use actix_web::{HttpResponse, web};
use crate::metrics::Metrics;

pub async fn get_metrics(metrics: web::Data<Metrics>) -> HttpResponse {
    let metrics_output = metrics.render();
    HttpResponse::Ok()
        .content_type("text/plain")
        .body(metrics_output)
}