# Code Structure Documentation

## Project Overview

**Project Type**: Rust library crate with binary
**Build System**: Cargo
**Edition**: Rust 2024
**Module Structure**: Library-based with single binary entry point

## Directory Structure

```text
zero2prod/
├── Cargo.toml                 # Project manifest and dependencies
├── configuration/             # YAML configuration files
│   ├── base.yaml             # Base configuration
│   ├── local.yaml            # Local environment overrides
│   └── production.yaml       # Production environment overrides
├── migrations/               # SQLx database migrations (14 files)
├── src/                      # Source code
│   ├── lib.rs               # Library entry point (module exports)
│   ├── main.rs              # Binary entry point (runtime initialization)
│   ├── authentication/      # Authentication and authorization
│   │   ├── mod.rs
│   │   ├── middleware.rs    # reject_anonymous_users middleware
│   │   └── password.rs      # Argon2 password hashing
│   ├── configuration.rs     # Configuration loading and types
│   ├── domain/              # Domain models and validation
│   │   ├── mod.rs
│   │   ├── new_subscriber.rs
│   │   ├── subscriber_email.rs
│   │   └── subscriber_name.rs
│   ├── email_client.rs      # Email service integration
│   ├── idempotency/         # Idempotency implementation
│   │   ├── mod.rs
│   │   ├── key.rs           # IdempotencyKey type
│   │   └── persistence.rs   # Database operations
│   ├── issue_delivery_worker.rs  # Background worker logic
│   ├── routes/              # HTTP route handlers
│   │   ├── mod.rs
│   │   ├── admin/           # Protected admin routes
│   │   │   ├── mod.rs
│   │   │   ├── dashboard.rs
│   │   │   ├── logout.rs
│   │   │   ├── newsletter/  # Newsletter management
│   │   │   │   ├── mod.rs
│   │   │   │   ├── get.rs   # Form rendering
│   │   │   │   └── post.rs  # Newsletter submission
│   │   │   └── password/    # Password management
│   │   │       ├── mod.rs
│   │   │       ├── get.rs   # Form rendering
│   │   │       └── post.rs  # Password change
│   │   ├── health_check.rs
│   │   ├── home/            # Home page
│   │   │   ├── mod.rs
│   │   │   └── home.rs
│   │   ├── login/           # Login flow
│   │   │   ├── mod.rs
│   │   │   ├── get.rs       # Login form
│   │   │   └── post.rs      # Login submission
│   │   ├── subscriptions.rs
│   │   └── subscriptions_confirm.rs
│   ├── session_state.rs     # Session state management
│   ├── startup.rs           # Application initialization
│   ├── telemetry.rs         # Observability setup
│   └── utils.rs             # Utility functions
└── tests/
    └── api/                 # Integration tests
        ├── main.rs
        ├── helpers.rs       # Test helpers
        ├── health_check.rs
        ├── subscriptions.rs
        ├── subscriptions_confirm.rs
        ├── login.rs
        ├── admin_dashboard.rs
        ├── change_password.rs
        └── newsletter.rs
```

## Key Modules Inventory

### Core Application (`src/`)

| File | Lines of Code (est.) | Purpose |
|------|---------------------|---------|
| `main.rs` | 50 | Binary entry point, spawns web server and worker tasks |
| `lib.rs` | 15 | Library entry point, re-exports modules |
| `startup.rs` | 124 | Application initialization, HTTP server setup, middleware configuration |
| `configuration.rs` | 139 | Configuration loading with layered YAML + environment variables |
| `telemetry.rs` | ~50 | Observability initialization (tracing setup) |
| `utils.rs` | ~50 | Utility functions for error handling and redirects |
| `session_state.rs` | ~50 | Session state management types |

### Domain Layer (`src/domain/`)

| File | Purpose | Key Types |
|------|---------|-----------|
| `subscriber_email.rs` | Email validation and type wrapper | `SubscriberEmail` |
| `subscriber_name.rs` | Name validation with forbidden character checks | `SubscriberName` |
| `new_subscriber.rs` | Aggregate for validated subscriber data | `NewSubscriber` |

