# Component Dependencies

## Overview

This document defines the component dependency graph for the AWS modernized architecture, covering both deployment dependencies (which CDK stacks depend on others) and runtime dependencies (which services call which services).

---

## Component Dependency Graph

### High-Level Dependency Visualization

```mermaid
graph TB
    subgraph "Infrastructure Layer (CDK Stacks)"
        Network[Network Stack<br/>VPC, Subnets, SGs, VPC Endpoints]
        Database[Database Stack<br/>Aurora PostgreSQL]
        Cache[Cache Stack<br/>ElastiCache Serverless]
        Compute[Compute Stack<br/>ECS, ALB, ECR]
        Worker[Worker Stack<br/>SQS, Lambda, SES]
        Auth[Auth Stack<br/>Cognito User Pool]
        Observability[Observability Stack<br/>CloudWatch, X-Ray, SNS]
        CICD[CI/CD Stack<br/>GitHub OIDC, IAM]
    end
    
    subgraph "Application Layer (Rust Modules)"
        Config[Configuration Module]
        Startup[Startup Module]
        EmailClient[Email Client Module]
        AuthModule[Authentication Module]
        Routes[Routes Module]
        Domain[Domain Module]
    end
    
    subgraph "Runtime Components"
        Lambda[Lambda Handler<br/>newsletter-sender]
    end
    
    %% Infrastructure Dependencies (Deployment Order)
    Network --> Database
    Network --> Cache
    Network --> Auth
    Database --> Compute
    Cache --> Compute
    Network --> Worker
    Database --> Worker
    Compute --> Observability
    Worker --> Observability
    CICD -.->|deploys| Compute
    CICD -.->|deploys| Worker
    
    %% Application Dependencies
    Config --> Startup
    Config --> EmailClient
    Config --> AuthModule
    Domain --> Routes
    EmailClient --> Routes
    AuthModule --> Routes
    Startup --> Routes
    
    %% Runtime Dependencies (AWS Service Integration)
    Compute -->|reads secrets| Database
    Compute -->|reads secrets| Cache
    Compute -->|connects to| Database
    Compute -->|connects to| Cache
    Compute -->|writes to| Worker
    Compute -->|authenticates via| Auth
    Worker -->|triggered by| Worker
    Lambda -->|reads from| Database
    Lambda -->|sends via| Worker
    Observability -->|monitors| Compute
    Observability -->|monitors| Worker
    Observability -->|monitors| Database
    
    style Network fill:#1976D2,stroke:#0D47A1,stroke-width:3px,color:#fff
    style Database fill:#388E3C,stroke:#1B5E20,stroke-width:3px,color:#fff
    style Cache fill:#F57C00,stroke:#E65100,stroke-width:3px,color:#fff
    style Compute fill:#7B1FA2,stroke:#4A148C,stroke-width:3px,color:#fff
    style Worker fill:#C62828,stroke:#B71C1C,stroke-width:3px,color:#fff
    style Auth fill:#00796B,stroke:#004D40,stroke-width:3px,color:#fff
    style Observability fill:#FBC02D,stroke:#F57F17,stroke-width:3px,color:#000
    style CICD fill:#616161,stroke:#212121,stroke-width:3px,color:#fff
    
    style Config fill:#BBDEFB,stroke:#1976D2,stroke-width:2px,color:#000
    style Startup fill:#BBDEFB,stroke:#1976D2,stroke-width:2px,color:#000
    style EmailClient fill:#BBDEFB,stroke:#1976D2,stroke-width:2px,color:#000
    style AuthModule fill:#BBDEFB,stroke:#1976D2,stroke-width:2px,color:#000
    style Routes fill:#BBDEFB,stroke:#1976D2,stroke-width:2px,color:#000
    style Domain fill:#BBDEFB,stroke:#1976D2,stroke-width:2px,color:#000
    
    style Lambda fill:#FFE082,stroke:#FFA000,stroke-width:2px,color:#000
```

---

## Deployment Dependencies (CDK Stack Order)

Deployment dependencies determine the order in which CDK stacks must be deployed. A stack can only be deployed after all its dependencies are successfully deployed.

