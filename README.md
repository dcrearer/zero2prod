# Zero2Prod Application

## Metrics Implementation

This application includes a metrics system built with Prometheus. The metrics are exposed at the `/metrics` endpoint and can be scraped by Prometheus or other monitoring systems.

### Available Metrics

- `http_requests_total`: Counter that tracks the total number of HTTP requests
- `http_request_duration_seconds`: Histogram that measures HTTP request duration in seconds

### How Metrics are Implemented

1. **Metrics Module**: The `src/metrics.rs` file defines the core metrics structure and functionality.

2. **Middleware**: The `src/middleware.rs` file contains a middleware that automatically:
   - Increments the request counter for each request
   - Measures and records the duration of each request

3. **Metrics Endpoint**: The `/metrics` endpoint exposes all metrics in Prometheus format.

### Using with Prometheus

To scrape these metrics with Prometheus, add the following to your `prometheus.yml` configuration:

```yaml
scrape_configs:
  - job_name: 'zero2prod'
    scrape_interval: 5s
    static_configs:
      - targets: ['localhost:8000']
```

Replace `localhost:8000` with the actual host and port where your application is running.

### Adding Custom Metrics

To add more metrics to the application:

1. Add new metric fields to the `Metrics` struct in `src/metrics.rs`
2. Initialize and register them in the `new()` method
3. Use them in your application code where appropriate

Example of adding a new counter:

```rust
// In src/metrics.rs
pub struct Metrics {
    pub http_requests_total: IntCounter,
    pub http_request_duration: Histogram,
    pub my_custom_counter: IntCounter,  // New metric
    registry: Registry,
}

impl Metrics {
    pub fn new() -> Self {
        // ... existing code ...
        
        // Create new counter
        let my_custom_counter = IntCounter::new(
            "my_custom_counter", 
            "Description of my custom counter"
        ).unwrap();
        
        // Register it
        registry.register(Box::new(my_custom_counter.clone())).unwrap();
        
        Self {
            http_requests_total,
            http_request_duration,
            my_custom_counter,  // Include in struct
            registry,
        }
    }
}
```

Then use it in your code:

```rust
// In a request handler
my_custom_counter.inc();
```
