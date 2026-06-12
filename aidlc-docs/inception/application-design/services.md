# Service Layer Design

## Overview

This document defines the service layer orchestration patterns for the AWS modernized architecture. It covers how components interact, AWS service integration patterns, and cross-cutting concerns like logging, tracing, and secrets management.

---

## Service Layer Architecture

The service layer acts as the orchestration tier between the presentation layer (HTTP routes) and the data layer (Aurora, ElastiCache, SQS). It encapsulates business logic and AWS service integrations.

### Service Layer Responsibilities

1. **Business Logic Orchestration**: Coordinate multi-step operations across data stores
2. **AWS Service Integration**: Abstract AWS SDK calls behind clean interfaces
3. **Transaction Management**: Ensure data consistency across Aurora operations
4. **Error Handling**: Translate AWS errors to application errors with context
5. **Observability**: Emit structured logs and traces for all operations

---

## Core Services

### 1. Subscription Service

**Purpose**: Handle newsletter subscription lifecycle (create, confirm, unsubscribe).

**Operations**:

#### 1.1 Create Subscription
```rust
pub async fn create_subscription(
    pool: &PgPool,
    email_client: &EmailClient,
    subscriber: NewSubscriber,
    base_url: &str,
) -> Result<(), SubscriptionError> {
    /// Creates a new subscription and sends confirmation email.
    /// 
    /// Steps:
    /// 1. Begin database transaction
    /// 2. Insert subscriber with 'pending_confirmation' status
    /// 3. Generate unique confirmation token (UUID v4)
    /// 4. Insert token into subscription_tokens table
    /// 5. Commit transaction
    /// 6. Send confirmation email via SES (async, non-blocking)
    /// 
    /// AWS Services Used:
    ///   - Aurora PostgreSQL: Store subscriber and token
    ///   - SES: Send confirmation email
    /// 
    /// Error Handling:
    ///   - Duplicate email: Return SubscriptionError::AlreadyExists
    ///   - Database error: Rollback transaction, return SubscriptionError::DatabaseError
    ///   - Email send failure: Log error but return success (user can retry confirmation)
}
```

**AWS Integration Pattern**:
- **Aurora**: SQLx transaction for atomicity (subscriber + token insert)
- **SES**: Fire-and-forget email send (failures logged, not blocking)

#### 1.2 Confirm Subscription
```rust
pub async fn confirm_subscription(
    pool: &PgPool,
    token: &str,
) -> Result<(), SubscriptionError> {
    /// Confirms a subscription using the confirmation token.
    /// 
    /// Steps:
    /// 1. Begin database transaction
    /// 2. Fetch subscriber_id from subscription_tokens table
    /// 3. Update subscription status to 'confirmed'
    /// 4. Delete token from subscription_tokens table
    /// 5. Commit transaction
    /// 
    /// AWS Services Used:
    ///   - Aurora PostgreSQL: Update subscription status
    /// 
    /// Error Handling:
    ///   - Token not found: Return SubscriptionError::InvalidToken
    ///   - Database error: Rollback transaction, return SubscriptionError::DatabaseError
}
```

**AWS Integration Pattern**:
- **Aurora**: SQLx transaction for atomicity (status update + token delete)

---

### 2. Newsletter Service

**Purpose**: Handle newsletter publishing and delivery orchestration.

**Operations**:

#### 2.1 Publish Newsletter
```rust
pub async fn publish_newsletter(
    pool: &PgPool,
    sqs_client: &aws_sdk_sqs::Client,
    queue_url: &str,
    user_id: UserId,
    idempotency_key: &str,
    title: &str,
    text_content: &str,
    html_content: &str,
) -> Result<Uuid, PublishError> {
    /// Publishes a newsletter by storing issue and enqueuing delivery tasks.
    /// 
    /// Steps:
    /// 1. Check idempotency key in database (return cached newsletter_issue_id if exists)
    /// 2. Begin database transaction
    /// 3. Insert newsletter issue into newsletter_issues table
    /// 4. Fetch all confirmed subscribers
    /// 5. Commit transaction (newsletter stored, subscribers fetched)
    /// 6. Enqueue delivery tasks to SQS (batch send, 10 messages per API call)
    /// 7. Save idempotent response in database
    /// 8. Return newsletter_issue_id
    /// 
    /// AWS Services Used:
    ///   - Aurora PostgreSQL: Store newsletter issue, fetch subscribers
    ///   - SQS: Enqueue delivery tasks (one message per subscriber)
    /// 
    /// Error Handling:
    ///   - Idempotency violation: Return cached newsletter_issue_id (200 OK)
    ///   - Database error: Rollback transaction, return PublishError::DatabaseError
    ///   - SQS send error: Log error, return PublishError::QueueError
    ///   - Partial SQS batch failure: Retry failed messages
}
```

