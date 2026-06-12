# Unit of Work Definition

## Overview

This document defines the 8 implementation units for the AWS modernization of zero2prod newsletter service. Each unit represents a cohesive set of infrastructure and/or application changes that can be developed, tested, and deployed as a logical unit of work.

**Total Units**: 8  
**Execution Model**: Sequential with parallelization opportunities  
**Total Timeline**: 12 weeks (Phases 1-3: Weeks 1-10, Phase 4: Weeks 11-12)

---

## Unit 1: Network Infrastructure (CDK)

### Purpose
Establish the foundational VPC networking infrastructure with private subnets and VPC endpoints to enable secure, private communication between AWS services without internet egress.

### Priority
**CRITICAL** - Foundation unit that all other infrastructure depends on

### Dependencies
**None** - This is the first unit that must be completed

### Scope

#### Infrastructure Components (CDK Stack)
- **VPC**: Single VPC with CIDR block (e.g., 10.0.0.0/16)
- **Subnets**: 
  - 2 Public Subnets (one per AZ) for ALB
  - 2 Private Subnets (one per AZ) for ECS, Lambda, Aurora, ElastiCache
- **VPC Endpoints** (Interface and Gateway):
  - com.amazonaws.region.s3 (Gateway endpoint for ECR image pulls)
  - com.amazonaws.region.ecr.api (Interface endpoint)
  - com.amazonaws.region.ecr.dkr (Interface endpoint)
  - com.amazonaws.region.logs (CloudWatch Logs)
  - com.amazonaws.region.secretsmanager
  - com.amazonaws.region.sts (IAM role assumption)
  - com.amazonaws.region.ses (email sending)
  - com.amazonaws.region.sqs (message queuing)
- **Security Groups**:
  - ALB Security Group (inbound 443 from 0.0.0.0/0, outbound to ECS)
  - ECS Security Group (inbound from ALB, outbound to Aurora/ElastiCache/VPC endpoints)
  - Aurora Security Group (inbound from ECS/Lambda on port 5432)
  - ElastiCache Security Group (inbound from ECS on port 6379)
  - Lambda Security Group (outbound to SQS/SES/Aurora via VPC endpoints)
  - VPC Endpoint Security Group (inbound from ECS/Lambda)
- **Route Tables**: Public and private route tables configured
- **Internet Gateway**: For public subnets only
- **No NAT Gateway**: All AWS service access via VPC endpoints (cost optimization + security)

#### AWS Services Used
- Amazon VPC
- VPC Endpoints (Gateway and Interface)
- Security Groups
- Route Tables
- Internet Gateway

#### Deliverables
1. **CDK Stack**: `network_stack.py` with VPC, subnets, endpoints, security groups
2. **Stack Outputs**: VPC ID, subnet IDs, security group IDs for cross-stack references
3. **Documentation**: Network architecture diagram, security group rules table
4. **Validation**: Connectivity tests from private subnets to VPC endpoints

### Estimated Effort
**1 week** (5 business days)

### Requirements Mapped
- **NFR-3**: Security - Network Isolation (private subnets, VPC endpoints)
- **SECURITY-04**: Private networking and least-privilege IAM roles
- **NFR-14**: Operational Excellence - Infrastructure as Code (CDK)

### Success Criteria
- [ ] VPC created with public and private subnets across 2 AZs
- [ ] All 8 VPC endpoints deployed and accessible from private subnets
- [ ] Security groups defined with least-privilege rules
- [ ] CDK stack deploys without errors
- [ ] Network connectivity validated (bastion host test or Lambda test)

---

## Unit 2: Database Infrastructure (CDK + Migration)

### Purpose
Migrate the PostgreSQL database from self-hosted to Amazon Aurora PostgreSQL Serverless v2 with Multi-AZ high availability, encryption, and automated backups.

### Priority
**CRITICAL** - Application and worker tiers depend on database availability

### Dependencies
- **Unit 1**: Network Infrastructure (VPC, private subnets, security groups)

### Scope

#### Infrastructure Components (CDK Stack)
- **Aurora PostgreSQL Cluster**:
  - Engine: Aurora PostgreSQL (compatible with PostgreSQL 14+)
  - Deployment: Serverless v2 with auto-scaling (0.5 to 4 ACUs)
  - Multi-AZ: Primary in AZ-A, standby in AZ-B
  - Encryption: AWS KMS encryption at rest (AWS-managed key)
  - Backup: 7-day retention with automated backups
  - Parameter Group: Custom PostgreSQL settings (if needed)
  - TLS 1.2+ enforced for connections
