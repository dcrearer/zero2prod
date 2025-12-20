# Zero2Prod

A production-ready newsletter service built with Rust, featuring subscription management, health monitoring, and PostgreSQL integration.

**Version:** 0.4.0

## Features

- **RESTful API** - Health check and subscription endpoints
- **PostgreSQL Integration** - Type-safe database queries with sqlx
- **Structured Logging** - JSON-formatted tracing with Bunyan
- **Configuration Management** - YAML-based settings with environment overrides
- **Security** - Secret handling with secrecy crate
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
podman build -t zero2prod:0.4.0 .
podman run --rm -p 8000:8000 zero2prod:0.4.0
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health_check` | Health monitoring endpoint |
| POST | `/subscriptions` | Newsletter subscription (form data: name, email) |

## Project Structure

```
zero2prod/
├── src/
│   ├── main.rs              # Application entry point
│   ├── lib.rs               # Library exports
│   ├── configuration.rs     # Settings & database config
│   ├── startup.rs           # HTTP server setup
│   ├── telemetry.rs         # Logging configuration
│   └── routes/
│       ├── mod.rs
│       ├── health_check.rs  # Health endpoint
│       └── subscriptions.rs # Subscription endpoint
├── tests/
│   └── health_check.rs      # Integration tests
├── migrations/              # Database schema
├── scripts/
│   ├── init_db.sh          # Database initialization
│   └── release-and-build.sh # Release automation
├── configuration/           # YAML config files
└── Dockerfile              # Container definition
```

## Architecture

### Module Dependencies
```
main → configuration → startup → routes
  ↓
telemetry (logging)
  ↓
PgPool (database)
  ↓
HttpServer (actix-web) → health_check + subscriptions
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
*Last updated: 2025-12-19*
