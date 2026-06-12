# Component Inventory

## Component Classification

Components are organized by layer and responsibility following a clean architecture approach.

## Application Layer Components

### Binaries

| Component | Type | File Path | Description |
|-----------|------|-----------|-------------|
| zero2prod | Binary | `src/main.rs` | Main application entry point; spawns web server and background worker tasks |

### Application Services

| Component | Type | File Path | Description |
|-----------|------|-----------|-------------|
| Application | Struct | `src/startup.rs` | Application lifecycle manager; builds and runs HTTP server |
| Startup Module | Module | `src/startup.rs` | Server initialization, middleware setup, route registration |
| Configuration | Module | `src/configuration.rs` | Configuration loading with layered YAML and environment variables |
| Telemetry | Module | `src/telemetry.rs` | Observability setup with tracing subscriber initialization |
| Utils | Module | `src/utils.rs` | Utility functions for error handling and HTTP redirects |

### Background Workers

| Component | Type | File Path | Description |
|-----------|------|-----------|-------------|
| Issue Delivery Worker | Module | `src/issue_delivery_worker.rs` | Background worker for asynchronous email delivery from queue |

---

## Domain Layer Components

### Domain Models

| Component | Type | File Path | Description |
|-----------|------|-----------|-------------|
| SubscriberEmail | Struct | `src/domain/subscriber_email.rs` | Type-safe email address with validation |
| SubscriberName | Struct | `src/domain/subscriber_name.rs` | Type-safe subscriber name with validation rules |
| NewSubscriber | Struct | `src/domain/new_subscriber.rs` | Aggregate of validated subscriber data (email + name) |

### Domain Services

| Component | Type | File Path | Description |
|-----------|------|-----------|-------------|
| Email Validation | Function | `src/domain/subscriber_email.rs` | Email format and DNS validation logic |
| Name Validation | Function | `src/domain/subscriber_name.rs` | Name length and forbidden character validation |

---

## Routes Layer Components

### Public Route Handlers

| Component | HTTP Method | Route | File Path | Description |
|-----------|-------------|-------|-----------|-------------|
| health_check | GET | `/health_check` | `src/routes/health_check.rs` | Health check endpoint |
| home | GET | `/` | `src/routes/home/home.rs` | Home page rendering |
| subscribe | POST | `/subscriptions` | `src/routes/subscriptions.rs` | Newsletter subscription submission |
| confirm | GET | `/subscriptions/confirm` | `src/routes/subscriptions_confirm.rs` | Email confirmation handler |
| login_form | GET | `/login` | `src/routes/login/get.rs` | Login form rendering |
| login | POST | `/login` | `src/routes/login/post.rs` | Login submission handler |

### Protected Admin Route Handlers

| Component | HTTP Method | Route | File Path | Description |
|-----------|-------------|-------|-----------|-------------|
| admin_dashboard | GET | `/admin/dashboard` | `src/routes/admin/dashboard.rs` | Admin dashboard rendering |
| publish_newsletter_form | GET | `/admin/newsletters` | `src/routes/admin/newsletter/get.rs` | Newsletter submission form |
| publish_newsletter | POST | `/admin/newsletters` | `src/routes/admin/newsletter/post.rs` | Newsletter publishing handler (idempotent) |
| change_password_form | GET | `/admin/password` | `src/routes/admin/password/get.rs` | Password change form |
| change_password | POST | `/admin/password` | `src/routes/admin/password/post.rs` | Password change handler |
| log_out | POST | `/admin/logout` | `src/routes/admin/logout.rs` | Logout handler |

---

## Authentication & Authorization Components

### Authentication Services

| Component | Type | File Path | Description |
|-----------|------|-----------|-------------|
| Password Module | Module | `src/authentication/password.rs` | Argon2 password hashing and verification |
| Middleware | Module | `src/authentication/middleware.rs` | Authentication middleware for protecting routes |

