# Technology Stack Documentation

## Overview

Zero2prod is built entirely in Rust using modern, production-grade libraries for web services, async programming, and database access.

## Programming Languages

| Language | Version/Edition | Usage | Percentage |
|----------|----------------|-------|------------|
| Rust | 2024 Edition | Application code, tests | 100% |
| SQL | PostgreSQL dialect | Database migrations, queries | Embedded |
| YAML | 1.2 | Configuration files | Config only |

---

## Core Runtime & Framework

### Async Runtime

| Component | Version | Purpose | Features Used |
|-----------|---------|---------|---------------|
| **Tokio** | 1.48.0 | Async runtime for all async operations | `macros`, `rt-multi-thread` |

**Key Features**:
- Multi-threaded work-stealing scheduler
- Async I/O primitives
- `tokio::spawn` for concurrent tasks
- `tokio::select!` for task monitoring

### Web Framework

| Component | Version | Purpose | Key Features |
|-----------|---------|---------|--------------|
| **Actix-web** | 4.12.1 | HTTP server and routing | Middleware, routing, extractors, error handling |
| **actix-session** | 0.11.0 | Session management | Redis backend, secure cookies |
| **actix-web-flash-messages** | 0.5.0 | Flash messages | Cookie storage, signed messages |
| **tracing-actix-web** | 0.7.20 | Request tracing | Distributed tracing for HTTP requests |

**Architecture**: Actor-based web framework with middleware pipeline

---

## Database & Persistence

### Database

| Component | Version | Purpose | Protocol |
|-----------|---------|---------|----------|
| **PostgreSQL** | Not specified (via SQLx 0.8) | Primary data store | PostgreSQL wire protocol |
| **SQLx** | 0.8.6 | Async database driver and query builder | Compile-time checked queries |

**SQLx Features**:
- `runtime-tokio-rustls` - Async runtime with Rustls TLS
- `macros` - Compile-time query validation with `query!` macro
- `postgres` - PostgreSQL driver
- `uuid` - UUID support
- `chrono` - DateTime support
- `migrate` - Database migration support

**Schema Management**: SQLx migrations (14 migration files)

### Caching & Session Store

| Component | Version | Purpose | Protocol |
|-----------|---------|---------|----------|
| **Redis** | Not specified (via actix-session) | Session storage | RESP (Redis Serialization Protocol) |

**Features**:
- Session persistence across application restarts
- Secure session token storage
- Automatic session expiration

---

## Security

### Password Hashing

| Component | Version | Purpose | Algorithm |
|-----------|---------|---------|-----------|
| **argon2** | 0.5.3 | Password hashing | Argon2id with secure defaults |

**Configuration**:
- PHC string format for storage
- Automatic salt generation
- Memory-hard algorithm resistant to GPU attacks

### Secret Management

| Component | Version | Purpose |
|-----------|---------|---------|
| **secrecy** | 0.10.3 | Secret type wrappers to prevent accidental logging |

**Usage**:
- Wraps database passwords
- Wraps HMAC secrets
- Wraps authorization tokens
- Wraps Redis connection strings

---

## Observability

### Logging & Tracing

| Component | Version | Purpose |
|-----------|---------|---------|
| **tracing** | 0.1.44 | Structured logging and distributed tracing |
| **tracing-subscriber** | 0.3.22 | Subscriber implementations for tracing |
| **tracing-bunyan-formatter** | 0.3.10 | JSON structured log formatting (Bunyan format) |
| **tracing-log** | 0.2.0 | Bridge between `log` and `tracing` |
| **tracing-actix-web** | 0.7.20 | HTTP request tracing middleware |

**Features**:
- Structured logging with JSON output
- Span-based distributed tracing
- Context propagation across async boundaries
- Environment-based log level filtering

---

## HTTP Client

| Component | Version | Purpose | Features |
|-----------|---------|---------|----------|
| **reqwest** | 0.12.26 | HTTP client for external API calls | `json`, `rustls-tls`, `cookies` |

**Usage**:
- Email service (Postmark) API integration
- TLS with Rustls (no OpenSSL dependency)
- JSON request/response serialization
- Cookie handling for session-based APIs

---

## Serialization & Data

### Serialization Framework

| Component | Version | Purpose |
|-----------|---------|---------|
| **serde** | 1.0.228 | Serialization/deserialization framework with derive macros |
| **serde_json** | 1.0.145 | JSON serialization |
| **serde-aux** | 4.7.0 | Additional serde utilities (e.g., deserialize numbers from strings) |
| **serde_urlencoded** | 0.7.1 | URL-encoded form data (dev dependency) |

### Data Types

| Component | Version | Purpose |
|-----------|---------|---------|
| **uuid** | 1.19.0 | UUID generation and handling | Features: `serde`, `v4` |
| **chrono** | 0.4.42 | Date and time handling | Features: `clock` |

---

## Configuration Management

| Component | Version | Purpose |
|-----------|---------|---------|
| **config** | 0.15.19 | Layered configuration with YAML and environment variables |

**Configuration Sources** (in order of precedence):
1. Environment variables (prefix: `APP_`, separator: `__`)
2. Environment-specific YAML (`local.yaml`, `production.yaml`)
3. Base YAML (`base.yaml`)

---

## Validation & Utilities

### Validation

| Component | Version | Purpose |
|-----------|---------|---------|
| **validator** | 0.18.1 | Input validation framework |
| **unicode-segmentation** | 1.12.0 | Unicode-aware string handling for name validation |

### Utilities

| Component | Version | Purpose |
|-----------|---------|---------|
| **rand** | 0.8.5 | Random number generation for tokens | Features: `std_rng` |

---

## Error Handling