**AWS Integration Pattern**:
- **Aurora**: SQLx transaction for newsletter storage
- **SQS**: Batch send messages (10 per API call) with retry on partial failure

**SQS Message Format**:
```json
{
  "newsletter_issue_id": "550e8400-e29b-41d4-a716-446655440000",
  "subscriber_email": "user@example.com"
}
```

#### 2.2 Process Delivery Task (Lambda Function)
```rust
pub async fn process_delivery_task(
    pool: &PgPool,
    ses_client: &aws_sdk_sesv2::Client,
    sender_email: &str,
    newsletter_issue_id: Uuid,
    subscriber_email: &str,
) -> Result<(), DeliveryError> {
    /// Processes a single newsletter delivery task (called by Lambda for each SQS message).
    /// 
    /// Steps:
    /// 1. Fetch newsletter content from Aurora (title, text_content, html_content)
    /// 2. Send email via SES
    /// 3. Return success (SQS deletes message) or error (SQS retries)
    /// 
    /// AWS Services Used:
    ///   - Aurora PostgreSQL: Fetch newsletter content
    ///   - SES: Send newsletter email
    /// 
    /// Error Handling:
    ///   - Newsletter not found: Return DeliveryError::NewsletterNotFound (moves to DLQ after 3 retries)
    ///   - SES throttling: Return DeliveryError::Throttled (SQS retries with exponential backoff)
    ///   - SES bounce: Return DeliveryError::BounceError (moves to DLQ after 3 retries)
    ///   - Database error: Return DeliveryError::DatabaseError (SQS retries)
}
```

**AWS Integration Pattern**:
- **Aurora**: Read-only query for newsletter content
- **SES**: Send email with retry on throttling
- **SQS**: Automatic retry (3 attempts) with exponential backoff, then move to DLQ

---

### 3. Authentication Service

**Purpose**: Handle admin user authentication via Cognito.

**Operations**:

#### 3.1 Authenticate User
```rust
pub async fn authenticate_user(
    cognito_client: &aws_sdk_cognitoidentityprovider::Client,
    user_pool_client_id: &str,
    username: &str,
    password: &secrecy::Secret<String>,
) -> Result<AuthenticationResponse, AuthenticationError> {
    /// Authenticates a user via Cognito USER_PASSWORD_AUTH flow.
    /// 
    /// Steps:
    /// 1. Call Cognito InitiateAuth API with:
    ///    - AuthFlow: USER_PASSWORD_AUTH
    ///    - ClientId: User Pool Client ID
    ///    - AuthParameters: USERNAME, PASSWORD
    /// 2. Extract tokens from response:
    ///    - AccessToken: Short-lived token for API requests (1 hour)
    ///    - IdToken: Contains user attributes (1 hour)
    ///    - RefreshToken: Long-lived token for token refresh (30 days)
    /// 3. Decode IdToken to extract user_id (sub claim)
    /// 4. Return tokens and user_id
    /// 
    /// AWS Services Used:
    ///   - Cognito User Pools: Authenticate user
    /// 
    /// Error Handling:
    ///   - Invalid credentials: Return AuthenticationError::InvalidCredentials
    ///   - User not found: Return AuthenticationError::UserNotFound
    ///   - Account locked: Return AuthenticationError::AccountLocked
    ///   - Password expired: Return AuthenticationError::PasswordExpired
    ///   - Cognito API error: Return AuthenticationError::ServiceError
}

pub struct AuthenticationResponse {
    pub access_token: String,
    pub id_token: String,
    pub refresh_token: String,
    pub user_id: Uuid,
}
```

