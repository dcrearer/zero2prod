# Component Methods

## Overview

This document defines key method signatures for both infrastructure components (CDK constructs) and application components (Rust modules). Detailed business rules and implementation logic will be covered in per-unit Functional Design documents.

---

## Infrastructure Components (CDK Constructs)

Infrastructure components are defined as AWS CDK constructs in Python. Each construct exposes initialization methods and properties for cross-stack references.

### 1. Network Infrastructure Component

**CDK Stack**: `NetworkStack`

**Constructor**:
```python
class NetworkStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs
    ) -> None:
        """
        Creates VPC with public/private subnets, security groups, and VPC endpoints.
        
        Args:
            scope: CDK construct scope
            construct_id: Stack identifier
        """
```

**Key Properties**:
```python
@property
def vpc(self) -> ec2.Vpc:
    """Returns the VPC construct."""

@property
def private_subnets(self) -> List[ec2.ISubnet]:
    """Returns list of private subnets for ECS, Lambda, Aurora, ElastiCache."""

@property
def public_subnets(self) -> List[ec2.ISubnet]:
    """Returns list of public subnets for ALB."""

@property
def alb_security_group(self) -> ec2.SecurityGroup:
    """Returns security group for Application Load Balancer."""

@property
def ecs_security_group(self) -> ec2.SecurityGroup:
    """Returns security group for ECS tasks."""

@property
def aurora_security_group(self) -> ec2.SecurityGroup:
    """Returns security group for Aurora database."""

@property
def elasticache_security_group(self) -> ec2.SecurityGroup:
    """Returns security group for ElastiCache."""

@property
def lambda_security_group(self) -> ec2.SecurityGroup:
    """Returns security group for Lambda functions."""

@property
def vpc_endpoint_security_group(self) -> ec2.SecurityGroup:
    """Returns security group for VPC endpoints."""
```

**Key Methods**:
```python
def _create_vpc_endpoints(self) -> None:
    """
    Creates VPC endpoints for AWS services (S3, ECR, Logs, Secrets Manager, STS, SES, SQS).
    No NAT Gateway - all AWS service access via private endpoints.
    """

def _create_security_groups(self) -> None:
    """
    Creates security groups with least-privilege rules:
    - ALB: Inbound 443 from internet, outbound to ECS
    - ECS: Inbound from ALB, outbound to Aurora/ElastiCache/VPC endpoints
    - Aurora: Inbound 5432 from ECS and Lambda only
    - ElastiCache: Inbound 6379 from ECS only
    - Lambda: Outbound to Aurora and VPC endpoints
    """
```

---

### 2. Database Infrastructure Component

**CDK Stack**: `DatabaseStack`

**Constructor**:
```python
class DatabaseStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        security_group: ec2.ISecurityGroup,
        **kwargs
    ) -> None:
        """
        Creates Aurora PostgreSQL Serverless v2 cluster with Multi-AZ, encryption, and Secrets Manager integration.
        
        Args:
            scope: CDK construct scope
            construct_id: Stack identifier
            vpc: VPC from NetworkStack
            security_group: Security group for Aurora
        """
```

**Key Properties**:
```python
@property
def cluster(self) -> rds.DatabaseCluster:
    """Returns the Aurora cluster construct."""

@property
def cluster_endpoint(self) -> str:
    """Returns the cluster writer endpoint."""

@property
def cluster_read_endpoint(self) -> str:
    """Returns the cluster reader endpoint."""

@property
def secret(self) -> secretsmanager.ISecret:
    """Returns the Secrets Manager secret containing database credentials."""

@property
def database_name(self) -> str:
    """Returns the database name ('newsletter')."""
```

**Key Methods**:
```python
def _create_parameter_group(self) -> rds.ParameterGroup:
    """
    Creates parameter group with security settings:
    - rds.force_ssl = 1 (enforce TLS)
    - log_connections = 1 (audit logging)
    - log_min_duration_statement = 1000 (log slow queries > 1s)
    """

def _create_database_secret(self) -> secretsmanager.Secret:
    """
    Creates Secrets Manager secret for database credentials.
    Format: {"username": "postgres", "password": "generated", "host": "endpoint", "port": 5432, "dbname": "newsletter"}
    Enables automatic rotation (30 days).
    """

def grant_read_access(self, grantee: iam.IGrantable) -> None:
    """
    Grants read-only access to the database (for read replicas or analytics).
    
    Args:
        grantee: IAM principal to grant access to
    """

def grant_read_write_access(self, grantee: iam.IGrantable) -> None:
    """
    Grants read/write access to the database (for ECS tasks and Lambda functions).
    
    Args:
        grantee: IAM principal to grant access to
    """
```

---

### 3. Cache Infrastructure Component

**CDK Stack**: `CacheStack`

