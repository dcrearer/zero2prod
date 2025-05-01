use actix_web::{HttpResponse, web};
use crate::metrics::Metrics;

pub async fn health_check(metrics: web::Data<Metrics>) -> HttpResponse {
    // Increment the request counter
    metrics.http_requests_total.inc();
    
    HttpResponse::Ok().finish()
}