**AWS Integration Pattern**:
- **Cognito**: Call InitiateAuth API with USER_PASSWORD_AUTH flow
- **JWT Decoding**: Parse IdToken to extract user_id (sub claim)

#### 3.2 Validate Token
```rust
pub fn validate_token(
    cognito_validator: &CognitoValidator,
    access_token: &str,
) -> Result<Claims, ValidationError> {
    /// Validates a Cognito JWT access token.
    /// 
    /// Steps:
    /// 1. Decode JWT header (extract kid - key ID)
    /// 2. Find matching public key in JWKS
    /// 3. Verify JWT signature using RS256 algorithm
    /// 4. Validate token expiration (exp claim)
    /// 5. Validate issuer (iss claim matches Cognito User Pool)
    /// 6. Validate audience (aud claim matches client_id)
    /// 7. Extract claims (sub, username, exp, iat)
    /// 
    /// AWS Services Used:
    ///   - None (local validation using JWKS fetched at startup)
    /// 
    /// Error Handling:
    ///   - Invalid signature: Return ValidationError::InvalidSignature
    ///   - Expired token: Return ValidationError::TokenExpired
    ///   - Invalid issuer: Return ValidationError::InvalidIssuer
    ///   - Invalid audience: Return ValidationError::InvalidAudience
}
```

**AWS Integration Pattern**:
- **Cognito**: JWKS fetched at startup and cached in memory
- **JWT Validation**: Local validation (no API call) using cached JWKS

#### 3.3 Refresh Token
```rust
pub async fn refresh_token(
    cognito_client: &aws_sdk_cognitoidentityprovider::Client,
    user_pool_client_id: &str,
    refresh_token: &str,
) -> Result<AuthenticationResponse, AuthenticationError> {
    /// Refreshes access and ID tokens using refresh token.
    /// 
    /// Steps:
    /// 1. Call Cognito InitiateAuth API with:
    ///    - AuthFlow: REFRESH_TOKEN_AUTH
    ///    - ClientId: User Pool Client ID
    ///    - AuthParameters: REFRESH_TOKEN
    /// 2. Extract new access and ID tokens
    /// 3. Return new tokens (refresh token unchanged)
    /// 
    /// AWS Services Used:
    ///   - Cognito User Pools: Refresh tokens
    /// 
    /// Error Handling:
    ///   - Invalid refresh token: Return AuthenticationError::InvalidRefreshToken
    ///   - Cognito API error: Return AuthenticationError::ServiceError
}
```

**AWS Integration Pattern**:
- **Cognito**: Call InitiateAuth API with REFRESH_TOKEN_AUTH flow

---

### 4. Email Service

**Purpose**: Abstract SES email sending with retry logic and error handling.

**Operations**:

#### 4.1 Send Email
```rust
pub async fn send_email(
    ses_client: &aws_sdk_sesv2::Client,
    sender: &SubscriberEmail,
    recipient: &SubscriberEmail,
    subject: &str,
    html_content: &str,
    text_content: &str,
) -> Result<(), EmailError> {
    /// Sends an email via Amazon SES.
    /// 
    /// Steps:
    /// 1. Build SES SendEmail request:
    ///    - FromEmailAddress: sender email
    ///    - Destination: recipient email
    ///    - Content: Subject + Body (HTML + Text)
    /// 2. Call SES SendEmail API
    /// 3. Handle errors (throttling, bounces, etc.)
    /// 
    /// AWS Services Used:
    ///   - SES: Send email
    /// 
    /// Error Handling:
    ///   - Throttling: Retry with exponential backoff (3 attempts)
    ///   - Bounce: Return EmailError::BounceError
    ///   - Invalid recipient: Return EmailError::InvalidRecipient
    ///   - SES API error: Return EmailError::ServiceError
}
```

**AWS Integration Pattern**:
- **SES**: Call SendEmail API v2 with retry on throttling
- **IAM**: Uses ECS task role or Lambda execution role for authentication

**Retry Strategy**:
- Throttling errors: Exponential backoff (1s, 2s, 4s)
- Transient errors: Retry 3 times
- Permanent errors (bounce, invalid recipient): No retry, return error

---

## AWS Service Integration Patterns

### 1. ECS Fargate ↔ Aurora PostgreSQL

**Integration Type**: Database connection with connection pooling