- **Secrets Manager Secret**:
  - Database master password
  - Connection string with SSL parameters
  - Automatic rotation enabled (30 days)
- **Security**:
  - Deployed in private subnets (from Unit 1)
  - Security group allows inbound port 5432 from ECS and Lambda security groups only

#### Database Schema
- **Manual Schema Creation**: Execute DDL statements to recreate 6 tables
  1. `subscriptions` (id, email, name, subscribed_at, status)
  2. `subscription_tokens` (subscription_token, subscriber_id)
  3. `users` (user_id, username, password_hash) - Deprecated for auth, kept for audit
  4. `newsletter_issues` (newsletter_issue_id, title, text_content, html_content, published_at)
  5. `issue_delivery_queue` (deprecated, will be removed in Unit 5)
  6. `idempotency` (user_id, idempotency_key, response_status_code, response_headers, response_body, created_at)

#### Data Migration
1. Export data from source PostgreSQL database (pg_dump or logical replication)
2. Import data into Aurora cluster
3. Validate data integrity (row counts match, sample query validation)
4. Test SQLx connection from local development environment

#### AWS Services Used
- Amazon Aurora PostgreSQL Serverless v2
- AWS Secrets Manager
- AWS KMS (encryption key)

#### Deliverables
1. **CDK Stack**: `database_stack.py` with Aurora cluster, parameter groups, secrets
2. **Migration Scripts**: SQL DDL for schema creation, data import scripts
3. **Stack Outputs**: Aurora endpoint, secret ARN for cross-stack references
4. **Documentation**: Database schema diagram, migration runbook
5. **Validation**: Data integrity report, SQLx query compatibility tests

### Estimated Effort
**1 week** (5 business days)

### Requirements Mapped
- **FR-3**: Database Migration to Amazon Aurora PostgreSQL
- **NFR-1**: Reliability - High Availability (Multi-AZ)
- **NFR-4**: Security - Secrets Management (Secrets Manager)
- **NFR-5**: Security - Encryption (at rest and in transit)
- **SECURITY-01**: Encryption at rest and in transit
- **SECURITY-03**: Secrets in managed secret service

### Success Criteria
- [ ] Aurora PostgreSQL cluster deployed in private subnets with Multi-AZ
- [ ] All 6 tables created with correct schema
- [ ] Data migrated with zero data loss (row counts match)
- [ ] TLS 1.2+ connection validated from local development
- [ ] SQLx compile-time query validation passes
- [ ] Database password stored in Secrets Manager with automatic rotation

---

## Unit 3: Cache Infrastructure (CDK)

### Purpose
Deploy Amazon ElastiCache Serverless for Redis to replace external Redis for session storage with automatic scaling and Multi-AZ high availability.

### Priority
**CRITICAL** - Web application requires session storage for admin authentication

### Dependencies
- **Unit 1**: Network Infrastructure (VPC, private subnets, security groups)

### Scope

#### Infrastructure Components (CDK Stack)
- **ElastiCache Serverless for Redis**:
  - Deployment: Serverless with automatic scaling
  - Multi-AZ: Replication across 2 AZs for high availability
  - Encryption: At rest and in transit (TLS 1.2+)
  - Data Tiering: Enabled (automatically optimizes memory usage)
- **Secrets Manager Secret**:
  - Redis connection string (host:port)
  - TLS configuration parameters
- **Security**:
  - Deployed in private subnets (from Unit 1)
  - Security group allows inbound port 6379 from ECS security group only

#### Application Configuration
- Update `configuration.rs` to load `redis_uri` from Secrets Manager
- Connection string format: `rediss://cache-endpoint:6379` (note: `rediss://` for TLS)
- No data migration required (sessions are ephemeral)

#### AWS Services Used
- Amazon ElastiCache Serverless for Redis
- AWS Secrets Manager

#### Deliverables
1. **CDK Stack**: `cache_stack.py` with ElastiCache cluster, security group, secrets
2. **Stack Outputs**: ElastiCache endpoint, secret ARN for cross-stack references
3. **Configuration**: Application code update to load from Secrets Manager
4. **Documentation**: Cache architecture diagram, connection configuration guide
5. **Validation**: Session creation, retrieval, and expiration tests

### Estimated Effort
**3 days** (0.6 weeks)

