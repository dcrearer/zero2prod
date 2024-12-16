use std::net::TcpListener;
use zero2prod::run;
#[tokio::main]
async fn main() -> Result<(), std::io::Error> {
    let listener = TcpListener::bind("0.0.0.0:8000")
        .expect("Failed to bind random port");

    run(listener)?.await
}