### Deployment Order

**Phase 1: Foundation**
1. **Network Stack** (no dependencies)
   - Creates VPC, subnets, security groups, VPC endpoints
   - All other stacks depend on networking resources

**Phase 2: Data Layer**
2. **Database Stack** (depends on: Network)
   - Requires VPC ID, private subnets, Aurora security group
3. **Cache Stack** (depends on: Network)
   - Requires VPC ID, private subnets, ElastiCache security group

**Phase 3: Authentication**
4. **Auth Stack** (no infrastructure dependencies, but logically after Network)
   - Creates Cognito User Pool (no VPC integration)
   - Independent deployment, but needed by Compute Stack

**Phase 4: Compute Layer**
5. **Compute Stack** (depends on: Network, Database, Cache)
   - Requires VPC, subnets, security groups
   - Requires database secret ARN (from Database Stack)
   - Requires cache secret ARN (from Cache Stack)
   - Needs Auth Stack for Cognito User Pool ID (runtime dependency)

**Phase 5: Worker Layer**
6. **Worker Stack** (depends on: Network, Database)
   - Requires VPC ID, private subnets, Lambda security group
   - Requires database secret ARN (for Lambda)
   - Creates SQS queue (used by Compute Stack at runtime)

**Phase 6: Observability & CI/CD**
7. **Observability Stack** (depends on: Compute, Worker, Database, Cache)
   - Requires ALB ARN, ECS service name, Aurora cluster ID, Lambda function name
   - Creates dashboards and alarms for deployed resources
8. **CI/CD Stack** (no dependencies)
   - Creates GitHub OIDC provider and IAM role
   - Independent deployment

### Deployment Dependency Matrix

| Stack | Depends On | Provides To |
|-------|-----------|-------------|
| Network | None | Database, Cache, Compute, Worker, Auth |
| Database | Network | Compute, Worker, Observability |
| Cache | Network | Compute, Observability |
| Auth | None | Compute (runtime) |
| Compute | Network, Database, Cache | Worker (runtime), Observability |
| Worker | Network, Database | Compute (runtime), Observability |
| Observability | Compute, Worker, Database, Cache | Monitoring system |
| CI/CD | None | All stacks (deployment pipeline) |

### Cross-Stack References (CloudFormation Outputs)

**Network Stack Outputs**:
- `VpcId`: VPC identifier
- `PublicSubnetIds`: List of public subnet IDs (for ALB)
- `PrivateSubnetIds`: List of private subnet IDs (for ECS, Lambda, Aurora, ElastiCache)
- `AlbSecurityGroupId`: Security group for ALB
- `EcsSecurityGroupId`: Security group for ECS tasks
- `AuroraSecurityGroupId`: Security group for Aurora
- `ElastiCacheSecurityGroupId`: Security group for ElastiCache
- `LambdaSecurityGroupId`: Security group for Lambda
- `VpcEndpointSecurityGroupId`: Security group for VPC endpoints

**Database Stack Outputs**:
- `ClusterEndpoint`: Aurora writer endpoint
- `ClusterReadEndpoint`: Aurora reader endpoint
- `SecretArn`: Secrets Manager secret ARN for database credentials
- `ClusterId`: Aurora cluster identifier (for monitoring)

**Cache Stack Outputs**:
- `CacheEndpoint`: ElastiCache cluster endpoint
- `SecretArn`: Secrets Manager secret ARN for Redis connection string

**Auth Stack Outputs**:
- `UserPoolId`: Cognito User Pool ID
- `ClientId`: Cognito User Pool Client ID

**Compute Stack Outputs**:
- `LoadBalancerDnsName`: ALB DNS name (for client access)
- `LoadBalancerArn`: ALB ARN (for monitoring)
- `EcsClusterName`: ECS cluster name
- `EcsServiceName`: ECS service name (for monitoring)
- `TaskRoleArn`: ECS task IAM role ARN

