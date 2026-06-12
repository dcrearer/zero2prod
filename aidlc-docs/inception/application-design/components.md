# Component Design

## Component Overview

This document defines all components in the AWS modernized architecture, clearly distinguishing between infrastructure components (managed by AWS CDK) and application components (Rust code).

---

## Infrastructure Components

These components are defined and deployed using AWS CDK Python stacks. Each component maps to a CDK stack or set of CDK constructs.

### 1. Network Infrastructure Component

**Responsibility**: Provide secure, isolated networking for all application components with private subnet architecture and VPC endpoints.

**AWS Services Used**:
- Amazon VPC
- VPC Subnets (Public and Private)
- VPC Endpoints (Gateway and Interface)
- Security Groups
- Network ACLs (optional)

**Component Details**:

**VPC Configuration**:
- CIDR Block: 10.0.0.0/16 (65,536 addresses)
- Multi-AZ deployment: 2 Availability Zones minimum
- Public Subnets: 2 subnets (10.0.1.0/24, 10.0.2.0/24) - ALB only
- Private Subnets: 2 subnets (10.0.10.0/24, 10.0.11.0/24) - ECS, Lambda, Aurora, ElastiCache
- DNS Hostnames: Enabled
- DNS Resolution: Enabled

**VPC Endpoints** (No NAT Gateway - highest security):
- `com.amazonaws.region.s3` (Gateway endpoint) - ECR image pulls
- `com.amazonaws.region.ecr.api` (Interface endpoint) - ECR API
- `com.amazonaws.region.ecr.dkr` (Interface endpoint) - Docker registry
- `com.amazonaws.region.logs` (Interface endpoint) - CloudWatch Logs
- `com.amazonaws.region.secretsmanager` (Interface endpoint) - Secrets Manager
- `com.amazonaws.region.sts` (Interface endpoint) - STS token service
- `com.amazonaws.region.ses` (Interface endpoint) - SES email sending
- `com.amazonaws.region.sqs` (Interface endpoint) - SQS messaging

**Security Groups**:
- ALB Security Group: Inbound 443 (HTTPS) from 0.0.0.0/0, outbound to ECS tasks
- ECS Security Group: Inbound from ALB, outbound to Aurora, ElastiCache, VPC endpoints
- Aurora Security Group: Inbound 5432 from ECS and Lambda only
- ElastiCache Security Group: Inbound 6379 from ECS only
- Lambda Security Group: Outbound to Aurora, VPC endpoints
- VPC Endpoint Security Group: Inbound 443 from ECS and Lambda

**Outputs**:
- VPC ID
- Public Subnet IDs
- Private Subnet IDs
- Security Group IDs
- VPC Endpoint IDs

**Requirements Mapping**: NFR-3 (Network Isolation), SECURITY-01 (Encryption), SECURITY-04 (Private Networking)

---

### 2. Database Infrastructure Component

**Responsibility**: Provide highly available, scalable PostgreSQL database with automatic backups, encryption, and Multi-AZ deployment.

**AWS Services Used**:
- Amazon Aurora PostgreSQL Serverless v2
- AWS Secrets Manager
- Amazon CloudWatch (for database metrics)

**Component Details**:

**Aurora Cluster Configuration**:
- Engine: Aurora PostgreSQL (compatible with PostgreSQL 15+)
- Deployment: Serverless v2 with Multi-AZ
- Min ACUs: 0.5 (512 MB RAM)
- Max ACUs: 4 (4 GB RAM)
- Scaling Increment: 0.5 ACU
- Database Name: `newsletter`
- Master Username: `postgres`
- Master Password: Stored in Secrets Manager

**Encryption**:
- Encryption at Rest: Enabled (AWS KMS default key)
- Encryption in Transit: TLS 1.2+ enforced via parameter group

**Backup Configuration**:
- Automated Backups: Enabled
- Backup Retention: 7 days
- Backup Window: 03:00-04:00 UTC
- Snapshot on Delete: Enabled

**Parameter Group**:
- `rds.force_ssl`: 1 (enforce TLS connections)
- `log_connections`: 1 (audit logging)
- `log_disconnections`: 1 (audit logging)
- `log_min_duration_statement`: 1000 (log queries > 1 second)