**Constructor**:
```python
class CacheStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        security_group: ec2.ISecurityGroup,
        **kwargs
    ) -> None:
        """
        Creates ElastiCache Serverless for Redis cluster with Multi-AZ and encryption.
        
        Args:
            scope: CDK construct scope
            construct_id: Stack identifier
            vpc: VPC from NetworkStack
            security_group: Security group for ElastiCache
        """
```

**Key Properties**:
```python
@property
def cache_endpoint(self) -> str:
    """Returns the ElastiCache cluster endpoint."""

@property
def cache_port(self) -> int:
    """Returns the ElastiCache port (6379)."""

@property
def connection_secret(self) -> secretsmanager.ISecret:
    """Returns the Secrets Manager secret containing Redis connection string (rediss://)."""
```

**Key Methods**:
```python
def _create_connection_secret(self) -> secretsmanager.Secret:
    """
    Creates Secrets Manager secret for Redis connection string.
    Format: "rediss://<endpoint>:6379" (TLS-enabled Redis)
    """

def grant_access(self, grantee: iam.IGrantable) -> None:
    """
    Grants access to ElastiCache by allowing network connectivity (security group rule).
    
    Args:
        grantee: IAM principal to grant access to
    """
```

---

### 4. Compute Infrastructure Component

**CDK Stack**: `ComputeStack`

**Constructor**:
```python
class ComputeStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        alb_security_group: ec2.ISecurityGroup,
        ecs_security_group: ec2.ISecurityGroup,
        database_secret: secretsmanager.ISecret,
        cache_secret: secretsmanager.ISecret,
        **kwargs
    ) -> None:
        """
        Creates ECS Fargate cluster, ALB, ECR repository, task definition, and ECS service.
        
        Args:
            scope: CDK construct scope
            construct_id: Stack identifier
            vpc: VPC from NetworkStack
            alb_security_group: Security group for ALB
            ecs_security_group: Security group for ECS tasks
            database_secret: Secrets Manager secret for database credentials
            cache_secret: Secrets Manager secret for Redis connection string
        """
```

**Key Properties**:
```python
@property
def cluster(self) -> ecs.Cluster:
    """Returns the ECS cluster."""

@property
def service(self) -> ecs.FargateService:
    """Returns the ECS Fargate service."""

@property
def load_balancer(self) -> elbv2.ApplicationLoadBalancer:
    """Returns the Application Load Balancer."""

@property
def load_balancer_dns(self) -> str:
    """Returns the ALB DNS name for client access."""

@property
def task_role(self) -> iam.Role:
    """Returns the ECS task IAM role (application permissions)."""

@property
def execution_role(self) -> iam.Role:
    """Returns the ECS execution IAM role (ECS agent permissions)."""

@property
def ecr_repository(self) -> ecr.Repository:
    """Returns the ECR repository for Docker images."""
```

**Key Methods**:
```python
def _create_task_definition(self) -> ecs.FargateTaskDefinition:
    """
    Creates ECS task definition with:
    - CPU: 512 (0.5 vCPU)
    - Memory: 1024 MB (1 GB)
    - Container: zero2prod (port 8000)
    - Environment variables: DATABASE_URL, REDIS_URI, APP_APPLICATION__HMAC_SECRET (from Secrets Manager)
    - CloudWatch log group: /ecs/zero2prod-web
    """

def _create_ecs_service(self) -> ecs.FargateService:
    """
    Creates ECS Fargate service with:
    - Desired count: 2 (for HA)
    - Max count: 10 (auto-scaling limit)
    - Health check grace period: 60 seconds
    - Deployment circuit breaker enabled
    """

def _create_alb(self) -> elbv2.ApplicationLoadBalancer:
    """
    Creates Application Load Balancer with:
    - Internet-facing scheme
    - Multi-AZ deployment (public subnets)
    - HTTPS listener (port 443) with ACM certificate
    - HTTP redirect to HTTPS (port 80)
    - Access logging to S3
    """

def _create_target_group(self) -> elbv2.ApplicationTargetGroup:
    """
    Creates ALB target group with:
    - Target type: IP (for awsvpc mode)
    - Protocol: HTTP, Port: 8000
    - Health check path: /health_check
    - Health check interval: 30 seconds
    - Deregistration delay: 30 seconds
    """

def _configure_auto_scaling(self) -> None:
    """
    Configures ECS service auto-scaling:
    - Metric: CPU utilization
    - Target value: 70%
    - Min tasks: 2, Max tasks: 10
    - Scale-out cooldown: 60 seconds
    - Scale-in cooldown: 300 seconds
    """

def grant_sqs_send_access(self, queue: sqs.IQueue) -> None:
    """
    Grants ECS task role permission to send messages to SQS queue (for newsletter publishing).
    
    Args:
        queue: SQS queue for newsletter delivery
    """
```

---