**Worker Stack Outputs**:
- `QueueUrl`: SQS queue URL (for ECS to enqueue messages)
- `QueueArn`: SQS queue ARN (for IAM policies)
- `DlqUrl`: Dead letter queue URL
- `LambdaFunctionName`: Lambda function name (for monitoring)

**Observability Stack Outputs**:
- `OperationalDashboardUrl`: CloudWatch dashboard URL
- `BusinessDashboardUrl`: CloudWatch dashboard URL
- `CriticalAlertsTopicArn`: SNS topic ARN for critical alerts
- `WarningAlertsTopicArn`: SNS topic ARN for warning alerts

**CI/CD Stack Outputs**:
- `GitHubActionsRoleArn`: IAM role ARN for GitHub Actions

---

## Runtime Dependencies (Service Communication)

Runtime dependencies describe how components interact during application execution.

### Runtime Communication Patterns

#### 1. Client → ECS Fargate (Web Tier)

**Flow**: HTTP client → ALB → ECS tasks

**Protocol**: HTTPS (TLS 1.2+)

**Components**:
- **Client**: Web browser or API consumer
- **ALB**: Application Load Balancer (public subnets)
- **ECS Tasks**: Actix-web application (private subnets)

**Communication**:
1. Client sends HTTPS request to ALB DNS name
2. ALB terminates TLS, forwards HTTP request to ECS task
3. ECS task processes request, returns HTTP response
4. ALB forwards response to client

**Security**:
- ALB listens on port 443 (HTTPS) with ACM certificate
- ALB security group allows inbound from 0.0.0.0/0 on port 443
- ECS security group allows inbound from ALB security group on port 8000

---

#### 2. ECS Fargate → Aurora PostgreSQL

**Flow**: ECS tasks → Aurora cluster

**Protocol**: PostgreSQL wire protocol over TLS (port 5432)

**Components**:
- **ECS Tasks**: Application code (SQLx client)
- **Aurora Cluster**: Writer endpoint (for reads/writes) or reader endpoint (for reads)

**Communication**:
1. ECS task initializes SQLx connection pool at startup
2. Application code executes queries via connection pool
3. SQLx sends queries to Aurora over TLS connection
4. Aurora returns results

**Security**:
- ECS security group allows outbound to Aurora security group on port 5432
- Aurora security group allows inbound from ECS security group on port 5432
- TLS enforced by Aurora parameter group (`rds.force_ssl = 1`)
- Credentials retrieved from Secrets Manager at startup

**Connection Pooling**:
- Min connections: 5
- Max connections: 20
- Idle timeout: 600 seconds

---

#### 3. ECS Fargate → ElastiCache Serverless

**Flow**: ECS tasks → ElastiCache cluster

**Protocol**: Redis RESP protocol over TLS (port 6379)

**Components**:
- **ECS Tasks**: Session middleware (actix-session with Redis backend)
- **ElastiCache Cluster**: Serverless Redis cluster

**Communication**:
1. ECS task initializes Redis client at startup
2. Session middleware reads/writes session data to Redis
3. Redis client sends commands to ElastiCache over TLS connection
4. ElastiCache returns results

**Security**:
- ECS security group allows outbound to ElastiCache security group on port 6379
- ElastiCache security group allows inbound from ECS security group on port 6379
- TLS in-transit encryption enabled (`rediss://` protocol)

**Session Data**:
- Session ID stored in HTTP-only cookie
- Session data (user_id, flash messages) stored in Redis
- Session TTL: 1 hour

---

#### 4. ECS Fargate → SQS

**Flow**: ECS tasks → SQS queue

**Protocol**: HTTPS (AWS SDK) via VPC endpoint

**Components**:
- **ECS Tasks**: Newsletter publish route
- **SQS Queue**: Newsletter delivery task queue

**Communication**:
1. Newsletter publish endpoint batches delivery tasks
2. ECS task calls `sqs:SendMessageBatch` (10 messages per call)
3. SQS stores messages in queue
4. Lambda is triggered by new messages

**Security**:
- ECS task IAM role granted `sqs:SendMessage` on newsletter queue
- VPC endpoint for SQS (no internet egress)
- Messages encrypted at rest (SQS managed key)