### Requirements Mapped
- **FR-4**: Session Store Migration to ElastiCache Serverless
- **NFR-1**: Reliability - High Availability (Multi-AZ)
- **NFR-4**: Security - Secrets Management (Secrets Manager)
- **NFR-5**: Security - Encryption (at rest and in transit)
- **SECURITY-01**: Encryption at rest and in transit
- **SECURITY-03**: Secrets in managed secret service

### Success Criteria
- [ ] ElastiCache Serverless deployed in private subnets with Multi-AZ
- [ ] Encryption at rest and in transit enabled (TLS 1.2+)
- [ ] Connection string stored in Secrets Manager
- [ ] Application code updated to load redis_uri from Secrets Manager
- [ ] Session creation, retrieval, and expiration validated

---

## Unit 4: Compute Infrastructure (CDK + Application)

### Purpose
Deploy the zero2prod web application as a containerized service on ECS Fargate with Application Load Balancer, auto-scaling, and comprehensive observability.

### Priority
**CRITICAL** - Primary web application serving public and admin endpoints

### Dependencies
- **Unit 1**: Network Infrastructure (VPC, subnets, security groups)
- **Unit 2**: Database Infrastructure (Aurora PostgreSQL)
- **Unit 3**: Cache Infrastructure (ElastiCache Serverless)

### Scope

#### Infrastructure Components (CDK Stack)
- **Application Load Balancer (ALB)**:
  - Deployment: Public subnets across 2 AZs
  - Listeners: HTTPS (port 443) with ACM certificate, HTTP (port 80) redirects to HTTPS
  - Target Group: ECS tasks with health check on /health_check
  - Access Logging: Enabled to S3 bucket (SECURITY-02)
- **ECS Fargate Cluster**: Regional cluster for web tier
- **ECS Task Definition**:
  - Container: zero2prod web application
  - Image: ECR repository (built from Dockerfile)
  - CPU: 0.5 vCPU
  - Memory: 1 GB RAM
  - Environment Variables: Loaded from Secrets Manager (database, redis, HMAC secret)
  - Port Mapping: Container port 8000 → ALB target group
  - Logging: CloudWatch Logs with structured JSON (tracing-bunyan-formatter)
- **ECS Service**:
  - Launch Type: Fargate
  - Desired Count: 2 (Multi-AZ for HA)
  - Auto-Scaling: Target CPU 70%, min 2 tasks, max 10 tasks
  - Health Check Grace Period: 60 seconds
  - Deployment: Rolling update
- **ECR Repository**: Container registry for Docker images
- **IAM Roles**:
  - **Task Execution Role**: Permissions to pull ECR images, write CloudWatch logs, read Secrets Manager
  - **Task Role**: Permissions to read/write Aurora, ElastiCache, Secrets Manager (minimal)
- **CloudWatch Log Group**: Retention 30 days

#### Application Code Changes
- **Dockerfile**: Multi-stage build for Rust application
  - Stage 1: Build (cargo build --release)
  - Stage 2: Runtime (minimal image with compiled binary)
- **configuration.rs**: Update to load from Secrets Manager
  - Database password from Secrets Manager
  - Redis URI from Secrets Manager
  - HMAC secret from Secrets Manager
- **startup.rs**: Validate connections to Aurora and ElastiCache on startup
- **Health Check**: Ensure /health_check endpoint validates database connectivity

#### AWS Services Used
- Amazon ECS Fargate
- Application Load Balancer (ALB)
- Amazon ECR
- AWS IAM (roles and policies)
- AWS Secrets Manager
- Amazon CloudWatch Logs
- AWS Certificate Manager (ACM)
- Amazon S3 (ALB access logs)

#### Deliverables
1. **CDK Stack**: `compute_stack.py` with ALB, ECS cluster, service, task definition, IAM roles
2. **Dockerfile**: Multi-stage Docker build for Rust application
3. **Application Code**: Updated configuration.rs to load from Secrets Manager
4. **Stack Outputs**: ALB DNS name, ECS service ARN
5. **Documentation**: ECS architecture diagram, deployment guide, IAM policy documentation
6. **Validation**: All public and admin endpoints tested with < 200ms latency

### Estimated Effort
**1.5 weeks** (7-8 business days)