| Component | Version | Purpose |
|-----------|---------|---------|
| **anyhow** | 1.0.100 | Error context and chaining for internal errors |
| **thiserror** | 1.0.69 | Custom error type derivation |

**Strategy**:
- `anyhow::Error` for internal error propagation with context
- `thiserror` for custom error types exposed via API
- `actix_web::ResponseError` for HTTP error mapping

---

## Testing

### Testing Frameworks

| Component | Version | Purpose | Environment |
|-----------|---------|---------|-------------|
| **assert2** | 0.3.16 | Enhanced assertions | Dev |
| **rstest** | 0.26 | Parameterized tests | Dev |
| **quickcheck** | 1.0.3 | Property-based testing | Dev |
| **quickcheck_macros** | 1 | Macros for quickcheck | Dev |

### Test Utilities

| Component | Version | Purpose | Environment |
|-----------|---------|---------|-------------|
| **fake** | 2.10.0 | Fake data generation | Dev |
| **wiremock** | 0.6 | HTTP mocking for external services | Dev |
| **linkify** | 0.10.0 | Link extraction from HTML | Dev |

**Test Coverage**:
- 7 integration test suites in `tests/api/`
- Unit tests embedded in source files
- HTTP mocking for email service

---

## Build System

### Build Tool

| Tool | Version | Purpose |
|------|---------|---------|
| **Cargo** | Bundled with Rust | Build system, dependency management, test runner |

### Binary Configuration

```toml
[package]
name = "zero2prod"
version = "0.16.0"
edition = "2024"

[[bin]]
path = "src/main.rs"
name = "zero2prod"

[lib]
path = "src/lib.rs"
```

---

## Infrastructure Services

### External Dependencies

| Service | Purpose | Protocol | Provider |
|---------|---------|----------|----------|
| **PostgreSQL** | Primary database | TCP (PostgreSQL wire protocol) | Self-hosted / Cloud |
| **Redis** | Session storage | TCP (RESP) | Self-hosted / Cloud |
| **Postmark** | Email delivery | HTTPS REST API | Third-party SaaS |

### Configuration Requirements

**PostgreSQL**:
- Host, port, username, password, database name
- SSL mode configuration (require/prefer)

**Redis**:
- Connection URI (e.g., `redis://127.0.0.1:6379`)

**Email Service**:
- Base URL
- Authorization token
- Sender email address
- Timeout configuration

---

## Deployment Requirements

### Runtime Requirements

- **Rust Toolchain**: Rust 2024 edition compiler
- **PostgreSQL Client Libraries**: Required for SQLx
- **TLS Libraries**: Rustls (no OpenSSL dependency)

### Environment Variables

**Required**:
- `APP_DATABASE__PASSWORD` - Database password
- `APP_APPLICATION__HMAC_SECRET` - HMAC signing secret
- `APP_EMAIL_CLIENT__AUTHORIZATION_TOKEN` - Email service token
- `APP_REDIS_URI` - Redis connection string

**Optional**:
- `APP_ENVIRONMENT` - Environment name (default: `local`)
- `APP_APPLICATION__PORT` - HTTP server port (default: 8000)
- `APP_APPLICATION__HOST` - HTTP server bind address (default: localhost)

### System Requirements

- **Memory**: Depends on connection pool sizes and concurrent requests
- **CPU**: Multi-core recommended for Tokio multi-threaded runtime
- **Network**: Outbound HTTPS for email service, PostgreSQL and Redis connectivity

---

## AWS Modernization Target Stack

### Proposed AWS Services

| Current Component | AWS Replacement | Notes |
|------------------|-----------------|-------|
| Self-hosted PostgreSQL | Amazon RDS for PostgreSQL | Managed, automated backups, read replicas |
| Self-hosted Redis | Amazon ElastiCache for Redis | Managed, automatic failover |
| Postmark API | Amazon SES | Native AWS email service |
| Monolithic web server | Amazon ECS Fargate + ALB | Container orchestration, horizontal scaling |
| Background worker | AWS Lambda + Amazon SQS | Event-driven, elastic scaling |
| Configuration files | AWS Secrets Manager + SSM Parameter Store | Centralized secret management |
| Structured logs | Amazon CloudWatch Logs | Log aggregation and analysis |
| Metrics | Amazon CloudWatch Metrics | Application and infrastructure metrics |
| Distributed tracing | AWS X-Ray | End-to-end request tracing |
| Container registry | Amazon ECR | Private Docker registry |

---

## Version Summary

### Core Dependencies

```toml
actix-web = "4.12.1"
tokio = "1.48.0"
sqlx = "0.8.6"
serde = "1.0.228"
reqwest = "0.12.26"
tracing = "0.1.44"
tracing-subscriber = "0.3.22"
anyhow = "1.0.100"
uuid = "1.19.0"
chrono = "0.4.42"
argon2 = "0.5.3"
config = "0.15.19"
```

### Total Dependencies

- **Production dependencies**: ~25
- **Dev dependencies**: ~10
- **No unsafe code dependencies noted**

---

## Technology Maturity Assessment

| Technology | Maturity | Rust Ecosystem Status | AWS Compatibility |
|-----------|----------|----------------------|-------------------|
| Tokio | Mature | Industry standard | Excellent |
| Actix-web | Mature | Production-ready | Excellent (runs anywhere) |
| SQLx | Mature | Well-supported | Excellent (RDS compatible) |
| Argon2 | Mature | Cryptographically sound | Excellent |
| Tracing | Mature | Industry standard | Good (CloudWatch export available) |
| Reqwest | Mature | De facto standard | Excellent |

**Overall Assessment**: Production-ready stack with excellent AWS modernization compatibility.
