# Interaction Diagrams

## Overview

This document contains sequence diagrams showing how key business transactions are implemented across components in the zero2prod system.

---

## 1. Subscription Registration Flow

**Business Transaction**: User subscribes to newsletter with email confirmation

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant ActixWeb as Actix Web Server
    participant SubscribeHandler as subscribe() Handler
    participant Domain as Domain Layer
    participant PostgreSQL
    participant EmailClient
    participant Postmark as Postmark API

    User->>Browser: Fill subscription form
    Browser->>ActixWeb: POST /subscriptions<br/>(name, email)
    ActixWeb->>SubscribeHandler: Route to handler
    
    Note over SubscribeHandler: Parse form data
    SubscribeHandler->>Domain: FormData.try_into()<br/>NewSubscriber
    Domain->>Domain: SubscriberName::parse(name)
    Domain->>Domain: SubscriberEmail::parse(email)
    
    alt Validation fails
        Domain-->>SubscribeHandler: Err(ValidationError)
        SubscribeHandler-->>Browser: 400 Bad Request
        Browser-->>User: Show error
    else Validation succeeds
        Domain-->>SubscribeHandler: Ok(NewSubscriber)
        
        SubscribeHandler->>PostgreSQL: BEGIN transaction
        PostgreSQL-->>SubscribeHandler: Transaction started
        
        SubscribeHandler->>PostgreSQL: INSERT INTO subscriptions<br/>(id, email, name, status='pending')
        PostgreSQL-->>SubscribeHandler: subscriber_id
        
        SubscribeHandler->>SubscribeHandler: generate_subscription_token()<br/>(25-char random)
        
        SubscribeHandler->>PostgreSQL: INSERT INTO subscription_tokens<br/>(token, subscriber_id)
        PostgreSQL-->>SubscribeHandler: OK
        
        SubscribeHandler->>PostgreSQL: COMMIT transaction
        PostgreSQL-->>SubscribeHandler: Committed
        
        Note over SubscribeHandler: Build confirmation link
        SubscribeHandler->>EmailClient: send_email(email, "Welcome!", html, text)
        EmailClient->>Postmark: POST /email<br/>(From, To, Subject, Body)
        Postmark-->>EmailClient: 200 OK
        EmailClient-->>SubscribeHandler: OK
        
        SubscribeHandler-->>Browser: 200 OK
        Browser-->>User: Show success message
    end
```

**Key Components**:
- **Route Handler**: `src/routes/subscriptions.rs::subscribe()`
- **Domain Validation**: `src/domain/subscriber_email.rs`, `src/domain/subscriber_name.rs`
- **Database Operations**: `insert_subscriber()`, `store_token()`
- **Email Client**: `src/email_client.rs::send_email()`

---

## 2. Email Confirmation Flow

**Business Transaction**: User confirms subscription via email link

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant ActixWeb as Actix Web Server
    participant ConfirmHandler as confirm() Handler
    participant PostgreSQL

    User->>Browser: Click confirmation link in email
    Browser->>ActixWeb: GET /subscriptions/confirm<br/>?subscription_token=abc123
    ActixWeb->>ConfirmHandler: Route to handler
    
    Note over ConfirmHandler: Extract token from query
    
    ConfirmHandler->>PostgreSQL: SELECT subscriber_id<br/>FROM subscription_tokens<br/>WHERE token = $1
    
    alt Token not found
        PostgreSQL-->>ConfirmHandler: None
        ConfirmHandler-->>Browser: 401 Unauthorized
        Browser-->>User: Show error page
    else Token found
        PostgreSQL-->>ConfirmHandler: subscriber_id
        
        ConfirmHandler->>PostgreSQL: BEGIN transaction
        PostgreSQL-->>ConfirmHandler: Transaction started
        
        ConfirmHandler->>PostgreSQL: UPDATE subscriptions<br/>SET status = 'confirmed'<br/>WHERE id = $1
        PostgreSQL-->>ConfirmHandler: OK
        
        ConfirmHandler->>PostgreSQL: DELETE FROM subscription_tokens<br/>WHERE token = $1
        PostgreSQL-->>ConfirmHandler: OK
        
        ConfirmHandler->>PostgreSQL: COMMIT transaction
        PostgreSQL-->>ConfirmHandler: Committed
        
        ConfirmHandler-->>Browser: 200 OK (HTML page)
        Browser-->>User: Show confirmation success
    end
```