### Requirements Mapped
- **FR-1**: Web Application Deployment (ECS Fargate)
- **FR-7**: Public API Endpoints (all endpoints functional)
- **FR-8**: Admin API Endpoints (all endpoints functional)
- **NFR-1**: Reliability - High Availability (Multi-AZ, auto-scaling)
- **NFR-4**: Security - Secrets Management (Secrets Manager)
- **NFR-6**: Security - Access Logging (ALB logs to S3)
- **NFR-9**: Performance - API Latency (< 200ms p95)
- **NFR-11**: Scalability - Auto-Scaling (CPU-based)
- **SECURITY-02**: Access logging on network intermediaries

### Success Criteria
- [ ] ECS Fargate service running with 2 tasks across 2 AZs
- [ ] ALB routing traffic to ECS tasks with health checks passing
- [ ] All public endpoints functional (GET /, GET /health_check, POST /subscriptions, etc.)
- [ ] All admin endpoints functional with session-based auth (pre-Cognito)
- [ ] API latency < 200ms (p95)
- [ ] Auto-scaling tested (scale out on CPU > 70%, scale in on CPU < 50%)
- [ ] ALB access logs written to S3 bucket
- [ ] Application logs in CloudWatch Logs (structured JSON)

---

## Unit 5: Worker Infrastructure (CDK + Lambda + Application)

### Purpose
Replace the monolithic background worker with serverless event-driven architecture using SQS for message queuing and Lambda for email delivery processing.

### Priority
**CRITICAL** - Newsletter delivery functionality depends on worker tier

### Dependencies
- **Unit 1**: Network Infrastructure (VPC, private subnets, security groups)
- **Unit 2**: Database Infrastructure (Aurora PostgreSQL)

### Scope

#### Infrastructure Components (CDK Stack)
- **SQS Queue (Delivery Tasks)**:
  - Queue Type: Standard
  - Visibility Timeout: 5 minutes (Lambda execution time + buffer)
  - Message Retention: 4 days
  - Dead Letter Queue: Configured with max receive count = 3
  - Encryption: Server-side encryption (SSE-SQS)
- **SQS Dead Letter Queue (DLQ)**:
  - Captures messages that fail after 3 retry attempts
  - CloudWatch alarm when DLQ depth > 0
- **Lambda Function (Email Sender)**:
  - Runtime: Rust (cargo-lambda or Python with boto3)
  - Handler: Processes SQS batch messages (batch size = 10)
  - Environment: VPC-connected (private subnets)
  - Timeout: 5 minutes
  - Memory: 512 MB
  - Reserved Concurrency: 100 (aligned with SES sending rate)
  - Environment Variables: Aurora endpoint, SES region
  - Layers: AWS SDK for SES
- **Lambda Execution Role**:
  - Permissions: Read SQS, write CloudWatch Logs, read Aurora, send SES emails, read Secrets Manager
- **SES Configuration**:
  - Sender Identity: Domain or email verification
  - Production Access: Request quota increase (from sandbox 200/day)
  - Bounce/Complaint Handling: SNS topic (optional)

#### Application Code Changes
- **Newsletter Publish Endpoint** (`routes/admin/newsletter/post.rs`):
  - Remove database queue write (issue_delivery_queue table)
  - Add SQS batch send logic:
    1. Validate newsletter content
    2. Check idempotency
    3. Insert newsletter issue into Aurora
    4. Fetch confirmed subscribers from Aurora
    5. Write delivery tasks to SQS (one message per subscriber, batches of 10)
    6. Return 200 OK
  - Message format: `{"newsletter_issue_id": "uuid", "subscriber_email": "email@example.com"}`
- **Worker Code Removal**:
  - Delete `issue_delivery_worker.rs` (polling worker no longer needed)
  - Remove background worker task from main.rs
- **Lambda Handler Code** (Rust or Python):
  1. Receive SQS batch (up to 10 messages)
  2. Parse message: extract newsletter_issue_id and subscriber_email
  3. Query Aurora: Retrieve newsletter content by newsletter_issue_id
  4. Send email via SES: Use AWS SDK to send HTML email
  5. Error handling: Log errors, allow SQS retry on failure
  6. Return success: SQS deletes message
- **Database Migration**:
  - Mark `issue_delivery_queue` table as deprecated (can drop after validation)

#### AWS Services Used
- Amazon SQS (Standard Queue + DLQ)
- AWS Lambda
- Amazon SES
- AWS IAM (execution roles)
- AWS Secrets Manager (database credentials)
- Amazon CloudWatch Logs