**Database Schema** (6 tables):
1. `subscriptions`: id, email, name, subscribed_at, status
2. `subscription_tokens`: subscription_token, subscriber_id
3. `users`: user_id, username, password_hash (deprecated for auth, kept for audit)
4. `newsletter_issues`: newsletter_issue_id, title, text_content, html_content, published_at
5. `idempotency`: user_id, idempotency_key, response_status_code, response_headers, response_body, created_at
6. (Table removed): `issue_delivery_queue` - replaced by SQS

**Secrets Manager Integration**:
- Secret Name: `zero2prod/database/credentials`
- Secret Format: JSON `{"username": "postgres", "password": "<generated>", "host": "<cluster-endpoint>", "port": 5432, "dbname": "newsletter"}`
- Rotation: Enabled (30 days)

**Outputs**:
- Cluster Endpoint (Writer)
- Reader Endpoint
- Port (5432)
- Secret ARN

**Requirements Mapping**: FR-3 (Database Migration), NFR-1 (Multi-AZ HA), NFR-5 (Encryption), SECURITY-01 (Encryption at rest/transit)

---

### 3. Cache Infrastructure Component

**Responsibility**: Provide fast, scalable in-memory cache for HTTP session storage with automatic scaling and Multi-AZ replication.

**AWS Services Used**:
- Amazon ElastiCache Serverless for Redis
- AWS Secrets Manager

**Component Details**:

**ElastiCache Serverless Configuration**:
- Cache Engine: Redis 7.x compatible
- Deployment: Serverless (auto-scaling)
- Multi-AZ: Enabled (automatic replication)
- Snapshot Retention: 7 days
- Snapshot Window: 03:00-04:00 UTC

**Encryption**:
- Encryption at Rest: Enabled
- Encryption in Transit: TLS 1.2+ enabled

**Secrets Manager Integration**:
- Secret Name: `zero2prod/elasticache/connection-string`
- Secret Format: `rediss://<endpoint>:6379` (rediss = TLS-enabled Redis)

**Outputs**:
- Cache Endpoint
- Port (6379)
- Secret ARN

**Requirements Mapping**: FR-4 (Session Store Migration), NFR-1 (Multi-AZ HA), NFR-5 (Encryption), SECURITY-01 (Encryption)

---

### 4. Compute Infrastructure Component

**Responsibility**: Deploy and manage web application containers on ECS Fargate with load balancing, auto-scaling, and health monitoring.

**AWS Services Used**:
- Amazon ECS (Fargate)
- Application Load Balancer (ALB)
- Amazon ECR (Elastic Container Registry)
- AWS IAM (Task and Execution Roles)
- Amazon CloudWatch Logs
- AWS Certificate Manager (ACM)

**Component Details**:

**ECS Cluster**:
- Name: `zero2prod-cluster`
- Capacity Provider: Fargate
- Container Insights: Enabled

**Task Definition**:
- Family: `zero2prod-web`
- Requires Compatibilities: Fargate
- Network Mode: awsvpc
- CPU: 512 (0.5 vCPU)
- Memory: 1024 MB (1 GB)
- Container Image: `<ecr-repo>:latest`
- Port Mapping: 8000 (container) → 8000 (host)

**Container Environment Variables**:
- `APP_APPLICATION__BASE_URL`: ALB DNS name
- `APP_APPLICATION__HMAC_SECRET`: From Secrets Manager
- `DATABASE_URL`: From Secrets Manager (PostgreSQL connection string)
- `REDIS_URI`: From Secrets Manager (ElastiCache connection string)
- `AWS_REGION`: us-east-1 (or target region)

**IAM Task Role** (Application permissions):
- `secretsmanager:GetSecretValue` on database and Redis secrets
- `ses:SendEmail` on verified sender identity
- `sqs:SendMessage` on newsletter delivery queue
- `xray:PutTraceSegments` for X-Ray tracing

**IAM Execution Role** (ECS agent permissions):
- `ecr:GetAuthorizationToken`
- `ecr:BatchCheckLayerAvailability`
- `ecr:GetDownloadUrlForLayer`
- `ecr:BatchGetImage`
- `logs:CreateLogStream`
- `logs:PutLogEvents`
- `secretsmanager:GetSecretValue` (for ECS to inject secrets)