### Authentication Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `compute_password_hash` | Hash password with Argon2id | `src/authentication/password.rs` |
| `verify_password_hash` | Verify password against hash | `src/authentication/password.rs` |
| `change_password` | Change user password | `src/authentication/password.rs` |
| `validate_credentials` | Validate username/password | `src/authentication/password.rs` |
| `reject_anonymous_users` | Middleware to protect admin routes | `src/authentication/middleware.rs` |

### Session Management

| Component | Type | File Path | Description |
|-----------|------|-----------|-------------|
| Session State | Module | `src/session_state.rs` | Session state types and utilities |
| TypedSession | Extension Trait | `src/session_state.rs` | Type-safe session operations |

---

## Idempotency Components

| Component | Type | File Path | Description |
|-----------|------|-----------|-------------|
| IdempotencyKey | Struct | `src/idempotency/key.rs` | Type-safe wrapper for idempotency keys |
| Persistence Module | Module | `src/idempotency/persistence.rs` | Database operations for idempotency tracking |
| `try_processing` | Function | `src/idempotency/persistence.rs` | Check for existing processing and return saved response |
| `save_response` | Function | `src/idempotency/persistence.rs` | Save response for future replay |
| `NextAction` | Enum | `src/idempotency/persistence.rs` | Indicates whether to start processing or return saved response |

---

## Infrastructure Components

### Email Client

| Component | Type | File Path | Description |
|-----------|------|-----------|-------------|
| EmailClient | Struct | `src/email_client.rs` | HTTP client for Postmark email service integration |
| `send_email` | Method | `src/email_client.rs` | Send email via Postmark API |
| SendEmailRequest | Struct | `src/email_client.rs` | Request body for Postmark API |

### Database Components

**ORM/Query Builder**: SQLx with compile-time checked queries

| Database Operation | Location | Purpose |
|-------------------|----------|---------|
| `insert_subscriber` | `src/routes/subscriptions.rs` | Insert pending subscriber |
| `store_token` | `src/routes/subscriptions.rs` | Store confirmation token |
| `get_stored_credentials` | `src/authentication/password.rs` | Retrieve user credentials |
| `insert_newsletter_issue` | `src/routes/admin/newsletter/post.rs` | Store newsletter issue |
| `enqueue_delivery_tasks` | `src/routes/admin/newsletter/post.rs` | Create delivery queue entries |
| `dequeue_task` | `src/issue_delivery_worker.rs` | Fetch task with row-level locking |
| `delete_task` | `src/issue_delivery_worker.rs` | Remove completed task |
| `get_issue` | `src/issue_delivery_worker.rs` | Fetch newsletter content |
| `get_connection_pool` | `src/startup.rs` | Create PostgreSQL connection pool |

### Middleware Components

| Middleware | Type | Purpose | Location |
|------------|------|---------|----------|
| TracingLogger | Actix Middleware | Request tracing and logging | `src/startup.rs` |
| SessionMiddleware | Actix Middleware | Session management with Redis | `src/startup.rs` |
| FlashMessagesFramework | Actix Middleware | Flash messages with signed cookies | `src/startup.rs` |
| reject_anonymous_users | Custom Middleware | Protect admin routes | `src/authentication/middleware.rs` |

---

## Testing Components

### Test Helpers

| Component | Type | File Path | Description |
|-----------|------|-----------|-------------|
| Test Helpers | Module | `tests/api/helpers.rs` | Utilities for spawning test apps, test database setup |

### Integration Tests

| Test Suite | File Path | Coverage |
|------------|-----------|----------|
| Health Check Tests | `tests/api/health_check.rs` | Health check endpoint |
| Subscription Tests | `tests/api/subscriptions.rs` | Subscription submission flow |
| Confirmation Tests | `tests/api/subscriptions_confirm.rs` | Email confirmation flow |
| Login Tests | `tests/api/login.rs` | Login authentication flow |
| Admin Dashboard Tests | `tests/api/admin_dashboard.rs` | Admin dashboard access |
| Password Change Tests | `tests/api/change_password.rs` | Password change flow |
| Newsletter Tests | `tests/api/newsletter.rs` | Newsletter publishing flow |

---

## Configuration Components

### Configuration Files

