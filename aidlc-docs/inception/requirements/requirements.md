# AWS Modernization Requirements

## Intent Analysis Summary

**User Request**: "I would like to modernize this application to run on aws using the well architect design principles."

**Request Type**: Migration + Cloud-Native Modernization

**Scope**: System-wide architectural transformation
- Migrate from local/self-hosted deployment to AWS cloud infrastructure
- Re-architect monolithic application for cloud-native services
- Replace traditional background worker with serverless event-driven architecture
- Implement AWS Well-Architected Framework best practices
- Modernize authentication, observability, and operational practices

**Complexity**: Complex
- Multiple AWS service integrations (ECS, Lambda, Aurora, ElastiCache, SES, Cognito, Secrets Manager)
- Architectural paradigm shift from monolithic to distributed serverless components
- Database migration with manual schema redesign
- Security hardening with private networking and VPC endpoints
- Observability modernization with CloudWatch and X-Ray
- Infrastructure as Code with AWS CDK Python

**Timeline**: Standard (1-3 months)
- Full cloud-native re-architecture with proper integration and testing
- Phase 1 (Month 1): Infrastructure setup, database migration, ECS Fargate web tier
- Phase 2 (Month 2): SQS+Lambda worker, Cognito integration, observability stack
- Phase 3 (Month 3): Security hardening, performance optimization, DR testing

---

## Functional Requirements

### FR-1: Web Application Deployment
**Priority**: CRITICAL  
**Description**: Deploy the zero2prod web application (Actix-web) as a containerized service on AWS ECS Fargate.

**Acceptance Criteria**:
- Web application runs in ECS Fargate containers with no EC2 management
- Application serves all existing public and admin HTTP endpoints
- Auto-scaling configured based on CPU/memory utilization
- Health checks configured for container orchestration
- Application can handle concurrent requests with Tokio async runtime

**AWS Services**: ECS Fargate, Application Load Balancer, ECR

---

### FR-2: Background Email Delivery Worker
**Priority**: CRITICAL  
**Description**: Replace the monolithic background worker with serverless SQS + Lambda architecture for asynchronous email delivery.

**Acceptance Criteria**:
- Newsletter publishing endpoint writes delivery tasks to SQS queue (one message per subscriber)
- Lambda function triggered by SQS messages to process email delivery
- Lambda retrieves newsletter content from Aurora PostgreSQL
- Lambda sends email via Amazon SES
- Failed deliveries trigger automatic retries (SQS DLQ for permanent failures)
- No polling loops - fully event-driven architecture
- Queue depth visible in CloudWatch metrics

**AWS Services**: SQS, Lambda, SES

**Technical Notes**:
- SQS standard queue with visibility timeout = Lambda execution time + buffer
- Dead Letter Queue (DLQ) after 3 retry attempts
- Lambda concurrency limit aligned with SES sending quotas
- Batch size = 10 messages per Lambda invocation for efficiency

---

### FR-3: Database Migration to Amazon Aurora PostgreSQL
**Priority**: CRITICAL  
**Description**: Migrate from self-hosted PostgreSQL to Amazon Aurora PostgreSQL Serverless v2 with manual schema creation and data migration.

**Acceptance Criteria**:
- Aurora PostgreSQL cluster created with PostgreSQL-compatible engine
- All 6 existing tables migrated: subscriptions, subscription_tokens, users, newsletter_issues, issue_delivery_queue, idempotency
- Database schema manually recreated in Aurora (using existing SQLx migrations as reference)
- Data migrated from source PostgreSQL with zero data loss
- SQLx connection string updated to Aurora endpoint
- Multi-AZ deployment for high availability (99.9%)
- Automated backups with 7-day retention
- Encryption at rest enabled (SECURITY-01)
- TLS 1.2+ enforced for all connections (SECURITY-01)

**AWS Services**: Amazon Aurora PostgreSQL Serverless v2

**Migration Strategy**:
1. Create Aurora cluster in AWS
2. Manually execute DDL statements to create schema
3. Export data from source PostgreSQL (pg_dump or logical replication)
4. Import data into Aurora
5. Validate data integrity (row counts, checksums)
6. Update application configuration
7. Cutover with brief maintenance window

---

### FR-4: Session Store Migration to ElastiCache Serverless
**Priority**: HIGH  
**Description**: Migrate Redis session storage from self-hosted/external Redis to Amazon ElastiCache Serverless for Redis.

**Acceptance Criteria**:
- ElastiCache Serverless for Redis cluster created
- Automatic scaling based on workload
- Session middleware (actix-session) configured with ElastiCache endpoint
- Session data compatible with existing session structure
- Encryption in transit enabled (TLS 1.2+) (SECURITY-01)
- Encryption at rest enabled (SECURITY-01)
- Multi-AZ deployment for high availability

**AWS Services**: Amazon ElastiCache Serverless for Redis

**Migration Notes**:
- No data migration required (sessions are ephemeral)
- Update redis_uri configuration to ElastiCache endpoint
- Test session creation, retrieval, and expiration

---