**ECS Service**:
- Service Name: `zero2prod-web-service`
- Desired Count: 2 (for HA)
- Max Count: 10 (auto-scaling limit)
- Launch Type: Fargate
- Platform Version: LATEST
- Health Check Grace Period: 60 seconds
- Deployment Circuit Breaker: Enabled (rollback on failure)

**Auto-Scaling Policy**:
- Metric: CPU Utilization
- Target Value: 70%
- Scale-out Cooldown: 60 seconds
- Scale-in Cooldown: 300 seconds
- Min Capacity: 2
- Max Capacity: 10

**Application Load Balancer**:
- Scheme: Internet-facing
- Subnets: Public subnets (multi-AZ)
- Security Group: ALB security group
- IP Address Type: IPv4
- Deletion Protection: Enabled

**ALB Target Group**:
- Target Type: IP (for awsvpc mode)
- Protocol: HTTP
- Port: 8000
- Health Check Path: `/health_check`
- Health Check Interval: 30 seconds
- Health Check Timeout: 5 seconds
- Healthy Threshold: 2
- Unhealthy Threshold: 3
- Deregistration Delay: 30 seconds

**ALB Listener**:
- Protocol: HTTPS
- Port: 443
- SSL Certificate: ACM certificate
- Default Action: Forward to target group

**ALB HTTP Redirect**:
- Protocol: HTTP
- Port: 80
- Action: Redirect to HTTPS (301)

**Access Logging**:
- Enabled: Yes
- S3 Bucket: `zero2prod-alb-logs-<account-id>`
- Prefix: `alb/`

**ECR Repository**:
- Repository Name: `zero2prod`
- Image Scanning: Enabled (on push)
- Lifecycle Policy: Keep last 10 images

**CloudWatch Log Group**:
- Name: `/ecs/zero2prod-web`
- Retention: 30 days

**Outputs**:
- ALB DNS Name
- ALB ARN
- ECS Cluster Name
- ECS Service Name
- ECR Repository URI
- Task Role ARN
- Execution Role ARN

**Requirements Mapping**: FR-1 (Web Deployment), NFR-1 (Multi-AZ HA), NFR-9 (API Latency), NFR-11 (Auto-Scaling), NFR-6 (Access Logging), SECURITY-02 (Access Logging)

---

### 5. Worker Infrastructure Component

**Responsibility**: Provide event-driven email delivery using SQS queue and Lambda function, replacing the polling-based background worker.

**AWS Services Used**:
- Amazon SQS (Standard Queue)
- AWS Lambda
- Amazon SES
- AWS IAM (Lambda Execution Role)
- Amazon CloudWatch Logs

**Component Details**:

**SQS Queue Configuration**:
- Queue Name: `zero2prod-newsletter-delivery`
- Queue Type: Standard (unlimited throughput)
- Visibility Timeout: 300 seconds (5 minutes - Lambda execution time + buffer)
- Message Retention: 14 days
- Receive Message Wait Time: 0 (no long polling needed with Lambda trigger)
- Maximum Message Size: 256 KB
- Encryption: Server-side encryption enabled (SQS managed key)

**SQS Dead Letter Queue**:
- Queue Name: `zero2prod-newsletter-delivery-dlq`
- Queue Type: Standard
- Message Retention: 14 days
- Redrive Policy: Max Receives = 3

**Message Format** (JSON):
```json
{
  "newsletter_issue_id": "uuid-v4",
  "subscriber_email": "user@example.com"
}
```

**Lambda Function Configuration**:
- Function Name: `zero2prod-newsletter-sender`
- Runtime: Custom (Rust Lambda runtime via AWS Lambda Runtime for Rust)
- Handler: `bootstrap` (Rust compiled binary)
- Memory: 512 MB
- Timeout: 60 seconds
- Reserved Concurrency: 100 (aligned with SES sending rate)
- Environment Variables:
  - `DATABASE_URL`: From Secrets Manager
  - `AWS_REGION`: us-east-1
  - `SENDER_EMAIL`: Verified SES sender identity

**Lambda Trigger**:
- Event Source: SQS queue
- Batch Size: 10 messages
- Max Batching Window: 5 seconds
- Failure Destination: SQS DLQ