### 5. Worker Infrastructure Component

**CDK Stack**: `WorkerStack`

**Constructor**:
```python
class WorkerStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        lambda_security_group: ec2.ISecurityGroup,
        database_secret: secretsmanager.ISecret,
        **kwargs
    ) -> None:
        """
        Creates SQS queue, DLQ, Lambda function for email sending, and SES configuration.
        
        Args:
            scope: CDK construct scope
            construct_id: Stack identifier
            vpc: VPC from NetworkStack
            lambda_security_group: Security group for Lambda
            database_secret: Secrets Manager secret for database credentials
        """
```

**Key Properties**:
```python
@property
def queue(self) -> sqs.Queue:
    """Returns the SQS queue for newsletter delivery tasks."""

@property
def dead_letter_queue(self) -> sqs.Queue:
    """Returns the SQS dead letter queue for failed tasks."""

@property
def lambda_function(self) -> lambda_.Function:
    """Returns the Lambda function for email sending."""

@property
def queue_url(self) -> str:
    """Returns the SQS queue URL."""
```

**Key Methods**:
```python
def _create_sqs_queue(self) -> sqs.Queue:
    """
    Creates SQS standard queue with:
    - Queue name: zero2prod-newsletter-delivery
    - Visibility timeout: 300 seconds (5 minutes)
    - Message retention: 14 days
    - Server-side encryption enabled
    - Dead letter queue: max receives = 3
    """

def _create_lambda_function(self) -> lambda_.Function:
    """
    Creates Lambda function with:
    - Runtime: Custom (Rust Lambda runtime)
    - Handler: bootstrap
    - Memory: 512 MB
    - Timeout: 60 seconds
    - Reserved concurrency: 100
    - VPC configuration: private subnets
    - Environment variables: DATABASE_URL, SENDER_EMAIL
    - SQS trigger: batch size = 10, max batching window = 5 seconds
    """

def _configure_ses(self) -> None:
    """
    Configures SES sender identity and configuration set:
    - Sender identity: Domain verification (e.g., newsletter@example.com)
    - Configuration set: zero2prod-newsletter
    - Bounce/complaint handling: SNS notifications
    """

def grant_ses_send_access(self) -> None:
    """
    Grants Lambda execution role permission to send emails via SES.
    """
```

---

### 6. Authentication Infrastructure Component

**CDK Stack**: `AuthStack`

**Constructor**:
```python
class AuthStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs
    ) -> None:
        """
        Creates Cognito User Pool and User Pool Client for admin authentication.
        
        Args:
            scope: CDK construct scope
            construct_id: Stack identifier
        """
```

**Key Properties**:
```python
@property
def user_pool(self) -> cognito.UserPool:
    """Returns the Cognito User Pool."""

@property
def user_pool_client(self) -> cognito.UserPoolClient:
    """Returns the Cognito User Pool Client."""

@property
def user_pool_id(self) -> str:
    """Returns the User Pool ID."""

@property
def client_id(self) -> str:
    """Returns the User Pool Client ID."""
```

**Key Methods**:
```python
def _create_user_pool(self) -> cognito.UserPool:
    """
    Creates Cognito User Pool with:
    - Pool name: zero2prod-admin-users
    - Username attributes: username (not email)
    - Password policy: 12+ chars, uppercase, lowercase, numbers, symbols
    - Account lockout: 5 failed attempts, 15-minute lockout
    - MFA: Optional
    """

def _create_user_pool_client(self) -> cognito.UserPoolClient:
    """
    Creates User Pool Client with:
    - Client name: zero2prod-web-client
    - Auth flows: USER_PASSWORD_AUTH, REFRESH_TOKEN_AUTH
    - Access token validity: 1 hour
    - Refresh token validity: 30 days
    - Prevent user existence errors: enabled
    """
```

---

### 7. Observability Infrastructure Component

**CDK Stack**: `ObservabilityStack`

**Constructor**:
```python
class ObservabilityStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        load_balancer: elbv2.IApplicationLoadBalancer,
        ecs_service: ecs.IFargateService,
        aurora_cluster: rds.IDatabaseCluster,
        lambda_function: lambda_.IFunction,
        sqs_queue: sqs.IQueue,
        dlq: sqs.IQueue,
        **kwargs
    ) -> None:
        """
        Creates CloudWatch dashboards, alarms, X-Ray configuration, and SNS topics for alerts.
        
        Args:
            scope: CDK construct scope
            construct_id: Stack identifier
            load_balancer: ALB from ComputeStack
            ecs_service: ECS service from ComputeStack
            aurora_cluster: Aurora cluster from DatabaseStack
            lambda_function: Lambda function from WorkerStack
            sqs_queue: SQS queue from WorkerStack
            dlq: Dead letter queue from WorkerStack
        """
```