#### Deliverables
1. **CDK Stack**: `worker_stack.py` with SQS queues, Lambda function, IAM roles, SES config
2. **Lambda Handler**: Rust or Python code to process SQS messages and send SES emails
3. **Application Code**: Updated `routes/admin/newsletter/post.rs` to write to SQS
4. **Application Code**: Removed `issue_delivery_worker.rs` and background worker task
5. **Stack Outputs**: SQS queue URL, Lambda function ARN
6. **Documentation**: Worker architecture diagram, SQS message format, Lambda handler logic
7. **Validation**: End-to-end newsletter publishing and email delivery test

### Estimated Effort
**1.5 weeks** (7-8 business days)

### Requirements Mapped
- **FR-2**: Background Email Delivery Worker (SQS + Lambda)
- **FR-5**: Email Service Migration to Amazon SES
- **FR-9**: Idempotency Preservation (newsletter publish endpoint)
- **NFR-7**: Observability - Monitoring and Tracing (CloudWatch metrics)
- **NFR-8**: Observability - Alerting (SQS DLQ alarm)
- **NFR-10**: Performance - Email Queueing (< 1 minute to queue all emails)
- **NFR-11**: Scalability - Auto-Scaling (Lambda scales automatically)

### Success Criteria
- [ ] SQS queue and DLQ deployed with encryption and proper timeouts
- [ ] Lambda function deployed in VPC with Aurora and SES access
- [ ] Newsletter publish endpoint writes delivery tasks to SQS (not database queue)
- [ ] Lambda processes SQS messages and sends emails via SES
- [ ] Failed deliveries retry 3x before moving to DLQ
- [ ] CloudWatch alarm triggers when DLQ depth > 0
- [ ] End-to-end test: Publish newsletter, validate emails delivered to subscribers
- [ ] Background worker code removed (issue_delivery_worker.rs deleted)

---

## Unit 6: Authentication Infrastructure (CDK + Application)

### Purpose
Modernize admin authentication from local password-based (Argon2) to AWS Cognito User Pools with JWT token-based authentication for improved security and scalability.

### Priority
**IMPORTANT** - Can be deployed after web tier is functional (not blocking initial deployment)

### Dependencies
- **Unit 1**: Network Infrastructure (VPC for Cognito integration)

### Scope

#### Infrastructure Components (CDK Stack)
- **Cognito User Pool**:
  - Username/Password Authentication
  - Password Policy: Minimum 8 characters, uppercase, lowercase, number, special character
  - Account Lockout: 5 failed attempts, 5-minute lockout
  - MFA: Optional (can be enabled per user)
  - Email Verification: Optional (admin users only, no self-registration)
- **Cognito User Pool Client**:
  - App Client for web application
  - OAuth 2.0 Flows: Authorization Code Grant
  - Allowed Callback URLs: https://alb-dns-name/admin/callback
- **User Migration**:
  - Migrate admin users from `users` table to Cognito
  - Username preserved, password reset required on first login
  - Migration script or manual creation via AWS CLI/Console

#### Application Code Changes
- **Login Endpoint** (`routes/login/post.rs`):
  - Replace Argon2 password verification with Cognito authentication
  - Call Cognito API: InitiateAuth with username/password
  - Receive Cognito JWT tokens (ID token, access token, refresh token)
  - Store ID token in session (replace password_hash check)
- **Session Middleware** (`session_state.rs`):
  - Update to validate Cognito JWT instead of database lookup
  - Decode JWT, verify signature (using Cognito public keys)
  - Extract user claims (sub as user_id, username)
  - Validate token expiration
- **Authentication Middleware** (`authentication/middleware.rs`):
  - Replace `get_username` with Cognito JWT validation
  - Extract username from JWT claims
- **Password Change** (`routes/admin/password/post.rs`):
  - Replace local password update with Cognito ChangePassword API call
- **Logout Endpoint** (`routes/admin/logout/post.rs`):
  - Invalidate session (existing logic preserved)
  - Optionally revoke Cognito tokens (global sign-out)
- **Database Schema**:
  - Mark `users` table as deprecated (keep for audit trail, not used for auth)

#### AWS Services Used
- Amazon Cognito User Pools
- AWS IAM (for Cognito API permissions)

#### Deliverables
1. **CDK Stack**: `auth_stack.py` with Cognito User Pool, app client
2. **Migration Script**: Migrate admin users from database to Cognito (Python/Bash)
3. **Application Code**: Updated login, session, and authentication logic for Cognito JWT
4. **Stack Outputs**: Cognito User Pool ID, app client ID
5. **Documentation**: Cognito integration guide, JWT validation logic, user migration runbook
6. **Validation**: Admin login flow, protected endpoint access, password change, logout