**Message Format**:
```json
{
  "newsletter_issue_id": "550e8400-e29b-41d4-a716-446655440000",
  "subscriber_email": "user@example.com"
}
```

---

#### 5. SQS → Lambda

**Flow**: SQS queue → Lambda function (event-driven trigger)

**Protocol**: Lambda polling (internal AWS integration)

**Components**:
- **SQS Queue**: Newsletter delivery task queue
- **Lambda Function**: Email sender function

**Communication**:
1. Lambda service polls SQS queue for new messages
2. Lambda invokes function with batch of messages (up to 10)
3. Lambda function processes each message (fetch newsletter, send email)
4. Lambda returns success (SQS deletes messages) or error (SQS retries)

**Configuration**:
- Batch size: 10 messages per invocation
- Max batching window: 5 seconds
- Visibility timeout: 300 seconds (5 minutes)
- Max receives: 3 (then move to DLQ)

**Error Handling**:
- Partial batch failure: SQS retries failed messages
- Permanent failure (after 3 retries): Move to dead letter queue

---

#### 6. Lambda → Aurora PostgreSQL

**Flow**: Lambda function → Aurora cluster

**Protocol**: PostgreSQL wire protocol over TLS (port 5432)

**Components**:
- **Lambda Function**: Email sender function
- **Aurora Cluster**: Reader endpoint (read-only queries)

**Communication**:
1. Lambda function initializes SQLx connection pool at startup (cold start)
2. Lambda handler queries newsletter content from Aurora
3. SQLx sends query to Aurora over TLS connection
4. Aurora returns newsletter content

**Security**:
- Lambda security group allows outbound to Aurora security group on port 5432
- Aurora security group allows inbound from Lambda security group on port 5432
- TLS enforced by Aurora parameter group
- Lambda execution role granted read-only access to database

**Connection Pooling**:
- Max connections: 5 (lower than ECS due to Lambda concurrency limit)
- Connection reused across invocations (warm Lambda container)

---

#### 7. Lambda → SES

**Flow**: Lambda function → SES service

**Protocol**: HTTPS (AWS SDK) via VPC endpoint

**Components**:
- **Lambda Function**: Email sender function
- **SES**: Simple Email Service

**Communication**:
1. Lambda function builds SES SendEmail request
2. Lambda calls `ses:SendEmail` API
3. SES queues email for delivery
4. SES returns success or error

**Security**:
- Lambda execution role granted `ses:SendEmail` on verified sender identity
- VPC endpoint for SES (no internet egress)

**Error Handling**:
- Throttling: Return error (SQS retries with exponential backoff)
- Bounce: Return error (moves to DLQ after 3 retries)
- Invalid recipient: Return error (moves to DLQ after 3 retries)

---

#### 8. ECS Fargate ↔ Cognito

**Flow**: ECS tasks ↔ Cognito User Pools

**Protocol**: HTTPS (AWS SDK) for authentication, local JWT validation for protected routes

**Components**:
- **ECS Tasks**: Login route, authentication middleware
- **Cognito User Pools**: Admin user authentication

**Communication**:

**Login Flow**:
1. User submits username/password to login endpoint
2. ECS task calls Cognito `InitiateAuth` API
3. Cognito validates credentials, returns JWT tokens
4. ECS task stores tokens in Redis session
5. Client redirected to admin dashboard

**Protected Route Flow**:
1. Client sends request with Bearer token (from session)
2. Authentication middleware extracts token from Authorization header
3. Middleware validates JWT signature using cached JWKS (no API call)
4. Middleware extracts user_id from `sub` claim
5. Request proceeds to route handler

**Security**:
- ECS task IAM role granted `cognito-idp:InitiateAuth`
- JWT tokens signed with RS256 (asymmetric keys)
- JWKS cached in memory, refreshed every 1 hour

---

#### 9. ECS Fargate → Secrets Manager

**Flow**: ECS tasks → Secrets Manager

**Protocol**: HTTPS (AWS SDK) via VPC endpoint