**Key Properties**:
```python
@property
def operational_dashboard(self) -> cloudwatch.Dashboard:
    """Returns the operational CloudWatch dashboard."""

@property
def business_dashboard(self) -> cloudwatch.Dashboard:
    """Returns the business metrics CloudWatch dashboard."""

@property
def critical_alerts_topic(self) -> sns.Topic:
    """Returns the SNS topic for critical alerts (PagerDuty)."""

@property
def warning_alerts_topic(self) -> sns.Topic:
    """Returns the SNS topic for warning alerts (email)."""
```

**Key Methods**:
```python
def _create_operational_dashboard(self) -> cloudwatch.Dashboard:
    """
    Creates operational dashboard with widgets:
    - ALB request count, target response time, error rates
    - ECS CPU/memory utilization, task count
    - Aurora connections, read/write latency
    - ElastiCache hit rate
    - SQS queue depth
    - Lambda invocations, errors, duration
    """

def _create_business_dashboard(self) -> cloudwatch.Dashboard:
    """
    Creates business metrics dashboard with widgets:
    - Subscriptions per hour
    - Newsletters published per day
    - Emails sent per hour
    - Confirmation rate
    """

def _create_alarms(self) -> None:
    """
    Creates CloudWatch alarms:
    Critical (page oncall):
    - ServiceDown: ALB healthy targets = 0 for 5 minutes
    - DatabaseDown: Aurora status != available for 2 minutes
    - HighErrorRate: HTTP 5xx > 5% for 5 minutes
    - LambdaHighErrorRate: Lambda errors > 10% for 5 minutes
    
    Warning (email team):
    - DLQMessages: DLQ count > 0
    - HighLatency: ALB p95 > 300ms for 10 minutes
    - HighCPU: ECS CPU > 85% for 5 minutes
    """

def _configure_xray(self) -> None:
    """
    Configures X-Ray tracing:
    - ECS task X-Ray daemon sidecar
    - Lambda X-Ray active tracing
    - Sampling rate: 5%
    """

def _create_alb_access_logs_bucket(self) -> s3.Bucket:
    """
    Creates S3 bucket for ALB access logs:
    - Bucket name: zero2prod-alb-logs-<account-id>
    - Encryption: Server-side encryption (S3 managed)
    - Lifecycle policy: Delete logs older than 90 days
    """
```

---

### 8. CI/CD Infrastructure Component

**CDK Stack**: `CicdStack`

**Constructor**:
```python
class CicdStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        github_org: str,
        github_repo: str,
        **kwargs
    ) -> None:
        """
        Creates GitHub OIDC provider and IAM role for GitHub Actions.
        
        Args:
            scope: CDK construct scope
            construct_id: Stack identifier
            github_org: GitHub organization name
            github_repo: GitHub repository name
        """
```

**Key Properties**:
```python
@property
def github_oidc_provider(self) -> iam.OpenIdConnectProvider:
    """Returns the GitHub OIDC provider."""

@property
def github_actions_role(self) -> iam.Role:
    """Returns the IAM role for GitHub Actions."""

@property
def github_actions_role_arn(self) -> str:
    """Returns the ARN of the GitHub Actions role."""
```

**Key Methods**:
```python
def _create_github_oidc_provider(self) -> iam.OpenIdConnectProvider:
    """
    Creates GitHub OIDC provider:
    - Provider URL: https://token.actions.githubusercontent.com
    - Audience: sts.amazonaws.com
    """

def _create_github_actions_role(self) -> iam.Role:
    """
    Creates IAM role for GitHub Actions with permissions:
    - CloudFormation (for CDK deployments)
    - ECR (for Docker image push)
    - ECS (for service updates)
    - Lambda (for function updates)
    - IAM (for PassRole)
    - S3 (for CDK bootstrap bucket)
    - SSM (for CDK context)
    - Secrets Manager (for deployment secrets)
    
    Trust policy: Allow AssumeRoleWithWebIdentity from GitHub Actions OIDC
    Condition: Repository filter (e.g., repo:org/repo:*)
    """
```

---

## Application Components (Rust Modules)

Application components are Rust code modules. Method signatures use Rust syntax.

### 1. Configuration Module (`configuration.rs`)

**Purpose**: Load configuration from environment variables and Secrets Manager.

**Key Structs**:
```rust
pub struct Settings {
    pub database: DatabaseSettings,
    pub application: ApplicationSettings,
    pub email_client: EmailClientSettings,
    pub sqs: SqsSettings,
    pub cognito: CognitoSettings,
}

pub struct DatabaseSettings {
    pub username: String,
    pub password: secrecy::Secret<String>,
    pub port: u16,
    pub host: String,
    pub database_name: String,
    pub require_ssl: bool,
}

pub struct ApplicationSettings {
    pub port: u16,
    pub host: String,
    pub base_url: String,
    pub hmac_secret: secrecy::Secret<String>,
}

pub struct EmailClientSettings {
    pub sender_email: String,
}

pub struct SqsSettings {
    pub queue_url: String,
}

pub struct CognitoSettings {
    pub user_pool_id: String,
    pub client_id: String,
    pub region: String,
}
```