**Key Components**:
- **Route Handler**: `src/routes/subscriptions_confirm.rs::confirm()`
- **Database Operations**: Token lookup, status update, token deletion

---

## 3. Admin Login Flow

**Business Transaction**: Admin authenticates and creates session

```mermaid
sequenceDiagram
    participant Admin
    participant Browser
    participant ActixWeb as Actix Web Server
    participant LoginHandler as login() Handler
    participant AuthModule as Authentication Module
    participant PostgreSQL
    participant Redis

    Admin->>Browser: Submit login form
    Browser->>ActixWeb: POST /login<br/>(username, password)
    ActixWeb->>LoginHandler: Route to handler
    
    Note over LoginHandler: Extract credentials from form
    
    LoginHandler->>AuthModule: validate_credentials(username, password)
    AuthModule->>PostgreSQL: SELECT user_id, password_hash<br/>FROM users<br/>WHERE username = $1
    
    alt User not found
        PostgreSQL-->>AuthModule: None
        AuthModule-->>LoginHandler: Err(InvalidCredentials)
        LoginHandler->>LoginHandler: Set flash message (error)
        LoginHandler-->>Browser: 303 See Other → /login
        Browser-->>Admin: Show login form with error
    else User found
        PostgreSQL-->>AuthModule: (user_id, password_hash)
        
        AuthModule->>AuthModule: verify_password_hash(password, hash)
        Note over AuthModule: Argon2id verification
        
        alt Password incorrect
            AuthModule-->>LoginHandler: Err(InvalidCredentials)
            LoginHandler->>LoginHandler: Set flash message (error)
            LoginHandler-->>Browser: 303 See Other → /login
            Browser-->>Admin: Show login form with error
        else Password correct
            AuthModule-->>LoginHandler: Ok(user_id)
            
            LoginHandler->>Redis: Create session<br/>Set user_id in session
            Redis-->>LoginHandler: session_id
            
            LoginHandler-->>Browser: 303 See Other → /admin/dashboard<br/>Set-Cookie: session_id
            Browser->>ActixWeb: GET /admin/dashboard<br/>(Cookie: session_id)
            ActixWeb->>Redis: Retrieve session by session_id
            Redis-->>ActixWeb: user_id
            ActixWeb-->>Browser: 200 OK (HTML dashboard)
            Browser-->>Admin: Show dashboard
        end
    end
```

**Key Components**:
- **Route Handler**: `src/routes/login/post.rs::login()`
- **Authentication**: `src/authentication/password.rs::validate_credentials()`, `verify_password_hash()`
- **Session Management**: `src/session_state.rs` with Redis storage

---

## 4. Newsletter Publishing Flow (with Idempotency)

**Business Transaction**: Admin publishes newsletter issue to all confirmed subscribers