**Components**:
- **ECS Tasks**: Configuration module
- **Secrets Manager**: Database credentials, Redis connection string, HMAC secret

**Communication**:
1. ECS task starts, configuration module retrieves secrets at startup
2. Configuration calls `secretsmanager:GetSecretValue` for each secret
3. Secrets Manager returns secret values
4. Configuration parses secrets and caches in memory

**Security**:
- ECS task IAM role granted `secretsmanager:GetSecretValue` on specific secrets
- VPC endpoint for Secrets Manager (no internet egress)
- Secrets encrypted at rest (KMS)

**Caching Strategy**:
- Secrets cached in memory at startup
- Optional: Refresh every 5 minutes for rotation support

---

#### 10. Observability → All Services

**Flow**: CloudWatch and X-Ray collect metrics, logs, and traces from all services

**Protocol**: HTTPS (AWS SDK) via VPC endpoints

**Components**:
- **CloudWatch Logs**: ECS tasks, Lambda functions
- **CloudWatch Metrics**: ALB, ECS, Aurora, ElastiCache, SQS, Lambda
- **X-Ray**: Distributed tracing (ECS → Aurora, Lambda → SES)

**Communication**:
- ECS tasks write logs to CloudWatch Logs (via VPC endpoint)
- Lambda functions write logs to CloudWatch Logs (automatic)
- X-Ray daemon (ECS sidecar) sends trace segments to X-Ray service
- Lambda X-Ray active tracing sends trace segments automatically

**Metrics Collected**:
- ALB: Request count, target response time, HTTP 4xx/5xx errors
- ECS: CPU utilization, memory utilization, task count
- Aurora: Database connections, read/write latency, storage
- ElastiCache: Cache hit rate, evictions, connections
- SQS: Queue depth, message age, messages sent/received
- Lambda: Invocations, errors, duration, concurrent executions

---

## Component Interaction Diagrams

### Newsletter Publishing Flow (End-to-End)

```mermaid
sequenceDiagram
    participant Admin
    participant ALB
    participant ECS
    participant Aurora
    participant SQS
    participant Lambda
    participant SES
    participant Subscriber
    
    Admin->>ALB: POST /admin/newsletters (HTTPS)
    ALB->>ECS: Forward request (HTTP)
    ECS->>ECS: Validate JWT token (Cognito)
    ECS->>Aurora: Check idempotency key
    Aurora-->>ECS: No previous submission
    ECS->>Aurora: Begin transaction
    ECS->>Aurora: Insert newsletter issue
    ECS->>Aurora: Fetch confirmed subscribers
    Aurora-->>ECS: List of subscriber emails
    ECS->>Aurora: Commit transaction
    ECS->>SQS: Batch send messages (10 per call)
    SQS-->>ECS: Messages enqueued
    ECS->>Aurora: Save idempotent response
    ECS-->>ALB: 303 See Other
    ALB-->>Admin: Redirect to /admin/newsletters
    
    Note over SQS,Lambda: Async processing (event-driven)
    
    SQS->>Lambda: Trigger with batch (10 messages)
    Lambda->>Aurora: Fetch newsletter content
    Aurora-->>Lambda: Title, text, html
    Lambda->>SES: Send email
    SES-->>Lambda: Success
    Lambda-->>SQS: Delete message (success)
    SQS->>Lambda: Trigger next batch
    Lambda->>Aurora: Fetch newsletter content
    Lambda->>SES: Send email
    SES->>Subscriber: Deliver email
```

### Subscription Confirmation Flow