**Key Functions**:
```rust
pub async fn get_configuration() -> Result<Settings, ConfigError> {
    /// Loads configuration from environment variables and AWS Secrets Manager.
    /// 
    /// Steps:
    /// 1. Load AWS region from AWS_REGION environment variable
    /// 2. Initialize AWS SDK config
    /// 3. Retrieve database credentials from Secrets Manager
    /// 4. Retrieve Redis connection string from Secrets Manager
    /// 5. Retrieve HMAC secret from Secrets Manager
    /// 6. Parse environment variables for application settings
    /// 7. Validate required configuration keys
    /// 
    /// Returns:
    ///   Ok(Settings) on success
    ///   Err(ConfigError) if any required key is missing or Secrets Manager call fails
}

async fn get_database_settings(
    secrets_client: &aws_sdk_secretsmanager::Client,
) -> Result<DatabaseSettings, ConfigError> {
    /// Retrieves database configuration from Secrets Manager.
    /// 
    /// Args:
    ///   secrets_client: Secrets Manager client
    /// 
    /// Returns:
    ///   DatabaseSettings struct with username, password, host, port, database_name
}

async fn get_redis_connection_string(
    secrets_client: &aws_sdk_secretsmanager::Client,
) -> Result<String, ConfigError> {
    /// Retrieves Redis connection string from Secrets Manager.
    /// 
    /// Args:
    ///   secrets_client: Secrets Manager client
    /// 
    /// Returns:
    ///   Redis connection string (rediss://<endpoint>:6379)
}

async fn get_hmac_secret(
    secrets_client: &aws_sdk_secretsmanager::Client,
) -> Result<secrecy::Secret<String>, ConfigError> {
    /// Retrieves HMAC secret from Secrets Manager.
    /// 
    /// Args:
    ///   secrets_client: Secrets Manager client
    /// 
    /// Returns:
    ///   HMAC secret wrapped in secrecy::Secret for safe handling
}
```

**Implementation Notes**:
- Uses `aws-config` crate to initialize AWS SDK
- Uses `aws-sdk-secretsmanager` crate for secret retrieval
- Caches secrets in memory (optional: 5-minute TTL for dynamic updates)
- Validates all required keys at startup (fail fast)

---

### 2. Startup Module (`startup.rs`)

**Purpose**: Initialize application runtime, configure Actix-web with middleware, establish database/cache connections.

**Key Structs**:
```rust
pub struct Application {
    port: u16,
    server: actix_web::dev::Server,
}

pub struct ApplicationBaseUrl(pub String);
```

**Key Methods**:
```rust
impl Application {
    pub async fn build(configuration: Settings) -> Result<Self, anyhow::Error> {
        /// Builds the application runtime.
        /// 
        /// Steps:
        /// 1. Initialize database connection pool (SQLx with Aurora endpoint)
        /// 2. Initialize Redis client (ElastiCache connection string)
        /// 3. Initialize SQS client (AWS SDK)
        /// 4. Initialize Cognito validator (for JWT verification)
        /// 5. Configure Actix-web server with middleware:
        ///    - TracingLogger (HTTP request tracing)
        ///    - FlashMessages (session-based flash messages)
        ///    - SessionMiddleware (Redis-backed sessions)
        ///    - X-Ray middleware (distributed tracing)
        /// 6. Register routes (public, admin)
        /// 7. Bind server to configured address and port
        /// 
        /// Args:
        ///   configuration: Settings loaded from environment and Secrets Manager
        /// 
        /// Returns:
        ///   Ok(Application) on success
        ///   Err(anyhow::Error) if any initialization step fails
    }
    
    pub fn port(&self) -> u16 {
        /// Returns the port the server is bound to.
    }
    
    pub async fn run_until_stopped(self) -> Result<(), std::io::Error> {
        /// Runs the Actix-web server until stopped (SIGTERM or SIGINT).
        /// 
        /// Returns:
        ///   Ok(()) on graceful shutdown
        ///   Err(std::io::Error) on server error
    }
}

fn get_connection_pool(configuration: &DatabaseSettings) -> Result<PgPool, sqlx::Error> {
    /// Creates SQLx connection pool for Aurora PostgreSQL.
    /// 
    /// Configuration:
    ///   - SSL Mode: Require (enforce TLS)
    ///   - Min Connections: 5
    ///   - Max Connections: 20
    ///   - Connection Timeout: 10 seconds
    ///   - Idle Timeout: 600 seconds
    /// 
    /// Args:
    ///   configuration: Database settings with connection string
    /// 
    /// Returns:
    ///   Ok(PgPool) on success
    ///   Err(sqlx::Error) if connection fails
}

fn get_redis_client(redis_uri: &str) -> Result<redis::Client, redis::RedisError> {
    /// Creates Redis client for ElastiCache.
    /// 
    /// Args:
    ///   redis_uri: Redis connection string (rediss://)
    /// 
    /// Returns:
    ///   Ok(redis::Client) on success
    ///   Err(redis::RedisError) if connection fails
}
```