**Connection Details**:
- **Endpoint**: Aurora cluster writer endpoint (from Database Stack)
- **Port**: 5432
- **TLS**: Required (enforced by parameter group `rds.force_ssl = 1`)
- **Authentication**: Username/password from Secrets Manager
- **Connection Pool**: SQLx with min=5, max=20, idle_timeout=600s

**Implementation**:
```rust
// Configuration loaded at startup
let database_url = format!(
    "postgres://{}:{}@{}:{}/{}?sslmode=require",
    config.database.username,
    config.database.password.expose_secret(),
    config.database.host,
    config.database.port,
    config.database.database_name
);

let pool = PgPoolOptions::new()
    .min_connections(5)
    .max_connections(20)
    .idle_timeout(Duration::from_secs(600))
    .connect(&database_url)
    .await?;
```

**Security**:
- ECS security group allows outbound to Aurora security group on port 5432
- Aurora security group allows inbound from ECS security group on port 5432
- TLS 1.2+ enforced for all connections
- Credentials retrieved from Secrets Manager at startup

**Error Handling**:
- Connection timeout: Return `DatabaseError::ConnectionTimeout`
- Query timeout: Return `DatabaseError::QueryTimeout`
- Transaction conflict: Retry with exponential backoff (3 attempts)

---

### 2. ECS Fargate ↔ ElastiCache Serverless

**Integration Type**: In-memory cache for session storage

**Connection Details**:
- **Endpoint**: ElastiCache cluster endpoint (from Cache Stack)
- **Port**: 6379
- **TLS**: Required (`rediss://` protocol)
- **Authentication**: None (security group-based access control)

**Implementation**:
```rust
// Configuration loaded at startup
let redis_uri = config.redis_uri; // e.g., "rediss://<endpoint>:6379"

let redis_client = redis::Client::open(redis_uri)?;
let redis_store = RedisActorSessionStore::new(redis_client);

// Session middleware configuration
SessionMiddleware::builder(redis_store, Key::from(hmac_secret.expose_secret().as_bytes()))
    .cookie_name("sessionid")
    .cookie_http_only(true)
    .cookie_secure(true)
    .cookie_same_site(actix_web::cookie::SameSite::Strict)
    .session_lifecycle(PersistentSession::default().session_ttl(Duration::from_secs(3600)))
    .build()
```

**Security**:
- ECS security group allows outbound to ElastiCache security group on port 6379
- ElastiCache security group allows inbound from ECS security group on port 6379
- TLS in-transit encryption enabled
- Session data encrypted with HMAC secret (cookie signing)

**Error Handling**:
- Connection timeout: Log error, fall back to in-memory sessions (graceful degradation)
- Redis unavailable: Log error, return HTTP 503 Service Unavailable

---

### 3. ECS Fargate → SQS

**Integration Type**: Message queue for asynchronous task processing

**Connection Details**:
- **Queue URL**: From Worker Stack output
- **Authentication**: IAM role (ECS task role)
- **VPC Endpoint**: SQS VPC endpoint for private connectivity

**Implementation**:
```rust
// SQS client initialized at startup
let aws_config = aws_config::load_from_env().await;
let sqs_client = aws_sdk_sqs::Client::new(&aws_config);

// Batch send messages (10 per API call)
async fn enqueue_delivery_tasks(
    sqs_client: &aws_sdk_sqs::Client,
    queue_url: &str,
    newsletter_issue_id: Uuid,
    subscribers: Vec<SubscriberEmail>,
) -> Result<(), anyhow::Error> {
    let messages: Vec<_> = subscribers
        .into_iter()
        .enumerate()
        .map(|(idx, email)| {
            let body = serde_json::json!({
                "newsletter_issue_id": newsletter_issue_id,
                "subscriber_email": email.as_ref()
            });
            SendMessageBatchRequestEntry::builder()
                .id(idx.to_string())
                .message_body(body.to_string())
                .build()
        })
        .collect();
    
    // Send in batches of 10 (SQS limit)
    for chunk in messages.chunks(10) {
        sqs_client
            .send_message_batch()
            .queue_url(queue_url)
            .set_entries(Some(chunk.to_vec()))
            .send()
            .await?;
    }
    
    Ok(())
}
```