```mermaid
sequenceDiagram
    participant User
    participant ALB
    participant ECS
    participant Aurora
    participant SES
    participant Email
    
    User->>ALB: POST /subscriptions (HTTPS)
    ALB->>ECS: Forward request (HTTP)
    ECS->>ECS: Validate email format
    ECS->>Aurora: Begin transaction
    ECS->>Aurora: Insert subscriber (pending)
    ECS->>Aurora: Insert confirmation token
    Aurora-->>ECS: Transaction committed
    ECS->>SES: Send confirmation email
    SES-->>Email: Deliver email
    ECS-->>ALB: 200 OK
    ALB-->>User: Success page
    
    Note over User,Email: User receives confirmation email
    
    User->>Email: Click confirmation link
    Email->>ALB: GET /subscriptions/confirm?token=...
    ALB->>ECS: Forward request
    ECS->>Aurora: Begin transaction
    ECS->>Aurora: Fetch subscriber_id by token
    Aurora-->>ECS: Subscriber ID
    ECS->>Aurora: Update status to 'confirmed'
    ECS->>Aurora: Delete confirmation token
    Aurora-->>ECS: Transaction committed
    ECS-->>ALB: 200 OK
    ALB-->>User: Confirmation success page
```

### Authentication Flow (Cognito)

```mermaid
sequenceDiagram
    participant Admin
    participant ALB
    participant ECS
    participant Cognito
    participant ElastiCache
    
    Admin->>ALB: POST /login (HTTPS)
    ALB->>ECS: Forward request (HTTP)
    ECS->>Cognito: InitiateAuth (USERNAME, PASSWORD)
    Cognito-->>ECS: Access Token, ID Token, Refresh Token
    ECS->>ECS: Extract user_id from ID Token (sub claim)
    ECS->>ElastiCache: Store tokens in session
    ElastiCache-->>ECS: Session stored
    ECS-->>ALB: 303 See Other (redirect to /admin/dashboard)
    ALB-->>Admin: Set-Cookie: sessionid=...
    
    Note over Admin,ECS: Admin accesses protected route
    
    Admin->>ALB: GET /admin/dashboard (HTTPS)
    ALB->>ECS: Forward request with sessionid cookie
    ECS->>ElastiCache: Fetch session data
    ElastiCache-->>ECS: Access Token
    ECS->>ECS: Validate JWT token (local, using JWKS)
    ECS->>ECS: Extract user_id from sub claim
    ECS->>Aurora: Fetch dashboard data
    Aurora-->>ECS: Dashboard content
    ECS-->>ALB: 200 OK (dashboard HTML)
    ALB-->>Admin: Dashboard page
```

---

## Deployment Dependency Graph (CDK)

```mermaid
graph TD
    Network[Network Stack]
    Database[Database Stack]
    Cache[Cache Stack]
    Auth[Auth Stack]
    Compute[Compute Stack]
    Worker[Worker Stack]
    Observability[Observability Stack]
    CICD[CI/CD Stack]
    
    Network --> Database
    Network --> Cache
    Network --> Worker
    Database --> Compute
    Cache --> Compute
    Database --> Worker
    Compute --> Observability
    Worker --> Observability
    Database --> Observability
    Cache --> Observability
    
    style Network fill:#1976D2,stroke:#0D47A1,stroke-width:3px,color:#fff
    style Database fill:#388E3C,stroke:#1B5E20,stroke-width:3px,color:#fff
    style Cache fill:#F57C00,stroke:#E65100,stroke-width:3px,color:#fff
    style Auth fill:#00796B,stroke:#004D40,stroke-width:3px,color:#fff
    style Compute fill:#7B1FA2,stroke:#4A148C,stroke-width:3px,color:#fff
    style Worker fill:#C62828,stroke:#B71C1C,stroke-width:3px,color:#fff
    style Observability fill:#FBC02D,stroke:#F57F17,stroke-width:3px,color:#000
    style CICD fill:#616161,stroke:#212121,stroke-width:3px,color:#fff
```

---

## Runtime Dependency Graph (Service Communication)