| File | Purpose | Location |
|------|---------|----------|
| base.yaml | Base configuration for all environments | `configuration/base.yaml` |
| local.yaml | Local development overrides | `configuration/local.yaml` |
| production.yaml | Production environment overrides | `configuration/production.yaml` |

### Configuration Types

| Type | Purpose | Location |
|------|---------|----------|
| Settings | Root configuration struct | `src/configuration.rs` |
| ApplicationSettings | HTTP server configuration | `src/configuration.rs` |
| DatabaseSettings | PostgreSQL connection settings | `src/configuration.rs` |
| EmailClientSettings | Email service configuration | `src/configuration.rs` |
| Environment | Environment enum (Local, Production) | `src/configuration.rs` |

---

## Database Migration Components

**Location**: `migrations/`

**Count**: 14 migrations

| Migration | Purpose |
|-----------|---------|
| `20251210215928_create_subscriptions_table.sql` | Create subscriptions table |
| `20251226002359_add_status_to_subscriptions.sql` | Add status column |
| `20251226005359_amke_status_null_in_subscriptions.sql` | Make status nullable |
| `20251226011630_create_subscription_tokens_table.sql` | Create subscription tokens table |
| `20260101203037_create_users_table.sql` | Create users table |
| `20260101224111_rename_password_column.sql` | Rename password column |
| `20260102031137_add_salt_to_users.sql` | Add salt column (later removed) |
| `20260102035438_remove_salt_from_users.sql` | Remove salt column |
| `20260108011439_seed_user.sql` | Seed initial admin user |
| `20260113140333_create_idempotency_table.sql` | Create idempotency table |
| `20260115043534_relax_null_checks_on_idempotency.sql` | Modify idempotency constraints |
| `20260115060534_create_newsletter_issue_table.sql` | Create newsletter issues table |
| `20260115061726_create_issue_delivery_queue_table.sql` | Create delivery queue table |

---

## External Service Components

### Third-Party Services

| Service | Purpose | Integration Point |
|---------|---------|-------------------|
| PostgreSQL | Primary data store | `src/startup.rs`, all database operations |
| Redis | Session storage | `src/startup.rs` (SessionMiddleware) |
| Postmark API | Email delivery | `src/email_client.rs` |

### Cloud Infrastructure (for AWS modernization)

**Current**: None (self-hosted)

**Target AWS Services**:
- Amazon RDS (PostgreSQL replacement)
- Amazon ElastiCache (Redis replacement)
- Amazon SES (Postmark replacement)
- Amazon SQS (Queue replacement for issue_delivery_queue)
- AWS Lambda (Background worker replacement)
- Amazon ECS/Fargate (Web server hosting)
- Application Load Balancer (Traffic distribution)
- AWS Secrets Manager (Configuration secrets)
- Amazon CloudWatch (Observability)

---

## Component Dependency Graph

```text
main.rs
  ├─→ startup::Application (web server)
  │     ├─→ configuration (settings)
  │     ├─→ routes (all handlers)
  │     ├─→ email_client (confirmation emails)
  │     ├─→ authentication (middleware)
  │     └─→ telemetry (tracing)
  │
  └─→ issue_delivery_worker (background worker)
        ├─→ configuration (settings)
        ├─→ email_client (newsletter emails)
        └─→ domain (email validation)

routes
  ├─→ domain (validation)
  ├─→ authentication (password, session)
  ├─→ idempotency (newsletter publishing)
  └─→ email_client (confirmation emails)

authentication
  └─→ session_state (session types)

idempotency
  └─→ (database operations)

email_client
  └─→ domain (email types)
```

---

## Component Counts Summary

| Category | Count |
|----------|-------|
| Binary Entry Points | 1 |
| Application Modules | 7 |
| Domain Models | 3 |
| Route Handlers (Public) | 6 |
| Route Handlers (Admin) | 6 |
| Authentication Functions | 5 |
| Idempotency Functions | 3 |
| Background Worker Functions | 5 |
| Middleware Components | 4 |
| Database Migrations | 14 |
| Integration Test Suites | 7 |
| Configuration Files | 3 |
| External Service Integrations | 3 |

**Total Rust Source Files**: 36