**Security**:
- ECS task IAM role granted `sqs:SendMessage` on newsletter queue
- SQS messages encrypted at rest (SQS managed key)
- VPC endpoint for SQS (no internet egress)

**Error Handling**:
- Throttling: Retry with exponential backoff (3 attempts)
- Partial batch failure: Retry failed messages
- Queue unavailable: Return HTTP 500 Internal Server Error

---

### 4. Lambda → Aurora PostgreSQL

**Integration Type**: Read-only database access for newsletter content retrieval

**Connection Details**:
- **Endpoint**: Aurora cluster reader endpoint (for read scalability)
- **Port**: 5432
- **TLS**: Required
- **Authentication**: Username/password from Secrets Manager
- **VPC Configuration**: Lambda in private subnets with Aurora security group access

**Implementation**:
```rust
// Lambda handler initializes connection at startup (outside handler for connection reuse)
#[tokio::main]
async fn main() -> Result<(), Error> {
    let database_url = std::env::var("DATABASE_URL")?;
    
    let pool = PgPoolOptions::new()
        .max_connections(5) // Lower than ECS (Lambda has concurrency limit)
        .connect(&database_url)
        .await?;
    
    lambda_runtime::run(service_fn(move |event: LambdaEvent<SqsEvent>| {
        handler(event, pool.clone())
    })).await
}

async fn handler(event: LambdaEvent<SqsEvent>, pool: PgPool) -> Result<(), Error> {
    for record in event.payload.records {
        let message: SqsMessage = serde_json::from_str(&record.body)?;
        
        // Fetch newsletter content
        let newsletter = sqlx::query_as!(
            NewsletterIssue,
            "SELECT title, text_content, html_content FROM newsletter_issues WHERE newsletter_issue_id = $1",
            message.newsletter_issue_id
        )
        .fetch_one(&pool)
        .await?;
        
        // Send email via SES
        send_newsletter_email(&ses_client, &sender_email, &message.subscriber_email, &newsletter).await?;
    }
    
    Ok(())
}
```

**Security**:
- Lambda security group allows outbound to Aurora security group on port 5432
- Aurora security group allows inbound from Lambda security group on port 5432
- Lambda execution role granted `ec2:CreateNetworkInterface` for VPC access
- TLS 1.2+ enforced for all connections

**Error Handling**:
- Newsletter not found: Return error (moves to DLQ after 3 retries)
- Database error: Return error (SQS retries with exponential backoff)

---

### 5. Lambda → SES

**Integration Type**: Email sending via SES API

**Connection Details**:
- **Authentication**: IAM role (Lambda execution role)
- **VPC Endpoint**: SES VPC endpoint for private connectivity

**Implementation**:
```rust
// SES client initialized at startup
let aws_config = aws_config::load_from_env().await;
let ses_client = aws_sdk_sesv2::Client::new(&aws_config);

async fn send_newsletter_email(
    ses_client: &aws_sdk_sesv2::Client,
    sender_email: &str,
    recipient_email: &str,
    newsletter: &NewsletterIssue,
) -> Result<(), anyhow::Error> {
    ses_client
        .send_email()
        .from_email_address(sender_email)
        .destination(
            Destination::builder()
                .to_addresses(recipient_email)
                .build()
        )
        .content(
            EmailContent::builder()
                .simple(
                    Message::builder()
                        .subject(Content::builder().data(&newsletter.title).build())
                        .body(
                            Body::builder()
                                .html(Content::builder().data(&newsletter.html_content).build())
                                .text(Content::builder().data(&newsletter.text_content).build())
                                .build()
                        )
                        .build()
                )
                .build()
        )
        .send()
        .await?;
    
    Ok(())
}
```

**Security**:
- Lambda execution role granted `ses:SendEmail` on verified sender identity
- VPC endpoint for SES (no internet egress)

**Error Handling**:
- Throttling: Return error (SQS retries with exponential backoff)
- Bounce: Return error (moves to DLQ after 3 retries)
- Invalid recipient: Return error (moves to DLQ after 3 retries)

---

### 6. ECS Fargate ↔ Cognito User Pools

**Integration Type**: Authentication via Cognito API and JWT validation