### Estimated Effort
**1 week** (5 business days)

### Requirements Mapped
- **FR-6**: Admin Authentication Migration to AWS Cognito
- **FR-8**: Admin API Endpoints (Cognito auth required)
- **NFR-15**: Maintainability - Code Quality (preserve strong type safety)

### Success Criteria
- [ ] Cognito User Pool deployed with password policies and account lockout
- [ ] Admin users migrated from database to Cognito
- [ ] Login endpoint authenticates via Cognito and returns JWT
- [ ] Session middleware validates Cognito JWT tokens
- [ ] All admin endpoints require valid Cognito JWT
- [ ] Password change endpoint uses Cognito ChangePassword API
- [ ] Logout endpoint invalidates session and optionally revokes tokens
- [ ] `users` table marked as deprecated (not used for authentication)

---

## Unit 7: Observability Infrastructure (CDK)

### Purpose
Deploy comprehensive observability with CloudWatch dashboards, alarms, X-Ray distributed tracing, and alerting for proactive monitoring and incident response.

### Priority
**IMPORTANT** - Observability enables operational excellence but not blocking for initial deployment

### Dependencies
- **Unit 4**: Compute Infrastructure (ECS tasks for metrics/logs)
- **Unit 5**: Worker Infrastructure (Lambda for metrics/logs)

### Scope

#### Infrastructure Components (CDK Stack)
- **CloudWatch Dashboards**:
  1. **Operational Dashboard**: Request rates, error rates, API latencies (p50, p95, p99)
  2. **Business Dashboard**: Subscriptions/hour, newsletters published, emails sent
  3. **Infrastructure Dashboard**: ECS CPU/memory, Aurora connections, Lambda invocations
- **CloudWatch Alarms**:
  1. **Service Down**: ALB target group 0 healthy targets → SNS critical alert
  2. **Database Failure**: Aurora cluster status != available → SNS critical alert
  3. **High Error Rate**: HTTP 5xx > 5% for 5 minutes → SNS critical alert
  4. **Lambda Errors**: Lambda error rate > 10% for 5 minutes → SNS warning alert
  5. **SQS DLQ Messages**: Messages in DLQ > 0 → SNS warning alert
- **SNS Topics**:
  - **Critical Alerts**: PagerDuty integration or email for oncall
  - **Warning Alerts**: Email to engineering team
- **X-Ray Tracing**:
  - ECS tasks: X-Ray daemon sidecar or AWS Distro for OpenTelemetry
  - Lambda: X-Ray tracing enabled (automatic instrumentation)
  - Sampling: 5% of requests (configurable)
- **ALB Access Logging**:
  - S3 bucket for ALB access logs (created in Unit 4, enhanced here)
  - Encryption at rest (SSE-S3)
  - Retention: 90 days

#### Application Code Changes (Optional)
- **X-Ray Middleware** (optional enhancement):
  - Integrate X-Ray SDK for Rust (if available)
  - Instrument HTTP handlers for request tracing
  - Add subsegments for database queries
- **Structured Logging** (already in place):
  - Preserve tracing-bunyan-formatter for JSON logs
  - Ensure log correlation with X-Ray trace IDs

#### AWS Services Used
- Amazon CloudWatch (Logs, Metrics, Alarms, Dashboards)
- AWS X-Ray
- Amazon SNS (alert notifications)
- Amazon S3 (ALB access logs)

#### Deliverables
1. **CDK Stack**: `observability_stack.py` with dashboards, alarms, SNS topics, X-Ray config
2. **CloudWatch Dashboards**: 3 dashboards (operational, business, infrastructure)
3. **Alarms**: 5 critical alarms with SNS integration
4. **Documentation**: Observability architecture, alarm runbooks, dashboard screenshots
5. **Validation**: Simulate failure scenarios, verify alarms trigger

### Estimated Effort
**1 week** (5 business days)

### Requirements Mapped
- **NFR-6**: Security - Access Logging (ALB logs to S3)
- **NFR-7**: Observability - Monitoring and Tracing (CloudWatch + X-Ray)
- **NFR-8**: Observability - Alerting (critical alarms)
- **SECURITY-02**: Access logging on network intermediaries

