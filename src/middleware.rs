use actix_web::{
    dev::{forward_ready, Service, ServiceRequest, ServiceResponse, Transform},
    Error, web,
};
use futures::future::{ready, Ready};
use futures::Future;
use std::pin::Pin;
use std::time::Instant;
use crate::metrics::Metrics;

pub struct MetricsMiddleware {
    metrics: web::Data<Metrics>,
}

impl MetricsMiddleware {
    pub fn new(metrics: web::Data<Metrics>) -> Self {
        Self { metrics }
    }
}

impl<S, B> Transform<S, ServiceRequest> for MetricsMiddleware
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error>,
    S::Future: 'static,
    B: 'static,
{
    type Response = ServiceResponse<B>;
    type Error = Error;
    type Transform = MetricsMiddlewareService<S>;
    type InitError = ();
    type Future = Ready<Result<Self::Transform, Self::InitError>>;

    fn new_transform(&self, service: S) -> Self::Future {
        ready(Ok(MetricsMiddlewareService {
            service,
            metrics: self.metrics.clone(),
        }))
    }
}

pub struct MetricsMiddlewareService<S> {
    service: S,
    metrics: web::Data<Metrics>,
}

impl<S, B> Service<ServiceRequest> for MetricsMiddlewareService<S>
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error>,
    S::Future: 'static,
    B: 'static,
{
    type Response = ServiceResponse<B>;
    type Error = Error;
    type Future = Pin<Box<dyn Future<Output = Result<Self::Response, Self::Error>>>>;

    forward_ready!(service);

    fn call(&self, req: ServiceRequest) -> Self::Future {
        // Increment request counter
        self.metrics.http_requests_total.inc();
        
        let start = Instant::now();
        let fut = self.service.call(req);
        let metrics = self.metrics.clone();

        Box::pin(async move {
            let res = fut.await?;
            let duration = start.elapsed().as_secs_f64();
            
            // Record request duration
            metrics.http_request_duration.observe(duration);
            
            Ok(res)
        })
    }
}