**Validation Rules**:
- Email: Format validation + optional DNS verification
- Name: Length constraints, forbidden characters (`,`, `/`, `(`, `)`, `"`, `<`, `>`, `\`, `{`, `}`)

### Authentication (`src/authentication/`)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `password.rs` | Password hashing (Argon2) and verification | `compute_password_hash`, `verify_password_hash`, `change_password` |
| `middleware.rs` | Auth middleware for protecting routes | `reject_anonymous_users` |

**Security**:
- Argon2id algorithm with secure defaults
- Context preservation with `anyhow` for error chains
- Session-based authentication (user_id in session)

### Idempotency (`src/idempotency/`)

| File | Purpose |
|------|---------|
| `key.rs` | Type-safe idempotency key validation |
| `persistence.rs` | Database operations for idempotency tracking |

**Features**:
- Client-supplied idempotency keys
- Stores response (status, headers, body) for replay
- Prevents duplicate newsletter submissions

### Routes (`src/routes/`)

**Public Routes**:
- `GET /health_check` - Health check endpoint
- `GET /` - Home page
- `POST /subscriptions` - Subscribe to newsletter
- `GET /subscriptions/confirm` - Email confirmation
- `GET /login` - Login form
- `POST /login` - Login submission

**Protected Admin Routes** (require authentication):
- `GET /admin/dashboard` - Admin dashboard
- `GET /admin/newsletters` - Newsletter submission form
- `POST /admin/newsletters` - Publish newsletter (idempotent)
- `GET /admin/password` - Password change form
- `POST /admin/password` - Change password
- `POST /admin/logout` - Logout

### Background Worker (`src/issue_delivery_worker.rs`)

**Key Functions**:
- `run_worker_until_stopped`: Entry point for worker task
- `worker_loop`: Continuous polling loop
- `try_execute_task`: Dequeue task, send email, delete task
- `dequeue_task`: SELECT FOR UPDATE SKIP LOCKED pattern
- `delete_task`: Remove completed delivery task
- `get_issue`: Fetch newsletter content

**Execution Model**:
- Polls queue continuously
- 10-second sleep on empty queue
- 1-second backoff on errors
- Logs failures but continues processing

## Design Patterns

### 1. Repository Pattern
- Database operations encapsulated in functions (`insert_subscriber`, `store_token`, etc.)
- SQLx compile-time checked queries
- Transaction management at route handler level

### 2. Middleware Pipeline
```rust
App::new()
    .wrap(SessionMiddleware::new(...))      // Session management
    .wrap(FlashMessagesFramework::builder(...))  // Flash messages
    .wrap(TracingLogger::default())         // Request tracing
    .service(
        web::scope("/admin")
            .wrap(from_fn(reject_anonymous_users))  // Auth guard
            ...
    )
```

### 3. Type-Driven Design
- Newtype pattern for domain values (`SubscriberEmail`, `SubscriberName`, `IdempotencyKey`)
- `TryFrom` trait for validation
- Parse, don't validate principle

### 4. Actor Model (Implicit)
- Web server and background worker run concurrently
- Communicate via database (queue table)
- Row-level locking prevents race conditions

### 5. Idempotency Pattern
```rust
match try_processing(&pool, &idempotency_key, user_id).await? {
    NextAction::StartProcessing(transaction) => {
        // Execute business logic
        let response = ...;
        save_response(transaction, &idempotency_key, user_id, response).await?
    }
    NextAction::ReturnSavedResponse(response) => {
        // Return cached response
        response
    }
}
```

### 6. Error Handling Strategy
- `anyhow::Error` for internal errors (provides context chains)
- `thiserror` for custom error types (`SubscribeError`)
- `actix_web::ResponseError` for HTTP error mapping
- Structured error logging with cause chains

## Dependency Management

### Production Dependencies (Key Highlights)

**Web Framework**:
- `actix-web` 4.x - HTTP server
- `actix-session` 0.11 - Session management with Redis
- `actix-web-flash-messages` 0.5 - Flash messages with cookies

**Async Runtime**:
- `tokio` 1.x - Async runtime with macros and multi-threaded executor

**Database**:
- `sqlx` 0.8 - Compile-time checked SQL queries, PostgreSQL driver, migrations

**Security**:
- `argon2` 0.5 - Password hashing
- `secrecy` 0.10 - Secret management (prevents logging)

**Observability**:
- `tracing` 0.1 - Structured logging
- `tracing-subscriber` 0.3 - Tracing subscriber with environment filter
- `tracing-bunyan-formatter` 0.3 - JSON structured logs
- `tracing-actix-web` 0.7 - HTTP request tracing

**Data Serialization**:
- `serde` 1.x - Serialization framework
- `serde_json` 1.x - JSON support
- `serde-aux` 4.x - Serde helper functions

**Utilities**:
- `uuid` 1.x - UUID generation
- `chrono` 0.4 - Date/time handling
- `rand` 0.8 - Random token generation
- `validator` 0.18 - Validation framework
- `unicode-segmentation` 1.x - Unicode string handling
- `config` 0.15 - Configuration management
- `reqwest` 0.12 - HTTP client for email service

**Error Handling**:
- `anyhow` 1.x - Error context and chaining
- `thiserror` 1.x - Custom error types

### Development Dependencies

**Testing**:
- `assert2` 0.3 - Enhanced assertions
- `rstest` 0.26 - Parameterized tests
- `fake` 2.9 - Fake data generation
- `quickcheck` 1.0 - Property-based testing
- `wiremock` 0.6 - HTTP mocking for email client tests

**Test Utilities**:
- `linkify` 0.10 - Link extraction from HTML
- `serde_urlencoded` 0.7 - URL encoding for forms

## Build Configuration

### Cargo.toml Highlights

**Binary Configuration**:
```toml
[[bin]]
path = "src/main.rs"
name = "zero2prod"
```

**Library Configuration**:
```toml
[lib]
path = "src/lib.rs"
```

**Edition**:
```toml
edition = "2024"
```

**SQLx Features**:
- `runtime-tokio-rustls` - Async runtime with TLS
- `macros` - Compile-time checked queries
- `postgres` - PostgreSQL driver
- `migrate` - Migration support

**Reqwest Features**:
- `json` - JSON request/response bodies
- `rustls-tls` - TLS with Rustls (no OpenSSL dependency)
- `cookies` - Cookie handling

## Code Quality Indicators

### Modularization
- Well-organized module structure with clear separation of concerns
- Domain layer isolated from infrastructure
- Routes organized by access level (public vs admin)

### Type Safety
- Heavy use of newtype pattern for domain values
- Compile-time SQL checking with SQLx
- Minimal use of unwrap() in production code paths

### Testability
- 9 integration test modules
- Test helpers extracted to `tests/api/helpers.rs`
- Wiremock for external service mocking

### Documentation
- Module-level comments with file paths
- Tracing instrumentation for observability
- Structured error messages

## Technical Debt Observations

1. **Monolithic Structure**: Single binary with dual runtime tasks limits independent scaling
2. **Background Worker**: Single polling loop cannot scale horizontally safely
3. **Session Storage**: Redis dependency creates stateful deployment complexity
4. **Email Provider Coupling**: Tightly coupled to Postmark API structure
5. **Configuration**: No secrets management integration (AWS Secrets Manager, etc.)
6. **Database Migrations**: Manual migration management (no automated rollback)
7. **No API Versioning**: Routes lack versioning strategy
8. **Limited Observability**: No distributed tracing IDs, no metrics exports

## Migration Readiness

### AWS Modernization Candidates

**High Priority**:
- Replace background worker with SQS + Lambda
- Replace Redis sessions with DynamoDB or ElastiCache
- Use RDS PostgreSQL with automated backups
- Deploy web tier on ECS Fargate with ALB

**Medium Priority**:
- Replace Postmark with SES
- Integrate AWS Secrets Manager for configuration
- Add CloudWatch metrics and dashboards
- Implement X-Ray distributed tracing

**Low Priority**:
- Containerize with multi-stage Docker builds
- Implement blue/green deployments
- Add API Gateway for rate limiting and caching