```mermaid
graph LR
    subgraph External
        Client[HTTP Clients]
        Subscriber[Email Subscribers]
    end
    
    subgraph AWS Services
        ALB[Application Load Balancer]
        ECS[ECS Fargate Tasks]
        Aurora[Aurora PostgreSQL]
        ElastiCache[ElastiCache Serverless]
        SQS[SQS Queue]
        Lambda[Lambda Function]
        SES[Amazon SES]
        Cognito[Cognito User Pools]
        Secrets[Secrets Manager]
        CloudWatch[CloudWatch]
        XRay[X-Ray]
    end
    
    Client -->|HTTPS| ALB
    ALB -->|HTTP| ECS
    ECS -->|PostgreSQL/TLS| Aurora
    ECS -->|Redis/TLS| ElastiCache
    ECS -->|HTTPS| SQS
    ECS -->|HTTPS| Cognito
    ECS -->|HTTPS| Secrets
    ECS -->|Logs| CloudWatch
    ECS -->|Traces| XRay
    
    SQS -->|Event Trigger| Lambda
    Lambda -->|PostgreSQL/TLS| Aurora
    Lambda -->|HTTPS| SES
    Lambda -->|Logs| CloudWatch
    Lambda -->|Traces| XRay
    
    SES -->|Email| Subscriber
    
    style Client fill:#E0E0E0,stroke:#424242,stroke-width:2px,color:#000
    style Subscriber fill:#E0E0E0,stroke:#424242,stroke-width:2px,color:#000
    style ALB fill:#1976D2,stroke:#0D47A1,stroke-width:3px,color:#fff
    style ECS fill:#7B1FA2,stroke:#4A148C,stroke-width:3px,color:#fff
    style Aurora fill:#388E3C,stroke:#1B5E20,stroke-width:3px,color:#fff
    style ElastiCache fill:#F57C00,stroke:#E65100,stroke-width:3px,color:#fff
    style SQS fill:#C62828,stroke:#B71C1C,stroke-width:3px,color:#fff
    style Lambda fill:#FF6F00,stroke:#E65100,stroke-width:3px,color:#fff
    style SES fill:#00838F,stroke:#006064,stroke-width:3px,color:#fff
    style Cognito fill:#00796B,stroke:#004D40,stroke-width:3px,color:#fff
    style Secrets fill:#5E35B1,stroke:#4527A0,stroke-width:3px,color:#fff
    style CloudWatch fill:#FBC02D,stroke:#F57F17,stroke-width:3px,color:#000
    style XRay fill:#43A047,stroke:#2E7D32,stroke-width:3px,color:#fff
```

---

## Dependency Summary Tables

### Infrastructure Component Dependencies

| Component | Deploy After | Reason |
|-----------|--------------|--------|
| Network Stack | None | Foundation for all networking |
| Database Stack | Network | Requires VPC, subnets, security groups |
| Cache Stack | Network | Requires VPC, subnets, security groups |
| Auth Stack | None | Independent (no VPC integration) |
| Compute Stack | Network, Database, Cache | Requires VPC, database secret, cache secret |
| Worker Stack | Network, Database | Requires VPC, Lambda security group, database secret |
| Observability Stack | Compute, Worker, Database, Cache | Monitors deployed resources |
| CI/CD Stack | None | Independent (deployment pipeline) |

### Application Component Dependencies

| Component | Depends On | Provides To |
|-----------|-----------|-------------|
| Configuration Module | Secrets Manager | All application modules |
| Startup Module | Configuration, Database, Cache, Cognito | Application runtime |
| Email Client Module | SES | Routes module |
| Authentication Module | Cognito | Routes module (middleware) |
| Routes Module | Database, Email Client, SQS, Cognito, Authentication | HTTP responses |
| Domain Module | None | Routes module (validation) |
| Lambda Handler | Aurora, SES | (Triggered by SQS) |

### AWS Service Integration Dependencies

| Source | Target | Protocol | Purpose |
|--------|--------|----------|---------|
| Client | ALB | HTTPS | Public HTTP access |
| ALB | ECS | HTTP | Load balancing |
| ECS | Aurora | PostgreSQL/TLS | Database queries |
| ECS | ElastiCache | Redis/TLS | Session storage |
| ECS | SQS | HTTPS (SDK) | Enqueue email tasks |
| ECS | Cognito | HTTPS (SDK) | User authentication |
| ECS | Secrets Manager | HTTPS (SDK) | Retrieve secrets |
| SQS | Lambda | Event Trigger | Process email tasks |
| Lambda | Aurora | PostgreSQL/TLS | Fetch newsletter content |
| Lambda | SES | HTTPS (SDK) | Send emails |
| ECS/Lambda | CloudWatch | HTTPS (SDK) | Logs and metrics |
| ECS/Lambda | X-Ray | HTTPS (SDK) | Distributed tracing |