```mermaid
sequenceDiagram
    participant Admin
    participant Browser
    participant ActixWeb as Actix Web Server
    participant AuthMiddleware as Auth Middleware
    participant PublishHandler as publish_newsletter() Handler
    participant IdempotencyModule as Idempotency Module
    participant PostgreSQL
    participant Redis

    Admin->>Browser: Submit newsletter form
    Browser->>ActixWeb: POST /admin/newsletters<br/>(title, text, html, idempotency_key)<br/>Cookie: session_id
    ActixWeb->>AuthMiddleware: reject_anonymous_users
    AuthMiddleware->>Redis: Retrieve session by session_id
    Redis-->>AuthMiddleware: user_id
    
    alt Not authenticated
        AuthMiddleware-->>Browser: 303 See Other → /login
        Browser-->>Admin: Redirect to login
    else Authenticated
        AuthMiddleware->>PublishHandler: Request with user_id
        
        Note over PublishHandler: Extract form data
        PublishHandler->>IdempotencyModule: try_processing(pool, idempotency_key, user_id)
        IdempotencyModule->>PostgreSQL: SELECT response_status, headers, body<br/>FROM idempotency<br/>WHERE user_id = $1 AND key = $2
        
        alt Idempotency record exists
            PostgreSQL-->>IdempotencyModule: (status, headers, body)
            IdempotencyModule-->>PublishHandler: ReturnSavedResponse(response)
            PublishHandler->>PublishHandler: Set flash message (success)
            PublishHandler-->>Browser: 303 See Other → /admin/newsletters<br/>(cached response)
            Browser-->>Admin: Show success (duplicate blocked)
        else First submission
            PostgreSQL-->>IdempotencyModule: None
            IdempotencyModule->>PostgreSQL: BEGIN transaction
            PostgreSQL-->>IdempotencyModule: transaction
            IdempotencyModule-->>PublishHandler: StartProcessing(transaction)
            
            Note over PublishHandler: Generate newsletter_issue_id
            PublishHandler->>PostgreSQL: INSERT INTO newsletter_issues<br/>(id, title, text, html, published_at)
            PostgreSQL-->>PublishHandler: OK
            
            PublishHandler->>PostgreSQL: INSERT INTO issue_delivery_queue<br/>(issue_id, subscriber_email)<br/>SELECT issue_id, email FROM subscriptions<br/>WHERE status = 'confirmed'
            Note over PostgreSQL: One queue entry per confirmed subscriber
            PostgreSQL-->>PublishHandler: N rows inserted
            
            PublishHandler->>IdempotencyModule: save_response(transaction, key, user_id, response)
            IdempotencyModule->>PostgreSQL: INSERT INTO idempotency<br/>(user_id, key, status, headers, body)
            PostgreSQL-->>IdempotencyModule: OK
            
            IdempotencyModule->>PostgreSQL: COMMIT transaction
            PostgreSQL-->>IdempotencyModule: Committed
            IdempotencyModule-->>PublishHandler: response
            
            PublishHandler->>PublishHandler: Set flash message (success)
            PublishHandler-->>Browser: 303 See Other → /admin/newsletters
            Browser-->>Admin: Show success message
        end
    end
```

**Key Components**:
- **Route Handler**: `src/routes/admin/newsletter/post.rs::publish_newsletter()`
- **Auth Middleware**: `src/authentication/middleware.rs::reject_anonymous_users()`
- **Idempotency**: `src/idempotency/persistence.rs::try_processing()`, `save_response()`
- **Database Operations**: `insert_newsletter_issue()`, `enqueue_delivery_tasks()`

---

## 5. Background Email Delivery Flow

**Business Transaction**: Async worker processes newsletter delivery queue

```mermaid
sequenceDiagram
    participant Worker as Background Worker
    participant PostgreSQL
    participant EmailClient
    participant Postmark as Postmark API

    loop Continuous polling
        Worker->>PostgreSQL: BEGIN transaction
        PostgreSQL-->>Worker: transaction
        
        Worker->>PostgreSQL: SELECT issue_id, subscriber_email<br/>FROM issue_delivery_queue<br/>FOR UPDATE SKIP LOCKED<br/>LIMIT 1
        
        alt Queue empty
            PostgreSQL-->>Worker: None
            Worker->>PostgreSQL: ROLLBACK transaction
            PostgreSQL-->>Worker: OK
            Worker->>Worker: Sleep 10 seconds
        else Task found
            PostgreSQL-->>Worker: (issue_id, subscriber_email)
            
            Note over Worker: Parse and validate email
            Worker->>Worker: SubscriberEmail::parse(email)
            
            alt Email invalid
                Worker->>Worker: Log error, skip subscriber
                Worker->>PostgreSQL: DELETE FROM issue_delivery_queue<br/>WHERE issue_id = $1 AND email = $2
                PostgreSQL-->>Worker: OK
                Worker->>PostgreSQL: COMMIT transaction
                PostgreSQL-->>Worker: Committed
            else Email valid
                Worker->>PostgreSQL: SELECT title, text_content, html_content<br/>FROM newsletter_issues<br/>WHERE issue_id = $1
                PostgreSQL-->>Worker: (title, text, html)
                
                Worker->>EmailClient: send_email(email, title, html, text)
                EmailClient->>Postmark: POST /email<br/>(From, To, Subject, Body)
                
                alt Email send fails
                    Postmark-->>EmailClient: 4xx/5xx error
                    EmailClient-->>Worker: Err(error)
                    Worker->>Worker: Log error
                    Worker->>Worker: Sleep 1 second (backoff)
                else Email sent successfully
                    Postmark-->>EmailClient: 200 OK
                    EmailClient-->>Worker: OK
                    
                    Worker->>PostgreSQL: DELETE FROM issue_delivery_queue<br/>WHERE issue_id = $1 AND email = $2
                    PostgreSQL-->>Worker: OK
                    
                    Worker->>PostgreSQL: COMMIT transaction
                    PostgreSQL-->>Worker: Committed
                end
            end
        end
    end
```