**IAM Lambda Execution Role**:
- `logs:CreateLogStream`
- `logs:PutLogEvents`
- `sqs:ReceiveMessage`
- `sqs:DeleteMessage`
- `sqs:GetQueueAttributes`
- `ses:SendEmail` on verified sender identity
- `secretsmanager:GetSecretValue` on database secret
- `xray:PutTraceSegments` for X-Ray tracing
- `ec2:CreateNetworkInterface` (for VPC access)
- `ec2:DescribeNetworkInterfaces`
- `ec2:DeleteNetworkInterface`

**Lambda VPC Configuration**:
- VPC ID: From Network Stack
- Subnets: Private subnets
- Security Groups: Lambda security group

**SES Configuration**:
- Sender Identity: Domain verified (e.g., newsletter@example.com)
- Configuration Set: `zero2prod-newsletter` (for bounce/complaint tracking)
- Production Access: Requested (if > 50K emails/day)

**CloudWatch Log Group**:
- Name: `/aws/lambda/zero2prod-newsletter-sender`
- Retention: 30 days

**Outputs**:
- SQS Queue URL
- SQS Queue ARN
- DLQ URL
- Lambda Function Name
- Lambda Function ARN
- Lambda Execution Role ARN

**Requirements Mapping**: FR-2 (Background Email Worker), NFR-10 (Email Queueing), NFR-11 (Auto-Scaling), SECURITY-01 (Encryption)

---

### 6. Authentication Infrastructure Component

**Responsibility**: Provide secure, managed authentication for admin users using AWS Cognito User Pools with JWT token-based authentication.

**AWS Services Used**:
- Amazon Cognito User Pools
- AWS IAM (for Cognito service permissions)

**Component Details**:

**Cognito User Pool Configuration**:
- Pool Name: `zero2prod-admin-users`
- Username Attributes: Username (not email)
- Username Case Sensitivity: False
- MFA: Optional (per-user configuration)
- Account Recovery: Email (requires verified email attribute)

**Password Policy**:
- Minimum Length: 12 characters
- Require Uppercase: Yes
- Require Lowercase: Yes
- Require Numbers: Yes
- Require Symbols: Yes
- Temporary Password Validity: 7 days

**User Pool Client Configuration**:
- Client Name: `zero2prod-web-client`
- Auth Flows: ALLOW_USER_PASSWORD_AUTH, ALLOW_REFRESH_TOKEN_AUTH
- Access Token Validity: 1 hour
- ID Token Validity: 1 hour
- Refresh Token Validity: 30 days
- Prevent User Existence Errors: Enabled (for security)

**User Attributes** (Required):
- username (unique identifier)
- email (for password recovery)

**Account Lockout Policy**:
- Failed Login Attempts: 5
- Lockout Duration: 15 minutes

**JWT Token Structure**:
- Access Token: Contains user_id (sub claim), username, token expiration
- ID Token: Contains user attributes
- Refresh Token: Long-lived token for obtaining new access tokens

**User Migration Strategy**:
1. Export admin users from `users` table (usernames only)
2. Create Cognito users with temporary passwords
3. Send password reset emails to admin users
4. Users complete password reset flow on first login
5. `users` table deprecated for authentication (kept for audit trail)

**Outputs**:
- User Pool ID
- User Pool ARN
- User Pool Client ID
- User Pool Domain (for hosted UI, optional)

**Requirements Mapping**: FR-6 (Cognito Authentication), SECURITY-03 (Managed Auth Service)

---

### 7. Observability Infrastructure Component

**Responsibility**: Provide comprehensive monitoring, logging, alerting, and distributed tracing for all application components.

**AWS Services Used**:
- Amazon CloudWatch (Metrics, Logs, Alarms, Dashboards)
- AWS X-Ray (Distributed Tracing)
- Amazon SNS (Alert Notifications)
- Amazon S3 (ALB Access Logs)

**Component Details**:

**CloudWatch Dashboards**:

1. **Operational Dashboard**:
   - ALB Request Count (per minute)
   - ALB Target Response Time (p50, p95, p99)
   - ALB HTTP 4xx/5xx Error Count
   - ECS CPU Utilization (per task)
   - ECS Memory Utilization (per task)
   - ECS Task Count (running/desired)
   - Aurora Database Connections
   - Aurora Read/Write Latency
   - ElastiCache Hit Rate
   - SQS Queue Depth
   - Lambda Invocations
   - Lambda Errors
   - Lambda Duration (p50, p95, p99)

2. **Business Dashboard**:
   - Subscriptions per Hour (custom metric)
   - Newsletters Published per Day (custom metric)
   - Emails Sent per Hour (SQS messages processed)
   - Confirmation Rate (custom metric)

3. **Infrastructure Dashboard**:
   - Auto-Scaling Activity (scale-out/scale-in events)
   - VPC Endpoint Data Transfer
   - Cost Allocation by Service

**CloudWatch Alarms**:

1. **Critical Alarms** (Page oncall):
   - `ServiceDown`: ALB healthy target count = 0 for 5 minutes
   - `DatabaseDown`: Aurora cluster status != available for 2 minutes
   - `HighErrorRate`: HTTP 5xx error rate > 5% for 5 minutes
   - `LambdaHighErrorRate`: Lambda error rate > 10% for 5 minutes

2. **Warning Alarms** (Email team):
   - `DLQMessages`: DLQ message count > 0
   - `HighLatency`: ALB target response time p95 > 300ms for 10 minutes
   - `HighCPU`: ECS CPU utilization > 85% for 5 minutes
   - `DatabaseHighConnections`: Aurora connections > 80% of max for 5 minutes

**SNS Topics**:
- `zero2prod-critical-alerts`: Subscribed by PagerDuty (or email for MVP)
- `zero2prod-warning-alerts`: Subscribed by team email list

**X-Ray Configuration**:
- Sampling Rate: 5% of requests (configurable)
- Service Map: Shows ECS → Aurora, ECS → ElastiCache, ECS → SQS, Lambda → Aurora, Lambda → SES
- Trace Segments: HTTP requests, database queries, cache operations, email sends

**CloudWatch Log Insights Queries** (pre-configured):
1. Top 10 slowest API endpoints
2. Failed authentication attempts
3. Email delivery failures
4. Database slow queries (> 1 second)

**S3 Bucket for ALB Logs**:
- Bucket Name: `zero2prod-alb-logs-<account-id>`
- Lifecycle Policy: Delete logs older than 90 days
- Encryption: Server-side encryption enabled (S3 managed key)
- Versioning: Disabled

**Outputs**:
- CloudWatch Dashboard URLs
- SNS Topic ARNs
- S3 Bucket Name (ALB logs)

**Requirements Mapping**: NFR-7 (Monitoring and Tracing), NFR-8 (Alerting), NFR-6 (Access Logging), SECURITY-02 (Access Logging)

---

### 8. CI/CD Infrastructure Component

**Responsibility**: Provide automated deployment pipeline for infrastructure changes and application code updates using GitHub Actions.

**AWS Services Used**:
- AWS IAM (OIDC Provider for GitHub Actions)
- Amazon ECR (Container Registry)
- AWS CloudFormation (CDK deployment target)

**Component Details**:

**GitHub OIDC Provider**:
- Provider URL: `https://token.actions.githubusercontent.com`
- Audience: `sts.amazonaws.com`
- Thumbprint: GitHub's OIDC thumbprint

**IAM Role for GitHub Actions**:
- Role Name: `GitHubActionsDeployRole`
- Trust Policy: Allow AssumeRoleWithWebIdentity from GitHub Actions OIDC provider
- Condition: Repository filter (e.g., `repo:organization/zero2prod:*`)

**IAM Policy Permissions**:
- `cloudformation:*` (for CDK deployments)
- `ecr:*` (for Docker image push)
- `ecs:UpdateService` (for ECS service updates)
- `lambda:UpdateFunctionCode` (for Lambda deployments)
- `iam:PassRole` (for ECS task role)
- `s3:*` (for CDK bootstrap bucket)
- `ssm:GetParameter` (for CDK context)
- `secretsmanager:GetSecretValue` (for deployment secrets)

**GitHub Actions Workflow** (`.github/workflows/deploy.yml`):

**Stages**:
1. **Build**:
   - Checkout code
   - Install Rust toolchain
   - Run cargo build --release
   - Run cargo test
   - Run cargo clippy
   - Run cargo fmt --check

