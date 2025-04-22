//! src/telemetry.rs
use tracing::{Subscriber, subscriber::set_global_default};
use tracing_bunyan_formatter::{BunyanFormattingLayer, JsonStorageLayer};
use tracing_log::LogTracer;
use tracing_subscriber::fmt::MakeWriter;
use tracing_subscriber::{EnvFilter, Registry, layer::SubscriberExt};

use opentelemetry::trace::TracerProvider;
use opentelemetry::{KeyValue, global};
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::{Resource, propagation::TraceContextPropagator};
use opentelemetry_semantic_conventions::resource;
use std::sync::LazyLock;

const APP_NAME: &str = "zero2prod";

static RESOURCE: LazyLock<Resource> = LazyLock::new(|| {
    Resource::builder()
        .with_attribute(KeyValue::new(resource::SERVICE_NAME, APP_NAME))
        .build()
});
pub fn get_subscriber<Sink>(env_filter: String, sink: Sink) -> impl Subscriber + Send + Sync
where
    Sink: for<'a> MakeWriter<'a> + Send + Sync + 'static,
{
    // Start a new otlp trace pipeline.
    // Spans are exported in batch - recommended setup for a production application.
    global::set_text_map_propagator(TraceContextPropagator::new());
    let otlp_exporter = opentelemetry_otlp::SpanExporter::builder()
        .with_tonic()
        .with_endpoint("http://127.0.0.1:4317")
        .build()
        .expect("Failed to build the span exporter");
    let provider = opentelemetry_sdk::trace::SdkTracerProvider::builder()
        .with_batch_exporter(otlp_exporter)
        .with_resource(RESOURCE.clone())
        .build();
    let tracer = provider.tracer(APP_NAME);

    // Filter based on level - trace, debug, info, warn, error
    // Tunable via `RUST_LOG` env variable
    let env_filter =
        EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new(env_filter));
    let telemetry = tracing_opentelemetry::layer().with_tracer(tracer);
    let formatting_layer = BunyanFormattingLayer::new(APP_NAME.into(), sink);
    Registry::default()
        .with(env_filter)
        .with(telemetry)
        .with(JsonStorageLayer)
        .with(formatting_layer)
}

pub fn init_subscriber(subscriber: impl Subscriber + Send + Sync) {
    LogTracer::init().expect("Failed to set logger");
    set_global_default(subscriber).expect("Failed to set subscriber");
}