### FR-5: Email Service Migration to Amazon SES
**Priority**: HIGH  
**Description**: Replace Postmark email service integration with Amazon SES for both transactional (confirmation) and bulk (newsletter) emails.

**Acceptance Criteria**:
- SES identity verified for sender email domain
- Email client code updated to use SES API instead of Postmark
- Confirmation emails sent via SES with < 1 second delivery to SES queue
- Newsletter emails queued via SQS and sent via Lambda + SES
- Bounce and complaint handling configured (SNS notifications)
- SES sending quotas increased if needed (default: 200 emails/day sandbox)
- Production access requested and approved (if > 50K emails/day)

**AWS Services**: Amazon SES, SNS (for bounce notifications)

**Email Client Changes**:
- Replace Postmark SDK with AWS SDK for Rust (aws-sdk-sesv2)
- Update SendEmailRequest structure to SES format
- Remove X-Postmark-Server-Token header
- Add AWS SigV4 signing for SES API requests

**Performance Requirement**:
- Emails queued within 1 minute of user action (FR-2 clarification)
- Actual delivery time depends on subscriber volume
- SES sending rate: Up to 14 emails/second (configurable)

---

### FR-6: Admin Authentication Migration to AWS Cognito
**Priority**: MEDIUM  
**Description**: Replace local password-based authentication with AWS Cognito user pools for admin user management.