2. **Package**:
   - Build Docker image
   - Tag image with commit SHA and 'latest'
   - Push to ECR

3. **Deploy Infrastructure**:
   - Install AWS CDK
   - Configure AWS credentials (OIDC)
   - Run cdk diff (for review)
   - Run cdk deploy --all --require-approval never

4. **Deploy Application**:
   - Update ECS service with new task definition
   - Wait for deployment to complete
   - Package Lambda function (Rust binary)
   - Update Lambda function code

5. **Smoke Tests**:
   - Run health check against ALB endpoint
   - Verify authentication flow
   - Verify subscription flow
   - Verify newsletter publish (test idempotency)

**Environments**:
- `dev`: Auto-deploy on push to `develop` branch
- `staging`: Auto-deploy on push to `main` branch
- `production`: Manual approval required

**Outputs**:
- OIDC Provider ARN
- GitHub Actions Role ARN
- ECR Repository URI

**Requirements Mapping**: NFR-13 (Deployment Automation), NFR-14 (Infrastructure as Code)

---

## Application Components

These components are Rust code modules within the zero2prod application. They are modified to integrate with AWS services.

### 1. Configuration Module (`configuration.rs`)

**Responsibility**: Load application configuration from environment variables and AWS Secrets Manager, replacing file-based configuration.

**Key Changes**:
- Replace YAML file loading with environment variable parsing
- Integrate AWS Secrets Manager SDK to retrieve database credentials, Redis connection string, HMAC secret
- Support dynamic configuration updates (optional: cache secrets with 5-minute TTL)
- Validate required configuration keys at startup

**Dependencies**:
- `aws-config` crate (for AWS SDK configuration)
- `aws-sdk-secretsmanager` crate
- `tokio` (async runtime)
- `serde` (for JSON secret parsing)

**Public Interface**:
```rust
pub struct Settings {
    pub database: DatabaseSettings,
    pub application: ApplicationSettings,
    pub email_client: EmailClientSettings,
    pub sqs: SqsSettings,
}

pub async fn get_configuration() -> Result<Settings, ConfigError> {
    // Load from environment variables and Secrets Manager
}
```

**AWS Integration**:
- Calls `secretsmanager:GetSecretValue` for database credentials, Redis connection string, HMAC secret
- Parses JSON secrets into strongly-typed structs

**Requirements Mapping**: NFR-4 (Secrets Management), SECURITY-03 (Secrets Manager)

---

### 2. Startup Module (`startup.rs`)

**Responsibility**: Initialize application runtime, configure Actix-web server with middleware, establish database and cache connections, integrate Cognito authentication.

**Key Changes**:
- Update `build()` to use Aurora connection string from Secrets Manager
- Update session middleware to use ElastiCache connection string
- Add Cognito JWT validation middleware
- Remove background worker spawn (no longer needed)
- Configure X-Ray middleware for distributed tracing

**Dependencies**:
- `actix-web` (web framework)
- `actix-session` (session middleware)
- `sqlx` (database connection pool)
- `redis` (ElastiCache client)
- `aws-sdk-cognitoidentityprovider` (Cognito integration)
- `jsonwebtoken` (JWT validation)
- `tracing-actix-web` (HTTP tracing)
- `aws-xray-sdk` (X-Ray instrumentation)

**Public Interface**:
```rust
pub struct Application {
    port: u16,
    server: actix_web::dev::Server,
}

impl Application {
    pub async fn build(configuration: Settings) -> Result<Self, anyhow::Error>;
    pub fn port(&self) -> u16;
    pub async fn run_until_stopped(self) -> Result<(), std::io::Error>;
}
```

**AWS Integration**:
- Connects to Aurora PostgreSQL via TLS (enforced by connection string)
- Connects to ElastiCache Serverless via TLS (`rediss://`)
- Validates Cognito JWT tokens for admin routes

**Requirements Mapping**: FR-1 (Web Deployment), FR-4 (Session Store), FR-6 (Cognito Auth), NFR-7 (X-Ray Tracing)

---

### 3. Email Client Module (`email_client.rs`)