**Implementation Notes**:
- Uses `sqlx::PgPool` for database connection pooling
- Uses `redis::Client` for Redis connections
- Uses `aws-sdk-sqs::Client` for SQS integration
- Uses custom `CognitoValidator` for JWT validation
- Uses `tracing-actix-web` for HTTP request tracing
- Uses `actix-session` with Redis storage for session management

---

### 3. Email Client Module (`email_client.rs`)

**Purpose**: Send emails via Amazon SES.

**Key Structs**:
```rust
pub struct EmailClient {
    ses_client: aws_sdk_sesv2::Client,
    sender: SubscriberEmail,
}
```

**Key Methods**:
```rust
impl EmailClient {
    pub async fn new(sender: SubscriberEmail) -> Self {
        /// Creates a new EmailClient using AWS SDK for SES.
        /// 
        /// Steps:
        /// 1. Initialize AWS SDK config
        /// 2. Create SES v2 client
        /// 3. Store sender email
        /// 
        /// Args:
        ///   sender: Verified sender email address
        /// 
        /// Returns:
        ///   EmailClient instance
    }
    
    pub async fn send_email(
        &self,
        recipient: &SubscriberEmail,
        subject: &str,
        html_content: &str,
        text_content: &str,
    ) -> Result<(), anyhow::Error> {
        /// Sends an email via Amazon SES.
        /// 
        /// Steps:
        /// 1. Build SES SendEmail request with:
        ///    - From address: sender email
        ///    - To address: recipient email
        ///    - Subject: email subject
        ///    - Body: HTML and text content
        /// 2. Call SES SendEmail API
        /// 3. Handle errors (throttling, bounces, etc.)
        /// 
        /// Args:
        ///   recipient: Recipient email address
        ///   subject: Email subject
        ///   html_content: HTML email body
        ///   text_content: Plain text email body
        /// 
        /// Returns:
        ///   Ok(()) on success
        ///   Err(anyhow::Error) on SES API error
    }
}
```

**Implementation Notes**:
- Uses `aws-sdk-sesv2::Client` for SES API v2
- Uses ECS task IAM role for authentication (no API token needed)
- Includes retry logic for throttling errors (exponential backoff)
- Logs email send failures with context (recipient, subject)

---

### 4. Authentication Module (`authentication/`)

**Purpose**: Validate Cognito JWT tokens for admin authentication.

**Key Structs**:
```rust
pub struct CognitoValidator {
    user_pool_id: String,
    client_id: String,
    jwks: jsonwebtoken::jwk::JwkSet,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Claims {
    pub sub: String,        // user_id
    pub username: String,
    pub exp: u64,           // expiration timestamp
    pub iat: u64,           // issued at timestamp
    pub aud: String,        // audience (client_id)
    pub iss: String,        // issuer (Cognito User Pool URL)
}

pub struct UserId(pub Uuid);
```

**Key Methods**:
```rust
impl CognitoValidator {
    pub async fn new(
        user_pool_id: String,
        client_id: String,
        region: String,
    ) -> Result<Self, anyhow::Error> {
        /// Creates a new CognitoValidator.
        /// 
        /// Steps:
        /// 1. Construct Cognito JWKS endpoint URL
        /// 2. Fetch JWKS (JSON Web Key Set) from Cognito
        /// 3. Parse JWKS for public keys
        /// 4. Store user_pool_id, client_id, and JWKS
        /// 
        /// Args:
        ///   user_pool_id: Cognito User Pool ID
        ///   client_id: Cognito User Pool Client ID
        ///   region: AWS region
        /// 
        /// Returns:
        ///   Ok(CognitoValidator) on success
        ///   Err(anyhow::Error) if JWKS fetch fails
    }
    
    pub fn validate_token(&self, token: &str) -> Result<Claims, ValidationError> {
        /// Validates a Cognito JWT token.
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
        /// Args:
        ///   token: JWT access token from Cognito
        /// 
        /// Returns:
        ///   Ok(Claims) on valid token
        ///   Err(ValidationError) on invalid signature, expired token, or claim mismatch
    }
}

pub async fn reject_anonymous_users(
    req: ServiceRequest,
    credentials: Option<TypedHeader<headers::Authorization<headers::authorization::Bearer>>>,
) -> Result<ServiceRequest, (Error, ServiceRequest)> {
    /// Actix-web middleware to protect admin routes.
    /// 
    /// Steps:
    /// 1. Extract Bearer token from Authorization header
    /// 2. Validate token using CognitoValidator
    /// 3. Extract user_id from sub claim
    /// 4. Store user_id in request extensions (for downstream handlers)
    /// 5. Allow request to proceed if token is valid
    /// 6. Return 401 Unauthorized if token is missing or invalid
    /// 
    /// Args:
    ///   req: Actix-web service request
    ///   credentials: Optional Authorization header
    /// 
    /// Returns:
    ///   Ok(ServiceRequest) if authenticated
    ///   Err((Error, ServiceRequest)) if not authenticated
}
```

