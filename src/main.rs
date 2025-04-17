//! src/main.rs

use zero2prod::configuration::get_configuration;
use zero2prod::telemetry::{get_subscriber, init_subscriber};
use zero2prod::startup::Application;

#[tokio::main]
async fn main() -> Result<(), std::io::Error> {
    let subscriber = get_subscriber("info".into(), std::io::stdout);
    init_subscriber(subscriber);

    let configuration = get_configuration()
        .expect("Failed to read configuration");
    let application = Application::build(configuration.clone())
        .await?;
    application.run_until_stopped().await?;
    Ok(())
}