**Responsibility**: Send emails via Amazon SES instead of Postmark, supporting both transactional (confirmation) and bulk (newsletter) emails.

**Key Changes**:
- Replace Postmark HTTP client with AWS SDK for SES
- Update `SendEmailRequest` structure to SES format
- Remove `X-Postmark-Server-Token` header
- Add AWS SigV4 signing (handled by SDK)
- Use IAM role credentials instead of API token

**Dependencies**:
- `aws-config` crate
- `aws-sdk-sesv2` crate (SES API v2)
- `tokio` (async runtime)

**Public Interface**:
```rust
pub struct EmailClient {
    ses_client: aws_sdk_sesv2::Client,
    sender: SubscriberEmail,
}

impl EmailClient {
    pub async fn new(sender: SubscriberEmail) -> Self;
    
    pub async fn send_email(
        &self,
        recipient: &SubscriberEmail,
        subject: &str,
        html_content: &str,
        text_content: &str,
    ) -> Result<(), reqwest::Error>;
}
```

**AWS Integration**:
- Calls `ses:SendEmail` using AWS SDK
- Uses ECS task IAM role for authentication (no API token needed)

**Requirements Mapping**: FR-5 (SES Migration)

---

### 4. Authentication Module (`authentication/`)

**Responsibility**: Validate Cognito JWT tokens for admin authentication, replacing local password verification.

**Key Changes**:
- Remove `verify_password_hash()` function (replaced by Cognito)
- Add `validate_cognito_token()` function to verify JWT signature and claims
- Update `reject_anonymous_users` middleware to validate Cognito tokens
- Extract `user_id` from JWT `sub` claim instead of session state
- Update session state to store Cognito tokens

**Dependencies**:
- `aws-sdk-cognitoidentityprovider` crate
- `jsonwebtoken` crate (JWT parsing and validation)
- `serde` (for JWT claims deserialization)

**Public Interface**:
```rust
pub struct CognitoValidator {
    user_pool_id: String,
    client_id: String,
    jwks: JwkSet, // JSON Web Key Set for token verification
}

impl CognitoValidator {
    pub async fn new(user_pool_id: String, client_id: String) -> Result<Self, anyhow::Error>;
    
    pub fn validate_token(&self, token: &str) -> Result<Claims, ValidationError>;
}

pub struct Claims {
    pub sub: String,        // user_id
    pub username: String,
    pub exp: u64,           // expiration timestamp
    pub iat: u64,           // issued at timestamp
}

pub async fn reject_anonymous_users(
    req: ServiceRequest,
    credentials: Option<TypedHeader<headers::Authorization<headers::authorization::Bearer>>>,
) -> Result<ServiceRequest, (Error, ServiceRequest)>;
```

**AWS Integration**:
- Fetches Cognito JWKS endpoint for public keys
- Validates JWT signature using RS256 algorithm
- Verifies token expiration and issuer claims

**Requirements Mapping**: FR-6 (Cognito Authentication), SECURITY-04 (Managed Auth)

---

### 5. Routes Module (`routes/`)

**Responsibility**: Handle HTTP requests, orchestrate business logic, integrate with AWS services (SQS, Cognito, Aurora).

**Key Changes**:

**5.1. Newsletter Publish Route (`routes/admin/newsletter/post.rs`)**:
- Replace database queue writes with SQS batch send
- Update idempotency check to use Cognito `user_id` (from JWT `sub` claim)
- Remove `issue_delivery_queue` table inserts
- Add SQS message batching (10 messages per API call)

**Dependencies**:
- `aws-sdk-sqs` crate
- `sqlx` (for idempotency and newsletter storage)
- `actix-web`

**Public Interface**:
```rust
pub async fn publish_newsletter(
    form: web::Json<BodyData>,
    pool: web::Data<PgPool>,
    email_client: web::Data<EmailClient>,
    sqs_client: web::Data<aws_sdk_sqs::Client>,
    queue_url: web::Data<String>,
    user_id: web::ReqData<UserId>, // Extracted from Cognito JWT
) -> Result<HttpResponse, actix_web::Error>;
```

**AWS Integration**:
- Calls `sqs:SendMessageBatch` to enqueue delivery tasks
- Message format: `{"newsletter_issue_id": "uuid", "subscriber_email": "user@example.com"}`
- Batch size: 10 messages per API call (SQS limit)