**Connection Details**:
- **Authentication**: IAM role (ECS task role) for Cognito API calls
- **JWKS Endpoint**: `https://cognito-idp.<region>.amazonaws.com/<user-pool-id>/.well-known/jwks.json`
- **VPC Endpoint**: Cognito VPC endpoint (optional, for private connectivity)

**Implementation**:
```rust
// Cognito client initialized at startup
let aws_config = aws_config::load_from_env().await;
let cognito_client = aws_sdk_cognitoidentityprovider::Client::new(&aws_config);

// JWKS fetched at startup and cached
let cognito_validator = CognitoValidator::new(
    config.cognito.user_pool_id,
    config.cognito.client_id,
    config.cognito.region,
).await?;

// Login endpoint
async fn login(
    form: web::Form<FormData>,
    cognito_client: web::Data<aws_sdk_cognitoidentityprovider::Client>,
    user_pool_client_id: web::Data<String>,
    session: Session,
) -> Result<HttpResponse, actix_web::Error> {
    let auth_response = cognito_client
        .initiate_auth()
        .auth_flow(AuthFlowType::UserPasswordAuth)
        .client_id(user_pool_client_id.as_ref())
        .auth_parameters("USERNAME", &form.username)
        .auth_parameters("PASSWORD", form.password.expose_secret())
        .send()
        .await?;
    
    let tokens = auth_response.authentication_result().unwrap();
    
    session.insert("access_token", tokens.access_token().unwrap())?;
    session.insert("refresh_token", tokens.refresh_token().unwrap())?;
    
    Ok(HttpResponse::SeeOther()
        .insert_header((header::LOCATION, "/admin/dashboard"))
        .finish())
}

// Middleware for protected routes
async fn reject_anonymous_users(
    req: ServiceRequest,
    credentials: Option<TypedHeader<headers::Authorization<headers::authorization::Bearer>>>,
) -> Result<ServiceRequest, (Error, ServiceRequest)> {
    let token = credentials
        .ok_or_else(|| (ErrorUnauthorized("Missing authorization header"), req))?
        .token();
    
    let validator = req.app_data::<web::Data<CognitoValidator>>()
        .ok_or_else(|| (ErrorInternalServerError("Cognito validator not found"), req))?;
    
    let claims = validator.validate_token(token)
        .map_err(|e| (ErrorUnauthorized(e), req))?;
    
    req.extensions_mut().insert(UserId(Uuid::parse_str(&claims.sub)?));
    
    Ok(req)
}
```

**Security**:
- Cognito User Pool enforces password complexity rules
- Account lockout after 5 failed login attempts
- JWT tokens signed with RS256 (asymmetric keys)
- JWKS cached in memory and refreshed every 1 hour

**Error Handling**:
- Invalid credentials: Return HTTP 401 Unauthorized
- Account locked: Return HTTP 403 Forbidden
- Token expired: Return HTTP 401 Unauthorized (client should refresh token)

---

## Cross-Cutting Concerns

### 1. Logging and Tracing

**Framework**: `tracing` with `tracing-subscriber` (structured logging)

**Log Levels**:
- **ERROR**: Critical failures requiring immediate attention
- **WARN**: Degraded functionality or recoverable errors
- **INFO**: Important operational events (user actions, API calls)
- **DEBUG**: Detailed diagnostic information
- **TRACE**: Very detailed diagnostic information (disabled in production)

**Structured Logging Format** (Bunyan JSON):
```json
{
  "timestamp": "2026-06-11T10:30:00.123Z",
  "level": "INFO",
  "msg": "Newsletter published",
  "newsletter_issue_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "subscriber_count": 1234,
  "duration_ms": 152
}
```

**CloudWatch Logs Integration**:
- ECS tasks write logs to `/ecs/zero2prod-web` log group
- Lambda functions write logs to `/aws/lambda/zero2prod-newsletter-sender` log group
- Log retention: 30 days for application logs, 90 days for access logs

**X-Ray Tracing**:
- **Trace ID**: Propagated across ECS → Aurora, ECS → SQS, Lambda → Aurora, Lambda → SES
- **Sampling Rate**: 5% of requests (configurable)
- **Service Map**: Visualizes dependencies (ECS ↔ Aurora, ECS ↔ SQS, Lambda ↔ SES)

