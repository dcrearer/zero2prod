# Zero2Prod

A production-ready newsletter service built with Rust, featuring subscription management, authentication, newsletter publishing with idempotency, background email delivery, and PostgreSQL integration.

**Version:** 0.16.0

## Features

- **RESTful API** - Health check, subscription, authentication, and admin endpoints
- **PostgreSQL Integration** - Type-safe database queries with sqlx
- **Structured Logging** - JSON-formatted tracing with Bunyan
- **Configuration Management** - YAML-based settings with environment overrides
- **Email Confirmation** - Two-step subscription process with email verification
- **Token Management** - Secure subscription token generation and validation
- **Authentication & Authorization** - Session-based auth with password hashing (Argon2)
- **Admin Dashboard** - Protected admin interface for newsletter management
- **Newsletter Publishing** - Idempotent newsletter creation and delivery
- **Background Worker** - Asynchronous email delivery queue with retry logic
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

### Run Background Worker
```bash
cargo run --bin issue_delivery_worker
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

### Public Endpoints
| Method | Path                     | Description                                                   |
|--------|--------------------------|---------------------------------------------------------------|
| GET    | `/`                      | Home page                                                     |
| GET    | `/health_check`          | Health monitoring endpoint                                    |
| POST   | `/subscriptions`         | Newsletter subscription (form data: name, email)              |
| GET    | `/subscriptions/confirm` | Email confirmation endpoint (query param: subscription_token) |
| GET    | `/login`                 | Login form                                                    |
| POST   | `/login`                 | Login submission (form data: username, password)              |

### Protected Admin Endpoints (Requires Authentication)
| Method | Path                     | Description                                                   |
|--------|--------------------------|---------------------------------------------------------------|
| GET    | `/admin/dashboard`       | Admin dashboard                                               |
| GET    | `/admin/newsletters`     | Newsletter publishing form                                    |
| POST   | `/admin/newsletters`     | Publish newsletter (JSON: title, text_content, html_content, idempotency_key) |
| GET    | `/admin/password`        | Change password form                                          |
| POST   | `/admin/password`        | Change password submission                                    |
| POST   | `/admin/logout`          | Logout                                                        |

## Project Structure

```text
zero2prod/
├── src/
│   ├── main.rs                      # Application entry point
│   ├── lib.rs                       # Library exports
│   ├── configuration.rs             # Settings & database config
│   ├── startup.rs                   # HTTP server setup
│   ├── telemetry.rs                 # Logging configuration
│   ├── email_client.rs              # Email service integration
│   ├── session_state.rs             # Session management
│   ├── utils.rs                     # Utility functions
│   ├── issue_delivery_worker.rs     # Background email delivery worker
│   ├── authentication/              # Authentication & authorization
│   │   ├── mod.rs
│   │   ├── middleware.rs            # Auth middleware
│   │   └── password.rs              # Password hashing/verification
│   ├── domain/                      # Domain models and validation
│   │   ├── mod.rs
│   │   ├── new_subscriber.rs
│   │   ├── subscriber_email.rs
│   │   └── subscriber_name.rs
│   ├── idempotency/                 # Idempotency key management
│   │   ├── mod.rs
│   │   ├── key.rs
│   │   └── persistence.rs
│   └── routes/
│       ├── mod.rs
│       ├── health_check.rs          # Health endpoint
│       ├── home/                    # Home page
│       ├── login/                   # Login endpoints
│       │   ├── get.rs
│       │   └── post.rs
│       ├── subscriptions.rs         # Subscription endpoint
│       ├── subscriptions_confirm.rs # Email confirmation
│       └── admin/                   # Protected admin routes
│           ├── dashboard.rs
│           ├── logout.rs
│           ├── newsletter/          # Newsletter publishing
│           │   ├── get.rs
│           │   └── post.rs
│           └── password/            # Password management
│               ├── get.rs
│               └── post.rs
├── tests/
│   └── api/                         # Integration tests
│       ├── main.rs
│       ├── helpers.rs
│       ├── health_check.rs
│       ├── subscriptions.rs
│       ├── subscriptions_confirm.rs
│       ├── login.rs
│       ├── admin_dashboard.rs
│       ├── change_password.rs
│       └── newsletter.rs
├── migrations/                      # Database schema
│   ├── *_create_subscriptions_table.sql
│   ├── *_create_subscription_tokens_table.sql
│   ├── *_create_users_table.sql
│   ├── *_create_idempotency_table.sql
│   ├── *_create_newsletter_issue_table.sql
│   └── *_create_issue_delivery_queue_table.sql
├── scripts/
│   ├── init_db.sh                   # Database initialization
│   └── release-and-build.sh         # Release automation
├── configuration/                   # YAML config files
└── Dockerfile                       # Container definition
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
SessionStore (Redis-backed sessions)
  |
HttpServer (actix-web) -> routes (public + admin)
  |
Authentication Middleware -> admin routes

Background Worker:
issue_delivery_worker -> PgPool + EmailClient -> process delivery queue
```

### Request Flow

#### Public Routes
1. **main** → Load configuration → Initialize telemetry → Connect to database
2. **startup** → Create HTTP server → Register routes → Setup session middleware
3. **routes** → Handle requests → Database operations → Response

#### Admin Routes (Protected)
1. Request → Session middleware → Check authentication
2. If authenticated → Route handler → Database operations → Response
3. If not authenticated → Redirect to `/login`

#### Newsletter Publishing Flow
1. Admin submits newsletter (with idempotency key)
2. Check idempotency table (prevent duplicates)
3. Insert newsletter into `newsletter_issues` table
4. Queue delivery tasks in `issue_delivery_queue` (one per confirmed subscriber)
5. Return success response
6. Background worker processes queue asynchronously

#### Background Email Delivery
1. Worker polls `issue_delivery_queue` table
2. Dequeue task with `FOR UPDATE SKIP LOCKED` (prevents race conditions)
3. Send email via EmailClient
4. Delete task from queue on success
5. Repeat until queue is empty

## Key Technologies

- **Web Framework**: actix-web 4.x
- **Database**: PostgreSQL with sqlx (compile-time verified queries)
- **Async Runtime**: tokio
- **Logging**: tracing + tracing-bunyan-formatter
- **Configuration**: config crate with YAML
- **Security**: 
  - secrecy for sensitive data
  - argon2 for password hashing
  - actix-session for session management
- **Testing**: wiremock for HTTP mocking

## Database Schema

### Core Tables
- **subscriptions** - Subscriber information with confirmation status
- **subscription_tokens** - Email confirmation tokens
- **users** - Admin user credentials (hashed passwords)
- **newsletter_issues** - Published newsletters
- **issue_delivery_queue** - Pending email delivery tasks
- **idempotency** - Idempotency key tracking for duplicate prevention

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

Integration tests use isolated PostgreSQL databases with unique names per test run. Tests cover:
- Health checks
- Subscription flow (create + confirm)
- Authentication (login/logout)
- Admin dashboard access
- Password changes
- Newsletter publishing (including idempotency and concurrency)

```bash
cargo test                # Run all tests
cargo test --lib          # Run unit tests only (15 tests)
cargo test --test api     # Run integration tests only
cargo nextest run         # Parallel test execution
```

## Security Features

- **Password Security**: Argon2id hashing with PHC string format
- **Session Management**: Secure session cookies with Redis backend
- **SQL Injection Prevention**: Parameterized queries via sqlx
- **CSRF Protection**: Session-based authentication
- **Idempotency**: Prevents duplicate newsletter sends
- **Database Locking**: `FOR UPDATE SKIP LOCKED` prevents race conditions

---
*Last updated: 2026-01-15*