**Implementation Notes**:
- Uses `jsonwebtoken` crate for JWT parsing and validation
- Uses `reqwest` to fetch JWKS from Cognito
- Caches JWKS in memory (refresh every 1 hour)
- Validates RS256 signature (Cognito uses asymmetric keys)

---

### 5. Routes Module (`routes/`)

**Purpose**: Handle HTTP requests, orchestrate business logic, integrate with AWS services.

#### 5.1 Newsletter Publish Route (`routes/admin/newsletter/post.rs`)

**Key Structs**:
```rust
#[derive(serde::Deserialize)]
pub struct BodyData {
    pub title: String,
    pub text_content: String,
    pub html_content: String,
    pub idempotency_key: String,
}
```

**Key Functions**:
```rust
pub async fn publish_newsletter(
    form: web::Json<BodyData>,
    pool: web::Data<PgPool>,
    email_client: web::Data<EmailClient>,
    sqs_client: web::Data<aws_sdk_sqs::Client>,
    queue_url: web::Data<String>,
    user_id: web::ReqData<UserId>,
) -> Result<HttpResponse, actix_web::Error> {
    /// Publishes a newsletter by inserting issue and enqueuing delivery tasks to SQS.
    /// 
    /// Steps:
    /// 1. Validate input (title, content non-empty)
    /// 2. Check idempotency key in database (return cached response if exists)
    /// 3. Begin database transaction
    /// 4. Insert newsletter issue into newsletter_issues table
    /// 5. Fetch all confirmed subscribers
    /// 6. Batch SQS send messages (10 messages per API call):
    ///    - Message body: {"newsletter_issue_id": "uuid", "subscriber_email": "user@example.com"}
    /// 7. Save idempotent response (status 303, location header)
    /// 8. Commit transaction
    /// 9. Return 303 See Other (redirect to /admin/newsletters)
    /// 
    /// Args:
    ///   form: Newsletter title, text_content, html_content, idempotency_key
    ///   pool: SQLx connection pool
    ///   email_client: EmailClient (not used in this endpoint)
    ///   sqs_client: SQS client
    ///   queue_url: SQS queue URL
    ///   user_id: User ID extracted from Cognito JWT
    /// 
    /// Returns:
    ///   Ok(HttpResponse 303) on success
    ///   Err(actix_web::Error) on validation error, database error, or SQS error
}

async fn enqueue_delivery_tasks(
    sqs_client: &aws_sdk_sqs::Client,
    queue_url: &str,
    newsletter_issue_id: Uuid,
    confirmed_subscribers: Vec<SubscriberEmail>,
) -> Result<(), anyhow::Error> {
    /// Enqueues newsletter delivery tasks to SQS in batches.
    /// 
    /// Steps:
    /// 1. Create messages for all confirmed subscribers
    /// 2. Batch messages (10 per batch - SQS limit)
    /// 3. Call sqs:SendMessageBatch for each batch
    /// 4. Handle partial failures (retry failed messages)
    /// 
    /// Args:
    ///   sqs_client: SQS client
    ///   queue_url: SQS queue URL
    ///   newsletter_issue_id: Newsletter issue UUID
    ///   confirmed_subscribers: List of confirmed subscriber emails
    /// 
    /// Returns:
    ///   Ok(()) on success
    ///   Err(anyhow::Error) on SQS API error
}
```

#### 5.2 Login Route (`routes/login/post.rs`)

**Key Structs**:
```rust
#[derive(serde::Deserialize)]
pub struct FormData {
    pub username: String,
    pub password: secrecy::Secret<String>,
}
```

