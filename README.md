# Zero2Prod

A production-ready newsletter service built with Rust, featuring subscription management, health monitoring, and PostgreSQL integration.

**Version:** 0.8.0

## Features

- **RESTful API** - Health check and subscription endpoints
- **PostgreSQL Integration** - Type-safe database queries with sqlx
- **Structured Logging** - JSON-formatted tracing with Bunyan
- **Configuration Management** - YAML-based settings with environment overrides
- **Email Confirmation** - Two-step subscription process with email verification
- **Token Management** - Secure subscription token generation and validation
- **Containerized** - Docker/Podman support with multi-stage builds
- **Database Migrations** - Automated schema management

## Quick Start

### Prerequisites
- Rust 1.92+ 
- PostgreSQL 15+
- Podman|Docker

### Database Setup
```bash
./scripts/init_db.sh
```

### Run Locally
```bash
cargo run
```

### Run Tests
```bash
cargo test
```

### Build Container
```bash
podman build -t zero2prod:latest .
podman run --rm -p 8000:8000 zero2prod:latest
```

## API Endpoints

| Method | Path                     | Description                                                   |
|--------|--------------------------|---------------------------------------------------------------|
| GET    | `/health_check`          | Health monitoring endpoint                                    |
| POST   | `/subscriptions`         | Newsletter subscription (form data: name, email)              |
| GET    | `/subscriptions/confirm` | Email confirmation endpoint (query param: subscription_token) |

## Project Structure

```text
zero2prod/
├── src/
│   ├── main.rs              # Application entry point
│   ├── lib.rs               # Library exports
│   ├── configuration.rs     # Settings & database config
│   ├── startup.rs           # HTTP server setup
│   ├── telemetry.rs         # Logging configuration
│   ├── email_client.rs      # Email service integration
│   ├── domain/              # Domain models and validation
│   │   ├── mod.rs
│   │   ├── new_subscriber.rs
│   │   ├── subscriber_email.rs
│   │   └── subscriber_name.rs
│   └── routes/
│       ├── mod.rs
│       ├── health_check.rs  # Health endpoint
│       ├── subscriptions.rs # Subscription endpoint
│       └── subscriptions_confirm.rs # Email confirmation
├── tests/
│   └── api/                 # Integration tests
│       ├── main.rs
│       ├── helpers.rs
│       ├── health_check.rs
│       ├── subscriptions.rs
│       └── subscriptions_confirm.rs
├── migrations/              # Database schema
├── scripts/
│   ├── init_db.sh          # Database initialization
│   └── release-and-build.sh # Release automation
├── configuration/           # YAML config files
└── Dockerfile              # Container definition
```

## Architecture

### Module Dependencies
```text
main -> telemetry -> configuration -> startup -> routes
  |
PgPool (database)
  |
EmailClient
  |
HttpServer (actix-web) -> health_check + subscriptions + subscriptions_confirm
```

### Request Flow
1. **main** → Load configuration → Initialize telemetry → Connect to database
2. **startup** → Create HTTP server → Register routes
3. **routes** → Handle requests → Database operations → Response

## Key Technologies

- **Web Framework**: actix-web 4.x
- **Database**: PostgreSQL with sqlx (compile-time verified queries)
- **Async Runtime**: tokio
- **Logging**: tracing + tracing-bunyan-formatter
- **Configuration**: config crate with YAML
- **Security**: secrecy for sensitive data

## Development

### Release Process
```bash
./scripts/release-and-build.sh
```
This script:
1. Bumps version with cargo-release
2. Builds debug binary
3. Creates container image with version tag
4. Tags as `latest`

### Configuration
Edit `configuration.yaml` for database and application settings.

### Environment Variables
- `APP_ENVIRONMENT` - Set to `production` or `development`
- `DATABASE_URL` - PostgreSQL connection string (optional)

## Testing

Integration tests use isolated PostgreSQL databases with unique names per test run.

```bash
cargo test
cargo nextest run  # Parallel test execution
```

---
*Last updated: 2025-12-27*
