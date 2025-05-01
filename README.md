# Zero2Prod

A production-ready web application built with Rust, following the principles outlined in the "Zero To Production In Rust" approach. This project implements a newsletter delivery service with user subscription management.

## Features

- User subscription system with email confirmation
- Newsletter creation and delivery
- Health check endpoint
- Telemetry and logging with OpenTelemetry
- Database migrations with SQLx
- Comprehensive test suite

## Tech Stack

- **Backend Framework**: Actix-Web
- **Database**: PostgreSQL with SQLx
- **Async Runtime**: Tokio
- **Configuration**: config-rs
- **Logging/Tracing**: tracing, tracing-subscriber, OpenTelemetry
- **Email**: Custom email client
- **Testing**: Tokio test, wiremock, quickcheck
- **Error Handling**: thiserror, anyhow
- **Security**: secrecy for sensitive data

## Getting Started

### Prerequisites

- Rust (latest stable version)
- PostgreSQL
- Docker (optional, for containerized deployment)

### Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd zero2prod
   ```

2. Set up the database:
   ```
   # Create a PostgreSQL database for the application
   # Update configuration in configuration files
   ```

3. Run the application:
   ```
   cargo run
   ```

4. Run tests:
   ```
   cargo test
   ```

### Configuration

The application uses a layered configuration system:
- Base configuration in `configuration/base.yaml`
- Environment-specific overrides in `configuration/{environment}.yaml`
- Environment variables for sensitive information

## Project Structure

- `src/`: Application source code
  - `configuration/`: Configuration management
  - `domain/`: Domain models and business logic
  - `email_client/`: Email delivery functionality
  - `routes/`: API endpoints
  - `startup/`: Application initialization
  - `telemetry/`: Logging and monitoring

- `tests/`: Integration tests
  - `api/`: API tests for each endpoint

## Scripts

The `scripts/` directory contains utility scripts for development, deployment, and maintenance tasks.

## Development

### Running in Development Mode

```
cargo run
```

### Running Tests

```
cargo test
```

## Deployment

The application can be deployed as a standalone binary or containerized with Docker.

## License

[License information]

## Acknowledgments

Based on the "Zero To Production In Rust" approach to building production-ready web services.