**Acceptance Criteria**:
- Cognito User Pool created with username/password authentication
- Existing admin users migrated to Cognito (password reset required)
- Login flow uses Cognito authentication
- Session management updated to use Cognito tokens (JWT)
- Password policies enforced via Cognito (Argon2 hashing replaced by Cognito's secure hashing)
- MFA optional (can be enabled per user)
- Admin dashboard accessible only with valid Cognito JWT

**AWS Services**: Amazon Cognito User Pools

**Migration Path**:
1. Create Cognito User Pool
2. Migrate admin users (usernames only, passwords reset on first login)
3. Update /login endpoint to authenticate via Cognito
4. Replace password verification logic with Cognito SDK calls
5. Update session middleware to validate Cognito JWT tokens
6. Remove users table from Aurora (keep for audit trail, mark as deprecated)

**Security Enhancement**:
- Cognito enforces password complexity rules
- Account lockout after failed login attempts
- Token-based authentication (stateless, more scalable)

---

### FR-7: Public API Endpoints
**Priority**: CRITICAL  
**Description**: All existing public endpoints must remain functional after migration.

**Endpoints**:
1. `GET /` - Home page
2. `GET /health_check` - Health monitoring
3. `POST /subscriptions` - Newsletter subscription (form data: name, email)
4. `GET /subscriptions/confirm` - Email confirmation (query: subscription_token)
5. `GET /login` - Login form
6. `POST /login` - Login submission (form data: username, password) [Modified for Cognito]

**Performance**: API response time < 200ms (p95)

---

### FR-8: Admin API Endpoints
**Priority**: CRITICAL  
**Description**: All existing admin endpoints must remain functional after migration with Cognito authentication.

**Endpoints**:
1. `GET /admin/dashboard` - Admin dashboard (requires Cognito auth)
2. `GET /admin/newsletters` - Newsletter publishing form (requires Cognito auth)
3. `POST /admin/newsletters` - Publish newsletter (requires Cognito auth, idempotency key)
4. `GET /admin/password` - Change password form (requires Cognito auth)
5. `POST /admin/password` - Change password (requires Cognito auth) [Modified for Cognito]
6. `POST /admin/logout` - Logout (requires Cognito auth)

**Performance**: API response time < 200ms (p95)

---

### FR-9: Idempotency Preservation
**Priority**: CRITICAL  
**Description**: Newsletter publishing idempotency mechanism must be preserved to prevent duplicate sends.

**Acceptance Criteria**:
- Idempotency table remains in Aurora PostgreSQL
- Newsletter publish endpoint checks idempotency key before processing
- Duplicate requests return cached response (201 or 200)
- Idempotency keys scoped to user_id (Cognito sub claim)
- Concurrent requests with same idempotency key handled safely

---

### FR-10: Data Validation and Domain Logic
**Priority**: CRITICAL  
**Description**: All existing domain validation rules must be preserved.

**Validation Rules**:
- Email address validation (format + DNS validation)
- Subscriber name validation (length, forbidden characters)
- Newsletter content validation (non-empty title, content)
- Idempotency key format validation

---

## Non-Functional Requirements

### NFR-1: Reliability - High Availability
**Priority**: CRITICAL  
**Well-Architected Pillar**: Reliability

**Requirement**: 99.9% availability (Multi-AZ deployment)

**Architecture**:
- **ECS Fargate**: Tasks spread across multiple AZs
- **Aurora PostgreSQL**: Multi-AZ with automatic failover
- **ElastiCache Serverless**: Multi-AZ replication
- **Application Load Balancer**: Multi-AZ distribution
- **SQS**: Regional service with automatic replication

**Failure Scenarios**:
- AZ failure: Automatic failover to healthy AZ (< 2 minutes)
- Container failure: ECS restarts task automatically (< 30 seconds)
- Database failure: Aurora fails over to standby (< 30 seconds)

**Availability Calculation**:
- ALB: 99.99%
- ECS Fargate: 99.99%
- Aurora Multi-AZ: 99.95%
- ElastiCache: 99.9%
- Combined: ~99.9%

---

### NFR-2: Reliability - Disaster Recovery
**Priority**: HIGH  
**Well-Architected Pillar**: Reliability

**Requirement**: Warm Standby (RTO: minutes, RPO: seconds)

**DR Strategy**:
- **Primary Region**: us-east-1 (or user's preferred region)
- **DR Region**: us-west-2 (cross-region)
- **Aurora**: Cross-region read replica with automated promotion
- **ElastiCache**: Global Datastore for cross-region replication
- **S3**: Cross-region replication for container images and backups
- **Infrastructure**: AWS CDK stacks deployable to DR region

**Failover Process**:
1. Route 53 health check detects primary region failure
2. Route 53 automatically routes traffic to DR region
3. Promote Aurora read replica to primary (< 1 minute)
4. ECS tasks already running in DR region (scaled down, scale up on failover)
5. Total RTO: 2-5 minutes
6. RPO: < 1 second (continuous replication)

**Cost Optimization**: DR region runs at 25% capacity, scales up on failover

---

### NFR-3: Security - Network Isolation
**Priority**: CRITICAL  
**Well-Architected Pillar**: Security

**Requirement**: Private subnets with VPC endpoints (highest security, no internet egress)

**VPC Architecture**:
- **Public Subnets**: Application Load Balancer only (internet-facing)
- **Private Subnets**: ECS Fargate tasks, Lambda functions, Aurora, ElastiCache
- **No NAT Gateway**: All AWS service access via VPC endpoints
- **No Internet Gateway** for private resources

**VPC Endpoints Required**:
- com.amazonaws.region.s3 (Gateway endpoint for ECR image pulls)
- com.amazonaws.region.ecr.api (Interface endpoint)
- com.amazonaws.region.ecr.dkr (Interface endpoint)
- com.amazonaws.region.logs (CloudWatch Logs)
- com.amazonaws.region.secretsmanager
- com.amazonaws.region.sts (for IAM role assumption)
- com.amazonaws.region.ses (for Lambda email sending)
- com.amazonaws.region.sqs (for Lambda SQS triggers)

**Security Groups**:
- ALB: Inbound 443 (HTTPS) from 0.0.0.0/0, outbound to ECS tasks
- ECS Tasks: Inbound from ALB only, outbound to Aurora, ElastiCache, VPC endpoints
- Aurora: Inbound from ECS and Lambda only (port 5432)
- ElastiCache: Inbound from ECS only (port 6379)
- Lambda: Outbound to SQS, SES, Aurora via VPC endpoints

**Compliance with SECURITY-01**:
- Aurora encryption at rest enabled
- ElastiCache encryption at rest enabled
- TLS 1.2+ enforced for all connections
- S3 bucket for logs encrypted at rest

---

### NFR-4: Security - Secrets Management
**Priority**: CRITICAL  
**Well-Architected Pillar**: Security

**Requirement**: AWS Secrets Manager for all application secrets

**Secrets to Migrate**:
- Database password (Aurora PostgreSQL)
- Redis connection string (ElastiCache Serverless)
- HMAC secret (for session cookies and flash messages)
- SES API credentials (IAM role recommended instead)
- Cognito client secret

**Implementation**:
- Store secrets in AWS Secrets Manager
- ECS task IAM role granted read access to secrets
- Lambda execution role granted read access to secrets
- Application code retrieves secrets on startup (or cache with 5-minute TTL)
- Automatic secret rotation enabled for database password (30 days)

**Configuration Management**:
- Replace configuration/base.yaml and local.yaml with environment-specific Secrets Manager references
- Use AWS CDK to create secrets during infrastructure deployment
- Secrets injected as environment variables in ECS task definitions

---

### NFR-5: Security - Encryption
**Priority**: CRITICAL  
**Well-Architected Pillar**: Security  
**Extension Rule**: SECURITY-01

**Requirement**: Encryption at rest and in transit for all data stores

**Encryption at Rest**:
- **Aurora PostgreSQL**: AWS KMS encryption with AWS-managed key (or customer-managed CMK)
- **ElastiCache**: Encryption at rest enabled
- **S3 Buckets**: Server-side encryption (SSE-S3 or SSE-KMS)
- **EBS Volumes**: Encrypted by default in ECS Fargate

**Encryption in Transit**:
- **ALB to Clients**: HTTPS only (TLS 1.2+), HTTP redirects to HTTPS
- **ALB to ECS Tasks**: HTTPS with valid certificate
- **ECS/Lambda to Aurora**: PostgreSQL SSL/TLS connection enforced
- **ECS to ElastiCache**: TLS in-transit encryption enabled
- **Lambda to SES**: HTTPS (AWS SDK default)
- **All VPC Endpoint Traffic**: TLS 1.2+

**Certificate Management**:
- ACM (AWS Certificate Manager) for ALB certificate
- Automatic renewal before expiration

---

### NFR-6: Security - Access Logging
**Priority**: HIGH  
**Well-Architected Pillar**: Security  
**Extension Rule**: SECURITY-02

**Requirement**: Access logging on all network-facing intermediaries

**Logging Configuration**:
- **Application Load Balancer**: Access logs to S3 bucket
  - Includes: timestamp, client IP, target, response code, latency
  - Retention: 90 days
- **CloudWatch Logs**: Application logs from ECS and Lambda
  - Structured JSON logs (Bunyan format preserved)
  - Retention: 30 days for application logs, 90 days for access logs

**Compliance**:
- No network intermediary deployed without access logging
- S3 bucket for ALB logs has encryption at rest (SECURITY-01)
- Log bucket has restricted IAM access (read-only for security team)

---

### NFR-7: Observability - Monitoring and Tracing
**Priority**: HIGH  
**Well-Architected Pillar**: Operational Excellence

**Requirement**: CloudWatch + X-Ray for comprehensive observability

**CloudWatch Metrics**:
- **ECS Fargate**: CPU, memory utilization per task
- **Aurora**: Database connections, read/write latency, storage, CPU
- **ElastiCache**: Cache hit rate, evictions, connections, CPU
- **SQS**: Queue depth, message age, messages sent/received
- **Lambda**: Invocations, errors, duration, concurrent executions
- **ALB**: Request count, target response time, HTTP error rates

**CloudWatch Logs**:
- ECS task logs (structured JSON from tracing-bunyan-formatter)
- Lambda function logs (structured logging)
- Aurora slow query logs (queries > 1 second)

**X-Ray Tracing**:
- End-to-end request tracing from ALB through ECS to Aurora
- Lambda function tracing for SQS message processing
- Service map visualization showing dependencies
- Trace sampling: 5% of requests (configurable)

**Dashboards**:
- **Operational Dashboard**: Request rates, error rates, latencies
- **Business Dashboard**: Subscriptions/hour, newsletters published, emails sent
- **Infrastructure Dashboard**: Resource utilization, costs

---

### NFR-8: Observability - Alerting
**Priority**: MEDIUM  
**Well-Architected Pillar**: Operational Excellence

**Requirement**: Critical alerting for service health

**Alerts**:
1. **Service Down**: ALB target group has 0 healthy targets → Page oncall
2. **Database Failure**: Aurora cluster status != available → Page oncall
3. **High Error Rate**: HTTP 5xx error rate > 5% for 5 minutes → Page oncall
4. **Lambda Errors**: Lambda error rate > 10% for 5 minutes → Email team
5. **SQS DLQ Messages**: Messages in dead-letter queue > 0 → Email team

**Notification**:
- SNS topic for critical alerts
- SNS topic subscribed to PagerDuty (or email for MVP)
- Alerts include runbook link for remediation

---

### NFR-9: Performance - API Latency
**Priority**: HIGH  
**Well-Architected Pillar**: Performance Efficiency

**Requirement**: API response time < 200ms (p95)

**Performance Targets**:
- **Health Check**: < 50ms
- **Subscription Form Submit**: < 200ms
- **Admin Dashboard**: < 200ms
- **Newsletter Publish**: < 500ms (idempotency check + SQS enqueue)

**Optimization Strategies**:
- Aurora Serverless v2: Auto-scales ACUs based on load
- ElastiCache: In-memory session storage (microsecond latency)
- ECS Fargate: Right-sized task CPU/memory (0.5 vCPU, 1 GB RAM)
- Connection pooling: SQLx connection pool (min: 5, max: 20)
- Keep-alive connections to Aurora and ElastiCache

**Load Testing**:
- JMeter or Locust to simulate concurrent users
- Target: 100 concurrent requests with < 200ms p95 latency
- Validate before production deployment

---

### NFR-10: Performance - Email Queueing
**Priority**: MEDIUM  
**Well-Architected Pillar**: Performance Efficiency

**Requirement**: Newsletter emails queued within 1 minute (actual delivery time varies by volume)

**Clarification** (from requirement-clarification-questions.md):
- Email queuing to SQS must complete within 1 minute
- Actual email delivery time depends on subscriber count
- No strict limit on end-to-end delivery time

**Implementation**:
- Newsletter publish endpoint writes all subscriber messages to SQS in batch
- SQS batch send: 10 messages per API call
- For 10,000 subscribers: ~1,000 API calls = ~10 seconds
- SQS Standard queue: Unlimited throughput

**Lambda Processing**:
- Lambda concurrency: 100 (aligned with SES sending rate)
- Batch size: 10 messages per Lambda invocation
- Expected processing rate: 1,000 emails/minute (adjustable)

---

### NFR-11: Scalability - Auto-Scaling
**Priority**: MEDIUM  
**Well-Architected Pillar**: Performance Efficiency

**Requirement**: Automatic scaling for unknown subscriber count

**ECS Fargate Auto-Scaling**:
- **Metric**: CPU utilization target = 70%
- **Min Tasks**: 2 (for HA)
- **Max Tasks**: 10
- **Scale-out**: Add 1 task when CPU > 70% for 2 minutes
- **Scale-in**: Remove 1 task when CPU < 50% for 5 minutes

**Lambda Concurrency**:
- **Reserved Concurrency**: 100 (prevents runaway Lambda costs)
- **SQS Trigger**: Batch size = 10, max batching window = 5 seconds
- **Auto-scaling**: Lambda scales automatically up to reserved concurrency

**Aurora Serverless v2**:
- **Min ACUs**: 0.5 (512 MB RAM)
- **Max ACUs**: 4 (4 GB RAM)
- **Auto-scaling**: Scales in 0.5 ACU increments based on load

**ElastiCache Serverless**:
- **Automatic scaling** based on workload
- No manual capacity planning required

---

### NFR-12: Cost Optimization
**Priority**: LOW  
**Well-Architected Pillar**: Cost Optimization

**Requirement**: Operations-first approach (no hard cost constraints)

**User Preference**: Prioritize operational simplicity and fully managed services over cost optimization

**Cost Considerations**:
- **ECS Fargate**: Pay per vCPU-hour and GB-hour (more expensive than EC2, but simpler)
- **Aurora Serverless v2**: Pay per ACU-hour (cost-effective for variable workloads)
- **ElastiCache Serverless**: Pay per data processed (no upfront provisioning)
- **Lambda**: Pay per invocation and GB-second (cost-effective for event-driven workloads)
- **NAT Gateway Avoided**: Saved ~$32/month by using VPC endpoints

**Cost Monitoring**:
- AWS Cost Explorer for monthly cost analysis
- Budget alert: Email when monthly costs exceed $500 (adjustable threshold)
- Cost allocation tags: Environment (prod/dev), Component (web/worker/database)

---

### NFR-13: Operational Excellence - Deployment Automation
**Priority**: HIGH  
**Well-Architected Pillar**: Operational Excellence

**Requirement**: GitHub Actions CI/CD pipeline with AWS deployment

**Pipeline Stages**:
1. **Build**: Compile Rust application, run unit tests
2. **Test**: Run integration tests against test Aurora database
3. **Package**: Build Docker image, push to Amazon ECR
4. **Deploy Infrastructure**: Deploy AWS CDK stacks (if changes detected)
5. **Deploy Application**: Update ECS service with new task definition
6. **Deploy Lambda**: Package and deploy Lambda function
7. **Smoke Tests**: Run health check and basic API tests against production

**GitHub Actions Workflow**:
- Trigger: Push to main branch
- AWS credentials: OIDC provider (no long-lived access keys)
- Environments: dev, staging, production (manual approval for production)

**Rollback Strategy**:
- ECS: Previous task definition retained, manual rollback via AWS console or CLI
- Lambda: $LATEST alias points to new version, previous versions retained (5 versions)
- Database: Migrations tested in staging first, manual rollback via restore from backup

---

### NFR-14: Operational Excellence - Infrastructure as Code
**Priority**: CRITICAL  
**Well-Architected Pillar**: Operational Excellence

**Requirement**: AWS CDK with Python for all infrastructure

**CDK Stacks**:
1. **Network Stack**: VPC, subnets, VPC endpoints, security groups
2. **Database Stack**: Aurora PostgreSQL cluster, parameter groups, secrets
3. **Cache Stack**: ElastiCache Serverless cluster
4. **Compute Stack**: ECS cluster, task definitions, services, ALB
5. **Worker Stack**: SQS queue, DLQ, Lambda function, IAM roles
6. **Auth Stack**: Cognito User Pool, app client
7. **Observability Stack**: CloudWatch dashboards, alarms, SNS topics
8. **CI/CD Stack**: ECR repository, GitHub OIDC provider

**CDK Organization**:
- Modular stacks with explicit dependencies
- Environment-specific configuration (dev.py, prod.py)
- Secrets referenced from Secrets Manager (not hardcoded)
- Stack outputs exported for cross-stack references

**CDK Deployment**:
```bash
cdk bootstrap  # One-time account/region setup
cdk synth      # Generate CloudFormation templates
cdk diff       # Preview changes
cdk deploy --all  # Deploy all stacks
```

---

### NFR-15: Maintainability - Code Quality
**Priority**: MEDIUM  
**Well-Architected Pillar**: Operational Excellence

**Requirement**: Preserve existing code quality (Grade A-)

**Code Quality Standards**:
- Strong type safety with newtype pattern
- Comprehensive error handling with context
- Structured logging (tracing + tracing-bunyan-formatter)
- Compile-time SQL validation (SQLx macros)
- No unsafe Rust code

**Testing Standards**:
- Integration test coverage: > 80% of critical paths
- Unit test coverage: > 50% of business logic
- Property-based testing: Partial enforcement (PBT-02, PBT-03, PBT-07, PBT-08, PBT-09)
  - Round-trip serialization tests for domain types
  - Idempotency property tests
  - Commutativity tests where applicable

**Security Testing**:
- Dependency vulnerability scanning (cargo audit in CI)
- Container image scanning (ECR scan on push)
- OWASP Top 10 validation (no SQL injection, XSS, CSRF)

---

## Extension Rules Summary

### Security Baseline (ENABLED)

**Status**: Enforced as blocking constraints across all phases

**Key Rules**:
- **SECURITY-01**: Encryption at rest and in transit for all data stores (Aurora, ElastiCache, S3)
- **SECURITY-02**: Access logging on network intermediaries (ALB)
- **SECURITY-03**: Secrets in managed secret service (Secrets Manager)
- **SECURITY-04**: Private networking and least-privilege IAM roles
- **SECURITY-05**: Security group rules documented and minimal
- **SECURITY-06**: No hardcoded credentials in code or configuration

**Compliance**:
All security rules must be verified before stage completion. Non-compliance is a blocking finding.

---

### Property-Based Testing (PARTIAL ENFORCEMENT)

**Status**: Partial enforcement - Rules PBT-02, PBT-03, PBT-07, PBT-08, PBT-09 only

**Enforced Rules**:
- **PBT-02**: Round-trip serialization tests (domain types ↔ JSON/database)
- **PBT-03**: Invariant preservation tests (validation rules hold for all inputs)
- **PBT-07**: Parse → serialize round-trip for external formats
- **PBT-08**: Serialization round-trip for persistence
- **PBT-09**: Property test coverage for migration/refactoring

**Advisory (Non-blocking)**:
- PBT-01, PBT-04, PBT-05, PBT-06, PBT-10: Treated as recommendations

**Implementation**:
- Use `quickcheck` crate (already in dev-dependencies)
- Generate random valid inputs with `Arbitrary` trait
- Verify properties hold for all generated inputs
- Document properties in test comments

---

## Architectural Diagrams

### Target AWS Architecture

```text
                           Internet
                              |
                              v
                    +------------------+
                    | Route 53 (DNS)   |
                    +------------------+
                              |
                              v
                    +------------------+
                    | WAF (optional)   |
                    +------------------+
                              |
                              v
            +------------------------------------------+
            | Application Load Balancer (Multi-AZ)     |
            | - HTTPS (TLS 1.2+)                       |
            | - Access Logs -> S3                      |
            +------------------------------------------+
                        |           |
            +-----------+           +-----------+
            v                                   v
    +----------------+                  +----------------+
    | ECS Fargate    |                  | ECS Fargate    |
    | Web Tier       |                  | Web Tier       |
    | (Private AZ-A) |                  | (Private AZ-B) |
    +----------------+                  +----------------+
            |                                   |
            +-------------------+---------------+
                                |
                +---------------+---------------+
                |               |               |
                v               v               v
    +------------------+ +-----------+ +------------------+
    | Aurora Postgres  | | ElastiCache| | Secrets Manager  |
    | Serverless v2    | | Serverless | | (Credentials)    |
    | Multi-AZ         | | Multi-AZ   | +------------------+
    +------------------+ +-----------+
                |
                |
    +----------------------------------------+
    | Newsletter Publishing Flow             |
    +----------------------------------------+
                |
                v
    +------------------+
    | SQS Queue        |
    | (Delivery Tasks) |
    +------------------+
                |
                v
    +------------------+
    | Lambda Function  |
    | (Email Sender)   |
    +------------------+
                |
                v
    +------------------+     +------------------+
    | Amazon SES       |     | SQS DLQ          |
    | (Email Delivery) |     | (Failed Tasks)   |
    +------------------+     +------------------+

    +------------------+
    | AWS Cognito      |
    | User Pools       |
    | (Admin Auth)     |
    +------------------+

    +------------------------------------------+
    | Observability                            |
    +------------------------------------------+
    | CloudWatch Logs | X-Ray | Metrics        |
    +------------------------------------------+

    +------------------------------------------+
    | Networking                               |
    +------------------------------------------+
    | VPC | Private Subnets | VPC Endpoints    |
    +------------------------------------------+
```

### Data Flow - Newsletter Publishing

```text
1. Admin logs in (Cognito)
2. Admin submits newsletter (POST /admin/newsletters)
3. ECS Task:
   - Validates input
   - Checks idempotency (Aurora)
   - Inserts newsletter issue (Aurora)
   - Fetches confirmed subscribers (Aurora)
   - Writes delivery tasks to SQS (batch)
   - Returns 200 OK
4. SQS triggers Lambda (batch of 10 messages)
5. Lambda:
   - Retrieves newsletter content (Aurora)
   - Sends email (SES)
   - Returns success (SQS deletes message)
6. Failed deliveries retry 3x, then move to DLQ
```

---

## Migration Checklist

### Phase 1: Infrastructure Setup (Weeks 1-2)
- [ ] Create AWS CDK Python project structure
- [ ] Define VPC, subnets, VPC endpoints, security groups (Network Stack)
- [ ] Create Aurora PostgreSQL Serverless v2 cluster (Database Stack)
- [ ] Create ElastiCache Serverless for Redis cluster (Cache Stack)
- [ ] Create Secrets Manager secrets
- [ ] Deploy infrastructure to AWS
- [ ] Validate connectivity (bastion host for testing)

### Phase 2: Database Migration (Week 3)
- [ ] Manually create Aurora database schema (execute DDL)
- [ ] Export data from source PostgreSQL
- [ ] Import data into Aurora
- [ ] Validate data integrity (row counts, sample queries)
- [ ] Test SQLx connection from local development

### Phase 3: Web Application Migration (Week 4)
- [ ] Update configuration to use Aurora and ElastiCache endpoints
- [ ] Create Dockerfile for zero2prod web application
- [ ] Create ECR repository
- [ ] Build and push Docker image
- [ ] Create ECS task definition (Compute Stack)
- [ ] Create ECS Fargate service with ALB (Compute Stack)
- [ ] Deploy ECS service
- [ ] Test all public endpoints (health check, subscriptions, login)
- [ ] Test session persistence

### Phase 4: Background Worker Migration (Week 5-6)
- [ ] Refactor newsletter publish endpoint to write to SQS (not database queue)
- [ ] Create SQS queue and DLQ (Worker Stack)
- [ ] Create Lambda function for email sending (Worker Stack)
- [ ] Implement Lambda handler (retrieve newsletter, send via SES, delete SQS message)
- [ ] Configure SQS trigger for Lambda
- [ ] Deploy Lambda function
- [ ] Test end-to-end newsletter publishing and delivery
- [ ] Remove old issue_delivery_queue table (deprecated)

### Phase 5: Email Service Migration (Week 6)
- [ ] Verify SES sender identity (domain or email)
- [ ] Request production access (if needed)
- [ ] Update EmailClient to use AWS SDK for SES
- [ ] Deploy updated code
- [ ] Test confirmation emails
- [ ] Test newsletter emails via SQS+Lambda
- [ ] Configure bounce/complaint handling (SNS)

### Phase 6: Authentication Migration (Week 7)
- [ ] Create Cognito User Pool (Auth Stack)
- [ ] Migrate admin users to Cognito (password reset required)
- [ ] Update login endpoint to authenticate via Cognito
- [ ] Update session middleware to validate Cognito JWT
- [ ] Deploy updated code
- [ ] Test admin login flow
- [ ] Test protected endpoints (dashboard, newsletter form)

### Phase 7: Observability (Week 8)
- [ ] Configure CloudWatch Logs for ECS and Lambda
- [ ] Enable X-Ray tracing in ECS and Lambda
- [ ] Create CloudWatch dashboards (Observability Stack)
- [ ] Create CloudWatch alarms for critical metrics
- [ ] Create SNS topic for alerts
- [ ] Subscribe to SNS topic (email or PagerDuty)
- [ ] Test alerting (simulate failure scenarios)

### Phase 8: Security Hardening (Week 9)
- [ ] Verify all SECURITY rules compliance
- [ ] Enable ALB access logging to S3
- [ ] Verify encryption at rest (Aurora, ElastiCache, S3)
- [ ] Verify TLS 1.2+ enforcement
- [ ] Review security group rules (least privilege)
- [ ] Review IAM roles (least privilege)
- [ ] Run vulnerability scans (cargo audit, ECR scan)
- [ ] Document security architecture

### Phase 9: CI/CD Pipeline (Week 10)
- [ ] Create GitHub Actions workflow
- [ ] Configure OIDC provider for AWS access
- [ ] Implement build, test, package, deploy stages
- [ ] Test pipeline in dev environment
- [ ] Deploy to staging environment
- [ ] Manual approval gate for production
- [ ] Deploy to production
- [ ] Test rollback procedure

### Phase 10: Disaster Recovery (Week 11)
- [ ] Set up Aurora cross-region read replica
- [ ] Configure ElastiCache Global Datastore
- [ ] Deploy CDK stacks to DR region (scaled down)
- [ ] Configure Route 53 health checks and failover
- [ ] Test DR failover procedure
- [ ] Document DR runbook

### Phase 11: Testing and Validation (Week 12)
- [ ] Load testing (100 concurrent users, < 200ms p95 latency)
- [ ] Stress testing (validate auto-scaling)
- [ ] End-to-end functional testing (all user journeys)
- [ ] Security testing (OWASP Top 10)
- [ ] Property-based tests for domain types
- [ ] DR failover test
- [ ] Production deployment and smoke tests
- [ ] Post-deployment monitoring (24-hour watch)

---

## Success Criteria

### Technical Success
- [ ] All public and admin endpoints functional with < 200ms latency (p95)
- [ ] Newsletter emails queued within 1 minute
- [ ] 99.9% availability achieved (Multi-AZ)
- [ ] Zero data loss during migration
- [ ] All SECURITY rules verified as compliant
- [ ] DR failover tested successfully (RTO < 5 minutes)

### Operational Success
- [ ] AWS CDK infrastructure fully deployed and documented
- [ ] CI/CD pipeline operational (automated deployments)
- [ ] CloudWatch dashboards and alarms configured
- [ ] Runbooks created for common operational tasks
- [ ] Team trained on AWS infrastructure and troubleshooting

### Business Success
- [ ] No user-visible downtime during migration
- [ ] Newsletter service continues operating without interruption
- [ ] Admin users successfully transitioned to Cognito authentication
- [ ] Email deliverability maintained (SES reputation healthy)

---

## Risks and Mitigation

### Risk 1: Aurora PostgreSQL Compatibility
**Risk**: SQLx query macros may fail if Aurora PostgreSQL has subtle incompatibilities.  
**Mitigation**: Test all SQLx queries in staging environment before production migration.

### Risk 2: SES Sending Limits
**Risk**: Default SES sandbox limits (200 emails/day) insufficient for production.  
**Mitigation**: Request production access early (Week 1), allow 24-48 hours for approval.

### Risk 3: Cognito JWT Integration Complexity
**Risk**: Replacing Argon2 password authentication with Cognito JWT may introduce bugs.  
**Mitigation**: Implement Cognito integration in staging first, test all admin workflows thoroughly.

### Risk 4: VPC Endpoint Costs
**Risk**: VPC Interface endpoints cost ~$7.20/month per endpoint (9 endpoints = ~$65/month).  
**Mitigation**: User accepted "operations-first" cost approach (NFR-12).

### Risk 5: Lambda Cold Start Latency
**Risk**: Lambda cold starts may delay first few email deliveries.  
**Mitigation**: Provision concurrency (1-2 instances) or accept cold starts (user selected "email queued in < 1 minute", not delivered).

### Risk 6: Manual Database Migration
**Risk**: Manual schema creation and data migration is error-prone.  
**Mitigation**: Automate as much as possible with scripts, validate with checksums and row counts.

---

## Out of Scope

The following items are explicitly **not included** in this modernization effort:

- ❌ Multi-region active-active deployment (DR is warm standby only)
- ❌ GraphQL API (REST API preserved)
- ❌ Mobile application (web only)
- ❌ Payment processing (no monetization)
- ❌ GDPR, HIPAA, PCI-DSS compliance (no compliance requirements specified)
- ❌ Machine learning features (e.g., spam detection, personalization)
- ❌ Third-party integrations beyond SES (no CRM, analytics, etc.)
- ❌ Kubernetes migration (ECS Fargate is the target)
- ❌ Rewrite in another language (Rust preserved)
- ❌ UI/UX redesign (frontend unchanged)

---

## Appendices

### A. AWS Service Summary

| Service | Purpose | Tier |
|---------|---------|------|
| ECS Fargate | Web application hosting | Compute |
| Lambda | Background email worker | Compute |
| Aurora PostgreSQL Serverless v2 | Database | Data |
| ElastiCache Serverless | Session storage | Data |
| SQS | Email delivery queue | Integration |
| SES | Email sending | Integration |
| Cognito User Pools | Admin authentication | Security |
| Secrets Manager | Secrets management | Security |
| Application Load Balancer | HTTP routing | Network |
| VPC | Network isolation | Network |
| CloudWatch | Logs, metrics, alarms | Observability |
| X-Ray | Distributed tracing | Observability |
| ECR | Container registry | Developer Tools |
| CDK | Infrastructure as Code | Developer Tools |
| Route 53 | DNS and failover | Network |
| SNS | Alert notifications | Integration |
| S3 | ALB access logs, backups | Storage |

**Total Services**: 17

---

### B. Configuration Changes

**Before (Local Deployment)**:
```yaml
# configuration/base.yaml
database:
  host: localhost
  port: 5432
  username: postgres
  password: password
  database_name: newsletter

redis_uri: redis://127.0.0.1:6379

email_client:
  base_url: https://api.postmarkapp.com
  authorization_token: POSTMARK_API_TOKEN
```

**After (AWS Deployment)**:
```yaml
# Configuration loaded from Secrets Manager
database:
  host: aurora-cluster.cluster-xyz.us-east-1.rds.amazonaws.com
  port: 5432
  username: postgres
  password: ${SECRETSMANAGER:database/password}
  database_name: newsletter
  require_ssl: true

redis_uri: ${SECRETSMANAGER:elasticache/connection-string}

email_client:
  # SES endpoint determined by AWS SDK, no base_url needed
  authorization_token: "" # IAM role used instead

application:
  hmac_secret: ${SECRETSMANAGER:application/hmac-secret}
```

---

### C. Glossary

- **ACU**: Aurora Capacity Unit (Aurora Serverless scaling unit)
- **ALB**: Application Load Balancer
- **CMK**: Customer Managed Key (KMS)
- **DLQ**: Dead Letter Queue (for failed messages)
- **DR**: Disaster Recovery
- **ECR**: Elastic Container Registry
- **ECS**: Elastic Container Service
- **IAM**: Identity and Access Management
- **JWT**: JSON Web Token (Cognito auth token)
- **Multi-AZ**: Multiple Availability Zones (for HA)
- **PBT**: Property-Based Testing
- **RTO**: Recovery Time Objective
- **RPO**: Recovery Point Objective
- **SES**: Simple Email Service
- **SNS**: Simple Notification Service
- **SQS**: Simple Queue Service
- **TLS**: Transport Layer Security
- **VPC**: Virtual Private Cloud

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-11  
**Status**: APPROVED (pending user confirmation)