### Success Criteria
- [ ] CloudWatch dashboards display operational, business, and infrastructure metrics
- [ ] 5 CloudWatch alarms configured with SNS topics
- [ ] X-Ray tracing enabled for ECS tasks and Lambda functions
- [ ] ALB access logs written to S3 with encryption and 90-day retention
- [ ] Simulate failure (stop ECS task), verify "Service Down" alarm triggers
- [ ] Service map in X-Ray console shows dependencies (ALB → ECS → Aurora)

---

## Unit 8: CI/CD Infrastructure (GitHub Actions + CDK)

### Purpose
Automate build, test, package, and deployment workflows using GitHub Actions with secure AWS OIDC authentication for zero long-lived credentials.

### Priority
**IMPORTANT** - Deployment automation improves operational efficiency but not blocking for initial deployment

### Dependencies
- **Unit 4**: Compute Infrastructure (ECS service, ECR repository)
- **Unit 5**: Worker Infrastructure (Lambda function)

### Scope

#### Infrastructure Components (CDK Stack)
- **AWS OIDC Provider for GitHub Actions**:
  - Identity Provider: GitHub Actions OIDC
  - Audience: sts.amazonaws.com
- **IAM Role for GitHub Actions**:
  - Trust Policy: Allow GitHub Actions from specific repository
  - Permissions: ECR push, ECS update service, Lambda update function, CDK deploy (CloudFormation)
- **ECR Repository** (already created in Unit 4, referenced here):
  - Image scanning enabled (scan on push)
  - Lifecycle policy: Retain last 10 images

#### CI/CD Pipeline (GitHub Actions Workflow)
- **Workflow File**: `.github/workflows/deploy.yml`
- **Trigger**: Push to main branch (or manual workflow_dispatch)
- **Environments**: dev, staging, production (manual approval for production)

##### Pipeline Stages
1. **Build**:
   - Checkout code
   - Install Rust toolchain
   - Run `cargo build --release`
   - Run unit tests: `cargo test`
2. **Test**:
   - Run integration tests (requires test Aurora database or mock)
   - Run property-based tests (quickcheck)
3. **Package**:
   - Build Docker image (multi-stage Dockerfile)
   - Tag image: `{ecr-repo}:commit-sha` and `{ecr-repo}:latest`
   - Authenticate to ECR (OIDC role)
   - Push image to ECR
4. **Deploy Infrastructure** (if CDK changes detected):
   - Install AWS CDK CLI
   - Run `cdk diff` to preview changes
   - Run `cdk deploy --all --require-approval never`
5. **Deploy Application**:
   - Update ECS service with new task definition (new image tag)
   - Wait for ECS deployment to complete
   - Package Lambda function (if Lambda code changed)
   - Update Lambda function code
6. **Smoke Tests**:
   - Health check: `curl https://alb-dns/health_check`
   - Subscription test: POST to /subscriptions, validate response
   - Admin login test: POST to /login, validate session

##### Environment Configuration
- **Dev Environment**: Auto-deploy on push to main
- **Staging Environment**: Auto-deploy after dev success
- **Production Environment**: Manual approval gate

#### Rollback Strategy
- **ECS**: Revert to previous task definition via AWS console or CLI
- **Lambda**: Revert to previous version via AWS console or CLI
- **Database**: Restore from snapshot (last resort, tested in DR)

#### AWS Services Used
- AWS IAM (OIDC provider, roles)
- Amazon ECR (already in Unit 4)
- AWS CloudFormation (CDK-generated stacks)

#### Deliverables
1. **CDK Stack**: `cicd_stack.py` with OIDC provider, IAM role for GitHub Actions
2. **GitHub Actions Workflow**: `.github/workflows/deploy.yml` with 6 stages
3. **Documentation**: CI/CD pipeline architecture, deployment guide, rollback procedures
4. **Validation**: Push to main, verify automated deployment, test rollback

### Estimated Effort
**1 week** (5 business days)

### Requirements Mapped
- **NFR-13**: Operational Excellence - Deployment Automation (GitHub Actions)
- **NFR-14**: Operational Excellence - Infrastructure as Code (CDK)
- **NFR-15**: Maintainability - Code Quality (automated testing)

### Success Criteria
- [ ] OIDC provider configured for GitHub Actions (no long-lived AWS credentials)
- [ ] IAM role grants GitHub Actions permissions for ECR, ECS, Lambda, CloudFormation
- [ ] GitHub Actions workflow deploys to dev environment on push to main
- [ ] ECS service updated with new Docker image automatically
- [ ] Lambda function updated with new code automatically
- [ ] Smoke tests pass after deployment (health check, subscription, login)
- [ ] Manual approval gate for production deployments
- [ ] Rollback procedure tested (revert ECS task definition)