**Key Components**:
- **Worker**: `src/issue_delivery_worker.rs::worker_loop()`, `try_execute_task()`
- **Queue Operations**: `dequeue_task()`, `delete_task()`
- **Content Retrieval**: `get_issue()`
- **Email Client**: `src/email_client.rs::send_email()`

**Concurrency Safety**:
- `FOR UPDATE SKIP LOCKED` prevents multiple workers from processing the same task
- Transaction ensures atomic dequeue + send + delete

---

## 6. Password Change Flow

**Business Transaction**: Admin changes their password

```mermaid
sequenceDiagram
    participant Admin
    participant Browser
    participant ActixWeb as Actix Web Server
    participant AuthMiddleware as Auth Middleware
    participant PasswordHandler as change_password() Handler
    participant AuthModule as Authentication Module
    participant PostgreSQL
    participant Redis

    Admin->>Browser: Submit password change form
    Browser->>ActixWeb: POST /admin/password<br/>(current, new, new_check)<br/>Cookie: session_id
    ActixWeb->>AuthMiddleware: reject_anonymous_users
    AuthMiddleware->>Redis: Retrieve session by session_id
    Redis-->>AuthMiddleware: user_id
    
    alt Not authenticated
        AuthMiddleware-->>Browser: 303 See Other → /login
        Browser-->>Admin: Redirect to login
    else Authenticated
        AuthMiddleware->>PasswordHandler: Request with user_id
        
        Note over PasswordHandler: Validate form inputs
        PasswordHandler->>PasswordHandler: Check new == new_check
        PasswordHandler->>PasswordHandler: Validate length (12-128)
        
        alt Validation fails
            PasswordHandler->>PasswordHandler: Set flash message (error)
            PasswordHandler-->>Browser: 303 See Other → /admin/password
            Browser-->>Admin: Show form with error
        else Validation passes
            PasswordHandler->>AuthModule: change_password(user_id, current, new)
            AuthModule->>PostgreSQL: SELECT username, password_hash<br/>FROM users WHERE user_id = $1
            PostgreSQL-->>AuthModule: (username, old_hash)
            
            AuthModule->>AuthModule: verify_password_hash(current, old_hash)
            Note over AuthModule: Argon2id verification
            
            alt Current password incorrect
                AuthModule-->>PasswordHandler: Err(InvalidPassword)
                PasswordHandler->>PasswordHandler: Set flash message (error)
                PasswordHandler-->>Browser: 303 See Other → /admin/password
                Browser-->>Admin: Show form with error
            else Current password correct
                AuthModule->>AuthModule: compute_password_hash(new)
                Note over AuthModule: Argon2id hashing
                AuthModule->>PostgreSQL: UPDATE users<br/>SET password_hash = $1<br/>WHERE user_id = $2
                PostgreSQL-->>AuthModule: OK
                
                AuthModule-->>PasswordHandler: OK
                PasswordHandler->>PasswordHandler: Set flash message (success)
                PasswordHandler-->>Browser: 303 See Other → /admin/password
                Browser-->>Admin: Show success message
            end
        end
    end
```

