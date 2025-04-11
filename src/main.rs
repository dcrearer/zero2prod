//! src/main.rs
use zero2prod::startup::run;
use zero2prod::configuration::get_configuration;
use zero2prod::telemetry::{get_subscriber, init_subscriber};
use std::net::TcpListener;
use sqlx::postgres::{PgPoolOptions};

#[tokio::main]
async fn main() -> Result<(), std::io::Error> {
    let subscriber = get_subscriber("info".into(), std::io::stdout);

    init_subscriber(subscriber);

    let configuration = get_configuration()
        .expect("Failed to read configuration");
    let connection_pool = PgPoolOptions::new()
        .connect_lazy_with(configuration.database.connection_options());
    let address = format!("{}:{}",configuration.application.host, configuration.application.port);
    let listener = TcpListener::bind(address)?;
    run(listener, connection_pool)?.await
}