**Implementation**:
```rust
use tracing::{info, error, instrument};

#[instrument(skip(pool, sqs_client), fields(newsletter_issue_id, subscriber_count))]
pub async fn publish_newsletter(
    pool: &PgPool,
    sqs_client: &aws_sdk_sqs::Client,
    queue_url: &str,
    user_id: UserId,
    newsletter: NewsletterData,
) -> Result<Uuid, PublishError> {
    let newsletter_issue_id = Uuid::new_v4();
    
    // Database transaction
    let mut tx = pool.begin().await?;
    sqlx::query!(/* ... */).execute(&mut tx).await?;
    let subscribers = sqlx::query_as!(/* ... */).fetch_all(&mut tx).await?;
    tx.commit().await?;
    
    let subscriber_count = subscribers.len();
    tracing::Span::current().record("newsletter_issue_id", &newsletter_issue_id.to_string());
    tracing::Span::current().record("subscriber_count", subscriber_count);
    
    // Enqueue delivery tasks
    enqueue_delivery_tasks(sqs_client, queue_url, newsletter_issue_id, subscribers).await?;
    
    info!("Newsletter published successfully");
    Ok(newsletter_issue_id)
}
```

---

### 2. Secrets Management

**Service**: AWS Secrets Manager

**Secrets Stored**:
1. Database credentials: `zero2prod/database/credentials`
   - Format: `{"username": "postgres", "password": "<generated>", "host": "<endpoint>", "port": 5432, "dbname": "newsletter"}`
2. Redis connection string: `zero2prod/elasticache/connection-string`
   - Format: `rediss://<endpoint>:6379`
3. HMAC secret: `zero2prod/application/hmac-secret`
   - Format: `<base64-encoded-secret>`

**Retrieval Pattern**:
- Secrets retrieved at application startup
- Cached in memory (no repeated API calls)
- Optional: Refresh secrets every 5 minutes (for rotation support)

**Implementation**:
```rust
async fn get_database_settings(
    secrets_client: &aws_sdk_secretsmanager::Client,
) -> Result<DatabaseSettings, ConfigError> {
    let secret = secrets_client
        .get_secret_value()
        .secret_id("zero2prod/database/credentials")
        .send()
        .await?;
    
    let secret_string = secret.secret_string()
        .ok_or_else(|| ConfigError::MissingSecret)?;
    
    let db_config: DatabaseConfig = serde_json::from_str(secret_string)?;
    
    Ok(DatabaseSettings {
        username: db_config.username,
        password: secrecy::Secret::new(db_config.password),
        host: db_config.host,
        port: db_config.port,
        database_name: db_config.dbname,
        require_ssl: true,
    })
}
```

**Rotation Strategy**:
- Database password rotated every 30 days (automated by Secrets Manager)
- Application handles rotation by refreshing secrets on connection failure

---

### 3. Error Handling

**Error Types**:

```rust
#[derive(Debug, thiserror::Error)]
pub enum SubscriptionError {
    #[error("Email already exists")]
    AlreadyExists,
    
    #[error("Invalid email format")]
    InvalidEmail,
    
    #[error("Database error: {0}")]
    DatabaseError(#[from] sqlx::Error),
    
    #[error("Email send error: {0}")]
    EmailError(#[from] EmailError),
}

#[derive(Debug, thiserror::Error)]
pub enum PublishError {
    #[error("Invalid newsletter content")]
    InvalidContent,
    
    #[error("Database error: {0}")]
    DatabaseError(#[from] sqlx::Error),
    
    #[error("Queue error: {0}")]
    QueueError(String),
}

#[derive(Debug, thiserror::Error)]
pub enum AuthenticationError {
    #[error("Invalid credentials")]
    InvalidCredentials,
    
    #[error("User not found")]
    UserNotFound,
    
    #[error("Account locked")]
    AccountLocked,
    
    #[error("Cognito service error: {0}")]
    ServiceError(String),
}
```

**Error Context**:
- Use `anyhow::Context` to add context to errors
- Log errors with structured fields (user_id, newsletter_issue_id, etc.)
- Return user-friendly error messages (no internal details exposed)