**Key Components**:
- **Route Handler**: `src/routes/admin/password/post.rs::change_password()`
- **Auth Module**: `src/authentication/password.rs::change_password()`, `verify_password_hash()`, `compute_password_hash()`

---

## Component Interaction Summary

### Component Communication Patterns

| Source Component | Target Component | Communication Type | Protocol |
|-----------------|------------------|-------------------|----------|
| Route Handlers | Domain Layer | Function Call | In-process |
| Route Handlers | PostgreSQL | SQL Query | PostgreSQL wire protocol |
| Route Handlers | Redis | Session Operations | RESP protocol (via actix-session) |
| Route Handlers | Email Client | Method Call | In-process |
| Email Client | Postmark API | HTTP POST | HTTPS REST |
| Background Worker | PostgreSQL | SQL Query | PostgreSQL wire protocol |
| Background Worker | Email Client | Method Call | In-process |
| Middleware | Redis | Session Lookup | RESP protocol |

### Data Flow Patterns

**Request-Response (Synchronous)**:
- User → Browser → Web Server → PostgreSQL → Web Server → Browser → User
- Latency-sensitive operations
- Blocking user interaction

**Fire-and-Forget (Asynchronous)**:
- Newsletter Publish → Queue → Background Worker → Email API
- Long-running operations
- Non-blocking user interaction

**Polling (Periodic)**:
- Background Worker continuously polls queue
- 10-second interval on empty queue
- 1-second backoff on errors

---

## Error Handling Patterns

### Retry Strategy

**Email Sending**:
- No automatic retries in application code
- Background worker continues on email failure (logs error)
- Failed tasks remain in queue (idempotent)

**Database Operations**:
- No automatic retries
- Rely on transaction rollback for consistency
- Errors propagated to user via flash messages or error pages

### Circuit Breaker

**Current Implementation**: None

**AWS Modernization Opportunity**: Add circuit breaker for external services using `resilience4j` pattern or AWS App Mesh

---

## Scalability Analysis

### Bottlenecks

1. **Background Worker**:
   - Single polling loop
   - Sequential processing
   - Cannot scale horizontally due to `FOR UPDATE SKIP LOCKED` limitation

2. **Session Storage**:
   - Single Redis instance
   - No automatic failover
   - All sessions lost if Redis crashes

3. **Email API**:
   - Rate-limited by Postmark
   - Sequential sending from single worker

### Scaling Strategies

**Web Tier**:
- ✅ Can scale horizontally (stateless)
- ✅ Load balancer ready (no session affinity needed)
- ✅ Connection pooling handles multiple instances

**Worker Tier**:
- ⚠️ Cannot scale horizontally with current polling model
- 🔄 **AWS Solution**: Replace with SQS + Lambda (automatic scaling)

**Data Tier**:
- ✅ PostgreSQL read replicas for read scaling
- ✅ Redis cluster for session HA
- ✅ RDS for automated backups and failover

---

## Observability in Interactions

### Tracing Spans

**Per-Transaction Spans**:
- `subscribe()` → Database operations → Email sending
- `publish_newsletter()` → Idempotency check → Queue creation
- `try_execute_task()` → Queue dequeue → Email sending

**Span Fields**:
- `subscriber_email`
- `newsletter_issue_id`
- `user_id`

### Log Correlation

**Request ID**: Not implemented (opportunity for X-Ray trace IDs)

**Error Context**: Propagated via `anyhow` with cause chains

---

## AWS Modernization Impact on Interactions

### Proposed Changes

**Queue-Based Worker**:
```mermaid
graph LR
    PublishHandler --> SQS[Amazon SQS]
    SQS --> Lambda[AWS Lambda]
    Lambda --> SES[Amazon SES]
```

**Session Management**:
```text
Redis → Amazon ElastiCache (Redis-compatible)
OR
Redis → Amazon DynamoDB (session table)
```

**Database**:
```text
PostgreSQL → Amazon RDS for PostgreSQL
(Minimal code changes, connection string only)
```

**Observability**:
```text
Tracing → AWS X-Ray (via OpenTelemetry)
Logs → CloudWatch Logs
Metrics → CloudWatch Metrics
```