---

## Communication Patterns Summary

### Synchronous Communication
- **Client → ALB → ECS**: HTTP request/response (user-facing)
- **ECS → Aurora**: Database queries (transactional)
- **ECS → ElastiCache**: Cache reads/writes (session management)
- **ECS → Cognito**: Authentication (login flow)
- **Lambda → Aurora**: Database queries (read-only)
- **Lambda → SES**: Email sending

### Asynchronous Communication
- **ECS → SQS → Lambda**: Email delivery (event-driven)
- **SES → Subscriber**: Email delivery (fire-and-forget)

### Configuration and Secrets
- **ECS → Secrets Manager**: One-time retrieval at startup
- **Lambda → Secrets Manager**: One-time retrieval at cold start

### Observability
- **All Services → CloudWatch**: Continuous log streaming
- **All Services → X-Ray**: Trace segment emission (5% sampling)

---

## Failure Impact Analysis

### Critical Dependencies (Single Point of Failure)

1. **Network Stack Failure**:
   - **Impact**: ALL services inaccessible (no VPC networking)
   - **Mitigation**: Multi-AZ deployment, automated failover

2. **Aurora Failure**:
   - **Impact**: Web tier cannot process requests (no data access), Lambda cannot fetch newsletter content
   - **Mitigation**: Multi-AZ with automatic failover (< 30 seconds), cross-region read replica for DR

3. **ALB Failure**:
   - **Impact**: No public access to web tier
   - **Mitigation**: Multi-AZ deployment, Route 53 health checks, cross-region failover

### Non-Critical Dependencies (Graceful Degradation)

1. **ElastiCache Failure**:
   - **Impact**: Session storage unavailable, users logged out
   - **Mitigation**: Fall back to in-memory sessions (single-node state), auto-scaling repair

2. **SQS Failure**:
   - **Impact**: Newsletter publishing fails (cannot enqueue tasks)
   - **Mitigation**: Retry logic, SQS is highly available (99.99% SLA), DLQ for failed messages

3. **Lambda Failure**:
   - **Impact**: Email delivery delayed (messages remain in SQS)
   - **Mitigation**: SQS retries with exponential backoff, Lambda auto-scales on recovery

4. **SES Failure**:
   - **Impact**: Emails not delivered (Lambda returns error)
   - **Mitigation**: SQS retries failed messages, DLQ for permanent failures

5. **Cognito Failure**:
   - **Impact**: New admin logins fail (existing sessions still valid)
   - **Mitigation**: JWT validation continues to work (JWKS cached), Cognito highly available

---

## Security Boundaries

### Network Security Boundaries

1. **Public Subnet** (Internet-facing):
   - ALB only
   - Accepts traffic from 0.0.0.0/0 on port 443

2. **Private Subnet** (No internet access):
   - ECS tasks, Lambda functions, Aurora, ElastiCache
   - All AWS service access via VPC endpoints

3. **Security Group Isolation**:
   - Each service has dedicated security group
   - Least-privilege rules (only necessary ports/protocols)
   - No direct internet access from private resources

### IAM Boundaries

1. **ECS Task Role** (Application permissions):
   - Read secrets (database, Redis, HMAC)
   - Send SQS messages (newsletter queue)
   - Send SES emails (confirmation emails only)
   - Authenticate with Cognito
   - Write X-Ray traces

2. **Lambda Execution Role** (Worker permissions):
   - Read secrets (database)
   - Receive/delete SQS messages
   - Send SES emails (newsletter emails only)
   - Connect to VPC (ENI creation)
   - Write X-Ray traces

3. **GitHub Actions Role** (Deployment permissions):
   - CloudFormation (CDK deployments)
   - ECR (Docker image push)
   - ECS (service updates)
   - Lambda (function updates)
   - IAM (PassRole for task/execution roles)

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-12  
**Status**: Ready for Review