**Error Responses** (HTTP):
- 400 Bad Request: Invalid input (validation errors)
- 401 Unauthorized: Missing or invalid authentication
- 403 Forbidden: Authenticated but insufficient permissions
- 404 Not Found: Resource not found
- 409 Conflict: Duplicate resource (e.g., email already exists)
- 500 Internal Server Error: Unexpected errors
- 503 Service Unavailable: Dependency unavailable (Aurora, Redis, SQS, SES)

---

### 4. Idempotency

**Purpose**: Prevent duplicate newsletter submissions using client-supplied idempotency keys.

**Implementation**:
```rust
async fn try_processing(
    pool: &PgPool,
    user_id: &UserId,
    idempotency_key: &str,
) -> Result<Option<HttpResponse>, anyhow::Error> {
    /// Checks if request with same idempotency key was already processed.
    /// 
    /// Returns:
    ///   Ok(Some(cached_response)) if request was already processed
    ///   Ok(None) if request is new
    let saved_response = sqlx::query!(
        "SELECT response_status_code, response_headers, response_body 
         FROM idempotency 
         WHERE user_id = $1 AND idempotency_key = $2",
        user_id.0,
        idempotency_key
    )
    .fetch_optional(pool)
    .await?;
    
    if let Some(response) = saved_response {
        // Return cached response
        Ok(Some(reconstruct_response(response)))
    } else {
        Ok(None)
    }
}

async fn save_response(
    pool: &PgPool,
    user_id: &UserId,
    idempotency_key: &str,
    http_response: &HttpResponse,
) -> Result<(), anyhow::Error> {
    /// Saves successful response for idempotency check.
    sqlx::query!(
        "INSERT INTO idempotency (user_id, idempotency_key, response_status_code, response_headers, response_body, created_at)
         VALUES ($1, $2, $3, $4, $5, NOW())",
        user_id.0,
        idempotency_key,
        http_response.status().as_u16() as i16,
        serde_json::to_value(http_response.headers())?,
        http_response.body()
    )
    .execute(pool)
    .await?;
    
    Ok(())
}
```

**Idempotency Table Schema**:
```sql
CREATE TABLE idempotency (
    user_id UUID NOT NULL,
    idempotency_key TEXT NOT NULL,
    response_status_code SMALLINT NOT NULL,
    response_headers JSONB NOT NULL,
    response_body BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, idempotency_key)
);
```

**Cleanup Strategy**:
- Idempotency records older than 24 hours can be deleted (admin discretion)
- Use Aurora's scheduled Lambda function for periodic cleanup (optional)

---

### 5. Performance Optimization

**Connection Pooling**:
- **Aurora**: SQLx connection pool (min=5, max=20, idle_timeout=600s)
- **Redis**: Single client with connection multiplexing

**Query Optimization**:
- Use prepared statements (SQLx compile-time checked queries)
- Index on `subscriptions.email` (unique constraint)
- Index on `subscriptions.status` (for confirmed subscriber queries)
- Index on `subscription_tokens.subscription_token` (for confirmation lookup)

**Caching Strategy**:
- Session data cached in Redis (TTL: 1 hour)
- Cognito JWKS cached in memory (refresh every 1 hour)
- Secrets cached in memory (refresh on rotation)

**Batch Processing**:
- SQS batch send: 10 messages per API call
- Lambda batch processing: 10 messages per invocation

**Auto-Scaling**:
- ECS tasks scale based on CPU utilization (target: 70%)
- Lambda scales automatically up to reserved concurrency (100)
- Aurora ACUs scale based on database load (0.5-4 ACUs)

---

## Service Layer Summary

| Service | Purpose | AWS Services Used | Key Operations |
|---------|---------|-------------------|----------------|
| Subscription Service | Manage newsletter subscriptions | Aurora, SES | Create, Confirm, Unsubscribe |
| Newsletter Service | Publish newsletters | Aurora, SQS, Lambda, SES | Publish, Process Delivery |
| Authentication Service | Admin authentication | Cognito | Authenticate, Validate Token, Refresh Token |
| Email Service | Send emails | SES | Send Email |

**Cross-Cutting Concerns**:
- Logging and Tracing (CloudWatch, X-Ray)
- Secrets Management (Secrets Manager)
- Error Handling (structured errors with context)
- Idempotency (prevent duplicate submissions)
- Performance Optimization (connection pooling, caching, batching)

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-11  
**Status**: Ready for Review