---

## Unit Summary Table

| Unit | Name | Priority | Dependencies | Effort | Phase | AWS Services |
|------|------|----------|--------------|--------|-------|--------------|
| 1 | Network Infrastructure | CRITICAL | None | 1 week | Phase 1 | VPC, VPC Endpoints, Security Groups |
| 2 | Database Infrastructure | CRITICAL | Unit 1 | 1 week | Phase 1 | Aurora PostgreSQL, Secrets Manager, KMS |
| 3 | Cache Infrastructure | CRITICAL | Unit 1 | 3 days | Phase 1 | ElastiCache Serverless, Secrets Manager |
| 4 | Compute Infrastructure | CRITICAL | Units 1, 2, 3 | 1.5 weeks | Phase 2 | ECS Fargate, ALB, ECR, IAM, CloudWatch Logs, ACM, S3 |
| 5 | Worker Infrastructure | CRITICAL | Units 1, 2 | 1.5 weeks | Phase 2 | SQS, Lambda, SES, IAM, CloudWatch Logs |
| 6 | Authentication Infrastructure | IMPORTANT | Unit 1 | 1 week | Phase 3 | Cognito User Pools, IAM |
| 7 | Observability Infrastructure | IMPORTANT | Units 4, 5 | 1 week | Phase 3 | CloudWatch, X-Ray, SNS, S3 |
| 8 | CI/CD Infrastructure | IMPORTANT | Units 4, 5 | 1 week | Phase 3 | IAM (OIDC), CloudFormation |

**Total Effort**: 8.5 weeks (design + implementation)  
**Total Timeline**: 12 weeks (includes testing and validation in Weeks 11-12)

---

## Execution Phases

### Phase 1: Foundation (Weeks 1-2)
**Objective**: Establish networking, database, and cache infrastructure

**Units**:
1. Unit 1: Network Infrastructure (Week 1)
2. Unit 2: Database Infrastructure (Week 2)
3. Unit 3: Cache Infrastructure (Week 2, parallel with Unit 2)

**Parallelization**: Units 2 and 3 can be developed in parallel after Unit 1 completes

**Milestone**: Foundation infrastructure ready for web application deployment

---

### Phase 2: Application (Weeks 3-6)
**Objective**: Deploy web application and background worker

**Units**:
4. Unit 4: Compute Infrastructure (Weeks 3-4)
5. Unit 5: Worker Infrastructure (Weeks 5-6)

**Milestone**: Core application functionality operational (web tier + worker tier)

---

### Phase 3: Security & Operations (Weeks 7-10)
**Objective**: Enhance security, observability, and operational automation

**Units**:
6. Unit 6: Authentication Infrastructure (Week 7)
7. Unit 7: Observability Infrastructure (Week 8)
8. Unit 8: CI/CD Infrastructure (Week 9-10)

**Parallelization**: Units 6 and 7 can be developed in parallel after Unit 4 completes

**Milestone**: Production-ready system with comprehensive security, monitoring, and automation

---

### Phase 4: Testing & Validation (Weeks 11-12)
**Objective**: Comprehensive testing and production deployment

**Activities**:
- Integration testing across all units
- End-to-end user journey testing
- Security testing (OWASP Top 10, vulnerability scanning)
- Performance testing (load testing, latency validation)
- DR failover testing (cross-region)
- Production deployment
- Post-deployment monitoring (24-hour watch)

**Milestone**: Production deployment complete, all quality gates passed

---

## Notes

### Parallelization Opportunities
- **Units 2 & 3**: Both depend only on Unit 1, can be developed simultaneously
- **Units 6 & 7**: Can be developed in parallel after Unit 4 (Compute) is complete
- **Testing**: Can overlap with final unit development in Weeks 10-11

### Critical Path
Unit 1 → Unit 2 → Unit 4 → Unit 5 → Build & Test

This path represents the minimum sequence required to deploy the core application functionality.

### Risk Mitigation
- **Database Migration (Unit 2)**: Allocate extra time for manual schema creation and data validation
- **Lambda Cold Starts (Unit 5)**: Consider provisioned concurrency if email delivery latency is critical
- **Cognito Integration (Unit 6)**: Test thoroughly in staging before production migration
- **Timeline Pressure**: Prioritize critical path units (1, 2, 4, 5) to deliver MVP first

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-12  
**Status**: Ready for Review
