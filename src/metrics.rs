use prometheus::{IntCounter, Histogram, Registry, Encoder, TextEncoder};
use prometheus::histogram_opts;

pub struct Metrics {
    pub http_requests_total: IntCounter,
    pub http_request_duration: Histogram,
    registry: Registry,
}

impl Metrics {
    pub fn new() -> Self {
        // Create a registry
        let registry = Registry::new();
        
        // Create counter metric
        let http_requests_total = IntCounter::new(
            "http_requests_total", 
            "Total number of HTTP requests"
        ).unwrap();
        
        // Create histogram metric
        let http_request_duration = Histogram::with_opts(
            histogram_opts!(
                "http_request_duration_seconds",
                "HTTP request duration in seconds"
            )
        ).unwrap();
        
        // Register metrics
        registry.register(Box::new(http_requests_total.clone())).unwrap();
        registry.register(Box::new(http_request_duration.clone())).unwrap();

        Self {
            http_requests_total,
            http_request_duration,
            registry,
        }
    }

    pub fn render(&self) -> String {
        let mut buffer = Vec::new();
        let encoder = TextEncoder::new();
        let metric_families = self.registry.gather();
        encoder.encode(&metric_families, &mut buffer).unwrap();
        String::from_utf8(buffer).unwrap()
    }
}