**Key Functions**:
```rust
pub async fn login(
    form: web::Form<FormData>,
    cognito_client: web::Data<aws_sdk_cognitoidentityprovider::Client>,
    user_pool_client_id: web::Data<String>,
    session: Session,
) -> Result<HttpResponse, actix_web::Error> {
    /// Authenticates a user via Cognito and stores tokens in session.
    /// 
    /// Steps:
    /// 1. Validate input (username, password non-empty)
    /// 2. Call Cognito InitiateAuth API with USER_PASSWORD_AUTH flow:
    ///    - AuthParameters: USERNAME, PASSWORD
    ///    - ClientId: User Pool Client ID
    /// 3. Extract tokens from Cognito response:
    ///    - AccessToken: Short-lived token for API requests
    ///    - IdToken: Contains user attributes
    ///    - RefreshToken: Long-lived token for token refresh
    /// 4. Store tokens in session (Redis):
    ///    - session.insert("access_token", access_token)
    ///    - session.insert("refresh_token", refresh_token)
    ///    - session.insert("user_id", sub_claim_from_id_token)
    /// 5. Return 303 See Other (redirect to /admin/dashboard)
    /// 
    /// Args:
    ///   form: Username and password
    ///   cognito_client: Cognito Identity Provider client
    ///   user_pool_client_id: Cognito User Pool Client ID
    ///   session: Actix-session Session
    /// 
    /// Returns:
    ///   Ok(HttpResponse 303) on success
    ///   Err(actix_web::Error) on authentication failure
}
```

#### 5.3 Other Routes (No AWS Integration Changes)

**Unchanged Routes**:
- `GET /` (home page)
- `GET /health_check` (health check)
- `POST /subscriptions` (newsletter subscription - writes to Aurora)
- `GET /subscriptions/confirm` (email confirmation - updates Aurora)
- `GET /login` (login form)
- `GET /admin/dashboard` (admin dashboard - uses Cognito JWT middleware)
- `GET /admin/newsletters` (newsletter form - uses Cognito JWT middleware)
- `GET /admin/password` (change password form - uses Cognito JWT middleware)
- `POST /admin/password` (change password - calls Cognito ChangePassword API)
- `POST /admin/logout` (logout - clears session)

---

### 6. Lambda Handler (New Component)

**Purpose**: Process SQS messages and send emails via SES.

**File**: `lambda/newsletter-sender/src/main.rs` (new Rust Lambda function)

**Key Structs**:
```rust
#[derive(Deserialize)]
struct SqsMessage {
    newsletter_issue_id: Uuid,
    subscriber_email: String,
}

#[derive(Deserialize)]
struct NewsletterIssue {
    title: String,
    text_content: String,
    html_content: String,
}
```

**Key Functions**:
```rust
async fn handler(event: LambdaEvent<SqsEvent>) -> Result<(), Error> {
    /// Lambda handler for SQS trigger.
    /// 
    /// Steps:
    /// 1. Initialize AWS SDK config
    /// 2. Create SES client
    /// 3. Create database connection (SQLx)
    /// 4. For each SQS message in batch:
    ///    a. Parse message body (newsletter_issue_id, subscriber_email)
    ///    b. Fetch newsletter content from Aurora
    ///    c. Send email via SES
    ///    d. Log success or error
    ///    e. Return success (SQS deletes message) or error (SQS retries)
    /// 5. Return batch result
    /// 
    /// Args:
    ///   event: SQS event with batch of messages (up to 10)
    /// 
    /// Returns:
    ///   Ok(()) on success (all messages processed)
    ///   Err(Error) on failure (partial batch failure handled by SQS)
}

async fn fetch_newsletter_content(
    pool: &PgPool,
    newsletter_issue_id: Uuid,
) -> Result<NewsletterIssue, sqlx::Error> {
    /// Fetches newsletter content from Aurora.
    /// 
    /// Args:
    ///   pool: SQLx connection pool
    ///   newsletter_issue_id: Newsletter issue UUID
    /// 
    /// Returns:
    ///   Ok(NewsletterIssue) on success
    ///   Err(sqlx::Error) if newsletter not found or database error
}

async fn send_newsletter_email(
    ses_client: &aws_sdk_sesv2::Client,
    sender_email: &str,
    recipient_email: &str,
    newsletter: &NewsletterIssue,
) -> Result<(), anyhow::Error> {
    /// Sends newsletter email via SES.
    /// 
    /// Args:
    ///   ses_client: SES client
    ///   sender_email: Verified sender email address
    ///   recipient_email: Subscriber email address
    ///   newsletter: Newsletter content (title, text, html)
    /// 
    /// Returns:
    ///   Ok(()) on success
    ///   Err(anyhow::Error) on SES API error
}
```

**Implementation Notes**:
- Uses `lambda_runtime` crate for AWS Lambda runtime
- Uses `aws-lambda-events` crate for SQS event parsing
- Uses `aws-sdk-sesv2` for SES email sending
- Uses `sqlx` for Aurora database queries
- Uses Lambda execution IAM role for authentication
- Logs to CloudWatch Logs with structured JSON format

---

## Summary

This document provides comprehensive method signatures for all infrastructure components (CDK constructs) and application components (Rust modules). Detailed business rules, validation logic, and implementation details will be covered in per-unit Functional Design documents during the Construction phase.

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-11  
**Status**: Ready for Review