**5.2. Login Route (`routes/login/post.rs`)**:
- Replace password verification with Cognito authentication
- Call Cognito `InitiateAuth` API with username/password
- Store Cognito access token and refresh token in session
- Extract `user_id` from Cognito response

**Dependencies**:
- `aws-sdk-cognitoidentityprovider` crate
- `actix-session` (session storage)
- `actix-web`

**Public Interface**:
```rust
pub async fn login(
    form: web::Form<FormData>,
    cognito_client: web::Data<aws_sdk_cognitoidentityprovider::Client>,
    user_pool_client_id: web::Data<String>,
    session: Session,
) -> Result<HttpResponse, actix_web::Error>;
```

**AWS Integration**:
- Calls `cognito-idp:InitiateAuth` with `USER_PASSWORD_AUTH` flow
- Retrieves access token, ID token, refresh token
- Stores tokens in Redis session

**5.3. Other Routes**:
- `/subscriptions`: No changes (writes to Aurora as before)
- `/subscriptions/confirm`: No changes (updates Aurora as before)
- `/admin/dashboard`: Update to validate Cognito JWT
- `/admin/password`: Update to use Cognito `ChangePassword` API

**Requirements Mapping**: FR-2 (SQS Integration), FR-6 (Cognito Auth), FR-7 (Public APIs), FR-8 (Admin APIs)

---

### 6. Domain Module (`domain.rs`)

**Responsibility**: Type-safe domain modeling with validation (unchanged).

**Key Changes**: NONE - Domain logic preserved as-is

**Components**:
- `SubscriberEmail`: Email validation
- `SubscriberName`: Name validation
- `NewSubscriber`: Aggregated validated subscriber

**Requirements Mapping**: FR-10 (Data Validation)

---

## Component Dependency Summary

| Component | Depends On | Provides To |
|-----------|-----------|-------------|
| Network Infrastructure | None | All other infrastructure components |
| Database Infrastructure | Network | Compute, Worker, Lambda |
| Cache Infrastructure | Network | Compute |
| Compute Infrastructure | Network, Database, Cache | Client requests, Worker (SQS) |
| Worker Infrastructure | Network, Database | (Independent, triggered by SQS) |
| Authentication Infrastructure | Network | Compute |
| Observability Infrastructure | Compute, Worker, Database, Cache | Monitoring system |
| CI/CD Infrastructure | None | All stacks (deployment pipeline) |
| Configuration Module | Secrets Manager | All application modules |
| Startup Module | Configuration, Database, Cache, Cognito | Application runtime |
| Email Client Module | SES | Routes |
| Authentication Module | Cognito | Routes (middleware) |
| Routes Module | Database, Email Client, SQS, Cognito | HTTP responses |
| Domain Module | None | Routes (validation) |

---

## AWS Service Mapping

| AWS Service | Infrastructure Component | Application Component |
|-------------|--------------------------|----------------------|
| VPC, Subnets, Security Groups | Network Infrastructure | N/A |
| VPC Endpoints | Network Infrastructure | N/A |
| Aurora PostgreSQL | Database Infrastructure | Configuration, Startup, Routes |
| ElastiCache Serverless | Cache Infrastructure | Configuration, Startup |
| ECS Fargate | Compute Infrastructure | Startup (runtime) |
| ALB | Compute Infrastructure | N/A |
| ECR | Compute Infrastructure | CI/CD |
| SQS | Worker Infrastructure | Routes (newsletter publish) |
| Lambda | Worker Infrastructure | (New Lambda handler code) |
| SES | Worker Infrastructure | Email Client |
| Cognito | Authentication Infrastructure | Authentication, Routes |
| Secrets Manager | Multiple (Database, Cache, Compute) | Configuration |
| CloudWatch | Observability Infrastructure | Startup (logging), Routes (metrics) |
| X-Ray | Observability Infrastructure | Startup (tracing) |
| SNS | Observability Infrastructure | N/A |
| IAM | All infrastructure components | N/A |
| CloudFormation (CDK) | All infrastructure components | N/A |
| S3 | Observability (ALB logs), CI/CD | N/A |

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-11  
**Status**: Ready for Review
