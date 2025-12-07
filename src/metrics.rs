use prometheus::{Encoder, IntCounter, IntCounterVec, Opts, Registry, TextEncoder};
use std::sync::OnceLock;

static REGISTRY: OnceLock<Registry> = OnceLock::new();

pub fn registry() -> &'static Registry {
    REGISTRY.get_or_init(|| {
        let r = Registry::new();
        r.register(Box::new(HTTP_REQUESTS.clone())).unwrap();
        r.register(Box::new(SUBSCRIPTION_REQUESTS.clone())).unwrap();
        r
    })
}

lazy_static::lazy_static! {
    pub static ref HTTP_REQUESTS: IntCounterVec = IntCounterVec::new(
        Opts::new("http_requests_total", "Total HTTP requests"),
        &["method", "path", "status"]
    ).unwrap();

    pub static ref SUBSCRIPTION_REQUESTS: IntCounter = IntCounter::new(
        "subscription_requests_total",
        "Total subscription requests"
    ).unwrap();
}

pub fn metrics_handler() -> String {
    let encoder = TextEncoder::new();
    let metric_families = registry().gather();
    let mut buffer = vec![];
    encoder.encode(&metric_families, &mut buffer).unwrap();
    String::from_utf8(buffer).unwrap()
}
