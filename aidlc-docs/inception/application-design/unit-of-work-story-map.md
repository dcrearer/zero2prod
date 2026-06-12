# Unit of Work to Requirements Mapping

## Overview

This document provides a comprehensive traceability matrix mapping functional requirements (FR) and non-functional requirements (NFR) to implementation units. Since User Stories were skipped for this infrastructure project, requirements serve as the primary source for mapping unit scope and coverage validation.

**Mapping Strategy**: Each requirement is mapped to one or more units that implement or satisfy that requirement. This ensures complete requirements coverage and enables traceability from business needs to technical implementation.

---

## Functional Requirements to Unit Mapping

### FR-1: Web Application Deployment
**Requirement**: Deploy the zero2prod web application (Actix-web) as a containerized service on AWS ECS Fargate.

**Mapped to Units**:
- **Unit 4: Compute Infrastructure** (PRIMARY)
  - ECS Fargate cluster and service
  - Application Load Balancer
  - ECR repository for container images
  - ECS task definition with zero2prod container
  - Auto-scaling based on CPU/memory
  - Health checks for container orchestration

**Coverage**: COMPLETE

---

### FR-2: Background Email Delivery Worker
**Requirement**: Replace the monolithic background worker with serverless SQS + Lambda architecture for asynchronous email delivery.

**Mapped to Units**:
- **Unit 5: Worker Infrastructure** (PRIMARY)
  - SQS queue for email delivery tasks
  - Lambda function triggered by SQS messages
  - Dead Letter Queue for failed deliveries
  - Event-driven architecture (no polling)
  - Queue depth metrics in CloudWatch

**Coverage**: COMPLETE

---

### FR-3: Database Migration to Amazon Aurora PostgreSQL
**Requirement**: Migrate from self-hosted PostgreSQL to Amazon Aurora PostgreSQL Serverless v2 with manual schema creation and data migration.

**Mapped to Units**:
- **Unit 2: Database Infrastructure** (PRIMARY)
  - Aurora PostgreSQL cluster (Serverless v2)
  - Manual schema creation (6 tables)
  - Data migration from source PostgreSQL
  - Multi-AZ deployment
  - Automated backups (7-day retention)
  - Encryption at rest

**Coverage**: COMPLETE

---

### FR-4: Session Store Migration to ElastiCache Serverless
**Requirement**: Migrate Redis session storage from self-hosted/external Redis to Amazon ElastiCache Serverless for Redis.

**Mapped to Units**:
- **Unit 3: Cache Infrastructure** (PRIMARY)
  - ElastiCache Serverless for Redis cluster
  - Multi-AZ deployment
  - Encryption at rest and in transit
  - Session middleware configuration (actix-session)

**Coverage**: COMPLETE

---

### FR-5: Email Service Migration to Amazon SES
**Requirement**: Replace Postmark email service integration with Amazon SES for both transactional (confirmation) and bulk (newsletter) emails.

**Mapped to Units**:
- **Unit 5: Worker Infrastructure** (PRIMARY)
  - SES configuration (sender identity verification)
  - Lambda function sends emails via SES
  - Bounce and complaint handling (SNS notifications)
  - SES sending quotas increased if needed
- **Unit 4: Compute Infrastructure** (SECONDARY)
  - Application code updated to use SES for confirmation emails
  - Email client code replaced (Postmark → AWS SDK for SES)

**Coverage**: COMPLETE

---

### FR-6: Admin Authentication Migration to AWS Cognito
**Requirement**: Replace local password-based authentication with AWS Cognito user pools for admin user management.

**Mapped to Units**:
- **Unit 6: Authentication Infrastructure** (PRIMARY)
  - Cognito User Pool with username/password authentication
  - Cognito User Pool Client for web application
  - Existing admin users migrated to Cognito
  - Login flow updated to use Cognito authentication
  - Session management updated to validate Cognito JWT tokens
  - Password policies enforced via Cognito

**Coverage**: COMPLETE

---

### FR-7: Public API Endpoints
**Requirement**: All existing public endpoints must remain functional after migration.

**Endpoints**:
1. GET / - Home page
2. GET /health_check - Health monitoring
3. POST /subscriptions - Newsletter subscription
4. GET /subscriptions/confirm - Email confirmation
5. GET /login - Login form
6. POST /login - Login submission (modified for Cognito)

**Mapped to Units**:
- **Unit 4: Compute Infrastructure** (PRIMARY)
  - ECS Fargate deployment serves all public endpoints
  - Application Load Balancer routes traffic to endpoints
  - Health check endpoint validation
- **Unit 2: Database Infrastructure** (SECONDARY)
  - Aurora PostgreSQL provides data for subscriptions
- **Unit 3: Cache Infrastructure** (SECONDARY)
  - ElastiCache provides session storage for authenticated endpoints
- **Unit 6: Authentication Infrastructure** (SECONDARY)
  - Cognito provides authentication for /login endpoint

**Coverage**: COMPLETE

---

### FR-8: Admin API Endpoints
**Requirement**: All existing admin endpoints must remain functional after migration with Cognito authentication.

**Endpoints**:
1. GET /admin/dashboard - Admin dashboard
2. GET /admin/newsletters - Newsletter publishing form
3. POST /admin/newsletters - Publish newsletter
4. GET /admin/password - Change password form
5. POST /admin/password - Change password (modified for Cognito)
6. POST /admin/logout - Logout

**Mapped to Units**:
- **Unit 4: Compute Infrastructure** (PRIMARY)
  - ECS Fargate deployment serves all admin endpoints
  - Application Load Balancer routes traffic to endpoints
- **Unit 6: Authentication Infrastructure** (SECONDARY)
  - Cognito JWT validation for all admin endpoints
  - Change password endpoint uses Cognito API
- **Unit 5: Worker Infrastructure** (SECONDARY)
  - Newsletter publish endpoint writes to SQS queue

**Coverage**: COMPLETE

---

### FR-9: Idempotency Preservation
**Requirement**: Newsletter publishing idempotency mechanism must be preserved to prevent duplicate sends.

**Mapped to Units**:
- **Unit 2: Database Infrastructure** (PRIMARY)
  - Idempotency table remains in Aurora PostgreSQL
- **Unit 4: Compute Infrastructure** (SECONDARY)
  - Newsletter publish endpoint checks idempotency key before processing
  - Idempotency keys scoped to user_id (Cognito sub claim)

**Coverage**: COMPLETE

---

### FR-10: Data Validation and Domain Logic
**Requirement**: All existing domain validation rules must be preserved.

**Validation Rules**:
- Email address validation (format + DNS validation)
- Subscriber name validation (length, forbidden characters)
- Newsletter content validation (non-empty title, content)
- Idempotency key format validation

**Mapped to Units**:
- **Unit 4: Compute Infrastructure** (PRIMARY)
  - Application code preserves all existing validation logic
  - Domain types (newtype pattern) unchanged
  - No changes to validation rules

**Coverage**: COMPLETE

---

## Non-Functional Requirements to Unit Mapping

### NFR-1: Reliability - High Availability
**Requirement**: 99.9% availability (Multi-AZ deployment)

**Mapped to Units**:
- **Unit 1: Network Infrastructure**
  - Multi-AZ VPC with public and private subnets across 2 AZs
- **Unit 2: Database Infrastructure**
  - Aurora PostgreSQL Multi-AZ with automatic failover
- **Unit 3: Cache Infrastructure**
  - ElastiCache Serverless Multi-AZ replication
- **Unit 4: Compute Infrastructure**
  - ECS Fargate tasks spread across multiple AZs
  - Application Load Balancer Multi-AZ distribution
- **Unit 5: Worker Infrastructure**
  - SQS regional service with automatic replication
  - Lambda functions deployed across multiple AZs

**Coverage**: COMPLETE

---

### NFR-2: Reliability - Disaster Recovery
**Requirement**: Warm Standby (RTO: minutes, RPO: seconds)

**Mapped to Units**:
- **FUTURE ENHANCEMENT** (not in current 8 units)
  - Cross-region read replica for Aurora
  - ElastiCache Global Datastore for cross-region replication
  - S3 cross-region replication for backups
  - Route 53 health checks and failover

**Coverage**: PARTIAL (DR setup deferred to post-MVP)

---

### NFR-3: Security - Network Isolation
**Requirement**: Private subnets with VPC endpoints (highest security, no internet egress)

**Mapped to Units**:
- **Unit 1: Network Infrastructure** (PRIMARY)
  - Private subnets for ECS, Lambda, Aurora, ElastiCache
  - Public subnets for ALB only
  - VPC endpoints for all AWS services (no NAT Gateway)
  - Security groups with least-privilege rules

**Coverage**: COMPLETE

---

### NFR-4: Security - Secrets Management
**Requirement**: AWS Secrets Manager for all application secrets

**Mapped to Units**:
- **Unit 2: Database Infrastructure**
  - Aurora password stored in Secrets Manager
  - Automatic secret rotation enabled (30 days)
- **Unit 3: Cache Infrastructure**
  - Redis connection string stored in Secrets Manager
- **Unit 4: Compute Infrastructure**
  - Application code updated to load secrets from Secrets Manager
  - ECS task IAM role granted read access to secrets
  - HMAC secret stored in Secrets Manager
- **Unit 5: Worker Infrastructure**
  - Lambda execution role granted read access to secrets

**Coverage**: COMPLETE

---

### NFR-5: Security - Encryption
**Requirement**: Encryption at rest and in transit for all data stores

**Mapped to Units**:
- **Unit 1: Network Infrastructure**
  - TLS 1.2+ enforced for all VPC endpoint traffic
- **Unit 2: Database Infrastructure**
  - Aurora encryption at rest (AWS KMS)
  - TLS 1.2+ enforced for database connections
- **Unit 3: Cache Infrastructure**
  - ElastiCache encryption at rest
  - TLS 1.2+ for in-transit encryption (rediss://)
- **Unit 4: Compute Infrastructure**
  - ALB HTTPS (TLS 1.2+), HTTP redirects to HTTPS
  - ACM certificate for ALB
  - EBS volumes encrypted by default (ECS Fargate)
- **Unit 5: Worker Infrastructure**
  - SQS server-side encryption (SSE-SQS)
  - Lambda to SES HTTPS (AWS SDK default)

**Coverage**: COMPLETE

---

### NFR-6: Security - Access Logging
**Requirement**: Access logging on all network-facing intermediaries

**Mapped to Units**:
- **Unit 4: Compute Infrastructure**
  - ALB access logs to S3 bucket
  - Log retention: 90 days
- **Unit 7: Observability Infrastructure**
  - S3 bucket encryption at rest for ALB logs
  - CloudWatch Logs for ECS and Lambda application logs

**Coverage**: COMPLETE

---

### NFR-7: Observability - Monitoring and Tracing
**Requirement**: CloudWatch + X-Ray for comprehensive observability

**Mapped to Units**:
- **Unit 4: Compute Infrastructure**
  - CloudWatch Logs for ECS tasks
  - Structured JSON logs (tracing-bunyan-formatter)
- **Unit 5: Worker Infrastructure**
  - CloudWatch Logs for Lambda function
  - Lambda CloudWatch metrics (invocations, errors, duration)
- **Unit 7: Observability Infrastructure** (PRIMARY)
  - CloudWatch dashboards (operational, business, infrastructure)
  - CloudWatch metrics for ECS, Aurora, ElastiCache, SQS, Lambda
  - X-Ray tracing for ECS and Lambda
  - Service map visualization

**Coverage**: COMPLETE

---

### NFR-8: Observability - Alerting
**Requirement**: Critical alerting for service health

**Mapped to Units**:
- **Unit 7: Observability Infrastructure** (PRIMARY)
  - CloudWatch alarms (service down, high error rate, Lambda errors, SQS DLQ)
  - SNS topics for critical and warning alerts
  - PagerDuty integration or email notifications

**Coverage**: COMPLETE

---

### NFR-9: Performance - API Latency
**Requirement**: API response time < 200ms (p95)

**Mapped to Units**:
- **Unit 2: Database Infrastructure**
  - Aurora Serverless v2 auto-scales ACUs based on load
  - Connection pooling (SQLx min: 5, max: 20)
- **Unit 3: Cache Infrastructure**
  - ElastiCache in-memory session storage (microsecond latency)
- **Unit 4: Compute Infrastructure**
  - ECS Fargate right-sized tasks (0.5 vCPU, 1 GB RAM)
  - ALB optimized routing with health checks
  - Keep-alive connections to Aurora and ElastiCache
- **Unit 7: Observability Infrastructure**
  - CloudWatch metrics track API latency (p50, p95, p99)
  - Alarms for latency degradation

**Coverage**: COMPLETE

---

### NFR-10: Performance - Email Queueing
**Requirement**: Newsletter emails queued within 1 minute (actual delivery time varies by volume)

**Mapped to Units**:
- **Unit 4: Compute Infrastructure**
  - Newsletter publish endpoint writes to SQS in batch (10 messages per API call)
  - For 10,000 subscribers: ~1,000 API calls = ~10 seconds
- **Unit 5: Worker Infrastructure**
  - SQS Standard queue with unlimited throughput
  - Lambda processes batch of 10 messages per invocation
  - Lambda concurrency: 100 (aligned with SES sending rate)

**Coverage**: COMPLETE

---

### NFR-11: Scalability - Auto-Scaling
**Requirement**: Automatic scaling for unknown subscriber count

**Mapped to Units**:
- **Unit 2: Database Infrastructure**
  - Aurora Serverless v2 auto-scales (0.5 to 4 ACUs)
- **Unit 3: Cache Infrastructure**
  - ElastiCache Serverless automatic scaling
- **Unit 4: Compute Infrastructure**
  - ECS Fargate auto-scaling (CPU target 70%, min 2, max 10 tasks)
- **Unit 5: Worker Infrastructure**
  - Lambda auto-scales up to reserved concurrency (100)
  - SQS queue scales automatically

**Coverage**: COMPLETE

---

### NFR-12: Cost Optimization
**Requirement**: Operations-first approach (no hard cost constraints)

**Mapped to Units**:
- **Unit 1: Network Infrastructure**
  - VPC endpoints instead of NAT Gateway (saves ~$32/month)
- **Unit 2: Database Infrastructure**
  - Aurora Serverless v2 (cost-effective for variable workloads)
- **Unit 3: Cache Infrastructure**
  - ElastiCache Serverless (pay per data processed, no upfront provisioning)
- **Unit 5: Worker Infrastructure**
  - Lambda (pay per invocation, cost-effective for event-driven workloads)

**Coverage**: PARTIAL (cost optimization is secondary to operational simplicity)

---

### NFR-13: Operational Excellence - Deployment Automation
**Requirement**: GitHub Actions CI/CD pipeline with AWS deployment

**Mapped to Units**:
- **Unit 8: CI/CD Infrastructure** (PRIMARY)
  - GitHub Actions workflow with 6 stages
  - AWS OIDC provider (no long-lived credentials)
  - IAM role for GitHub Actions
  - Automated ECS and Lambda deployments
  - Smoke tests post-deployment

**Coverage**: COMPLETE

---

### NFR-14: Operational Excellence - Infrastructure as Code
**Requirement**: AWS CDK with Python for all infrastructure

**Mapped to Units**:
- **Unit 1: Network Infrastructure** - CDK Stack: network_stack.py
- **Unit 2: Database Infrastructure** - CDK Stack: database_stack.py
- **Unit 3: Cache Infrastructure** - CDK Stack: cache_stack.py
- **Unit 4: Compute Infrastructure** - CDK Stack: compute_stack.py
- **Unit 5: Worker Infrastructure** - CDK Stack: worker_stack.py
- **Unit 6: Authentication Infrastructure** - CDK Stack: auth_stack.py
- **Unit 7: Observability Infrastructure** - CDK Stack: observability_stack.py
- **Unit 8: CI/CD Infrastructure** - CDK Stack: cicd_stack.py

**Coverage**: COMPLETE (all units use AWS CDK Python)

---

### NFR-15: Maintainability - Code Quality
**Requirement**: Preserve existing code quality (Grade A-)

**Mapped to Units**:
- **Unit 4: Compute Infrastructure**
  - Application code changes preserve strong type safety (newtype pattern)
  - Comprehensive error handling with context preserved
  - Structured logging (tracing-bunyan-formatter) unchanged
  - Compile-time SQL validation (SQLx macros) preserved
- **Unit 5: Worker Infrastructure**
  - Lambda handler code follows same quality standards
  - Error handling and logging consistent with application code
- **Unit 8: CI/CD Infrastructure**
  - Automated testing in CI pipeline (unit tests, integration tests)
  - Property-based testing (quickcheck) enforced
  - Dependency vulnerability scanning (cargo audit)
  - Container image scanning (ECR scan on push)

**Coverage**: COMPLETE

---

## Extension Rules to Unit Mapping

### Security Baseline Extension (ENABLED)

**SECURITY-01: Encryption at Rest and In Transit**
**Mapped to Units**:
- **Unit 2**: Aurora encryption at rest, TLS 1.2+ enforced
- **Unit 3**: ElastiCache encryption at rest and in transit
- **Unit 4**: ALB HTTPS, EBS volumes encrypted
- **Unit 5**: SQS server-side encryption

**SECURITY-02: Access Logging on Network Intermediaries**
**Mapped to Units**:
- **Unit 4**: ALB access logs to S3
- **Unit 7**: S3 bucket encryption for logs

**SECURITY-03: Secrets in Managed Secret Service**
**Mapped to Units**:
- **Unit 2**: Database password in Secrets Manager
- **Unit 3**: Redis connection string in Secrets Manager
- **Unit 4**: HMAC secret in Secrets Manager

**SECURITY-04: Private Networking and Least-Privilege IAM**
**Mapped to Units**:
- **Unit 1**: Private subnets, VPC endpoints
- **Unit 4**: ECS task IAM roles (least privilege)
- **Unit 5**: Lambda execution IAM roles (least privilege)

**SECURITY-05: Security Group Rules Documented**
**Mapped to Units**:
- **Unit 1**: Security group rules documented in CDK stack

**SECURITY-06: No Hardcoded Credentials**
**Mapped to Units**:
- **Unit 4**: All secrets loaded from Secrets Manager
- **Unit 5**: All secrets loaded from Secrets Manager

**Coverage**: COMPLETE

---

### Property-Based Testing Extension (PARTIAL ENFORCEMENT)

**PBT-02: Round-trip Serialization Tests**
**Mapped to Units**:
- **Unit 4**: Application code tests (domain types ↔ JSON/database)
- **Unit 8**: CI/CD pipeline enforces PBT tests

**PBT-03: Invariant Preservation Tests**
**Mapped to Units**:
- **Unit 4**: Validation rules property tests
- **Unit 8**: CI/CD pipeline enforces PBT tests

**PBT-07: Parse → Serialize Round-trip**
**Mapped to Units**:
- **Unit 4**: External format parsing tests
- **Unit 8**: CI/CD pipeline enforces PBT tests

**PBT-08: Serialization Round-trip for Persistence**
**Mapped to Units**:
- **Unit 4**: Database serialization tests
- **Unit 8**: CI/CD pipeline enforces PBT tests

**PBT-09: Property Test Coverage for Migration/Refactoring**
**Mapped to Units**:
- **Unit 4**: Migration to Aurora tested with PBT
- **Unit 8**: CI/CD pipeline enforces PBT tests

**Coverage**: COMPLETE (enforced rules only)

---

## Requirements Coverage Analysis

### Functional Requirements Coverage Summary

| Requirement | Primary Unit | Secondary Units | Coverage Status |
|-------------|--------------|-----------------|-----------------|
| FR-1: Web Application Deployment | Unit 4 | - | ✓ COMPLETE |
| FR-2: Background Email Delivery Worker | Unit 5 | - | ✓ COMPLETE |
| FR-3: Database Migration to Aurora | Unit 2 | - | ✓ COMPLETE |
| FR-4: Session Store Migration to ElastiCache | Unit 3 | - | ✓ COMPLETE |
| FR-5: Email Service Migration to SES | Unit 5 | Unit 4 | ✓ COMPLETE |
| FR-6: Admin Authentication Migration to Cognito | Unit 6 | - | ✓ COMPLETE |
| FR-7: Public API Endpoints | Unit 4 | Units 2, 3, 6 | ✓ COMPLETE |
| FR-8: Admin API Endpoints | Unit 4 | Units 5, 6 | ✓ COMPLETE |
| FR-9: Idempotency Preservation | Unit 2 | Unit 4 | ✓ COMPLETE |
| FR-10: Data Validation and Domain Logic | Unit 4 | - | ✓ COMPLETE |

**Total Functional Requirements**: 10  
**Requirements with COMPLETE Coverage**: 10 (100%)

---

### Non-Functional Requirements Coverage Summary

| Requirement | Primary Unit | Secondary Units | Coverage Status |
|-------------|--------------|-----------------|-----------------|
| NFR-1: Reliability - High Availability | Units 1, 2, 3, 4, 5 | - | ✓ COMPLETE |
| NFR-2: Reliability - Disaster Recovery | - | - | ⚠ PARTIAL (future) |
| NFR-3: Security - Network Isolation | Unit 1 | - | ✓ COMPLETE |
| NFR-4: Security - Secrets Management | Units 2, 3, 4, 5 | - | ✓ COMPLETE |
| NFR-5: Security - Encryption | Units 1, 2, 3, 4, 5 | - | ✓ COMPLETE |
| NFR-6: Security - Access Logging | Unit 4 | Unit 7 | ✓ COMPLETE |
| NFR-7: Observability - Monitoring/Tracing | Unit 7 | Units 4, 5 | ✓ COMPLETE |
| NFR-8: Observability - Alerting | Unit 7 | - | ✓ COMPLETE |
| NFR-9: Performance - API Latency | Units 2, 3, 4 | Unit 7 | ✓ COMPLETE |
| NFR-10: Performance - Email Queueing | Units 4, 5 | - | ✓ COMPLETE |
| NFR-11: Scalability - Auto-Scaling | Units 2, 3, 4, 5 | - | ✓ COMPLETE |
| NFR-12: Cost Optimization | Units 1, 2, 3, 5 | - | ⚠ PARTIAL (secondary) |
| NFR-13: Operational Excellence - Deployment | Unit 8 | - | ✓ COMPLETE |
| NFR-14: Operational Excellence - IaC | Units 1-8 | - | ✓ COMPLETE |
| NFR-15: Maintainability - Code Quality | Units 4, 5, 8 | - | ✓ COMPLETE |

**Total Non-Functional Requirements**: 15  
**Requirements with COMPLETE Coverage**: 13 (87%)  
**Requirements with PARTIAL Coverage**: 2 (13%)

**Partial Coverage Notes**:
- **NFR-2 (DR)**: Cross-region DR setup deferred to post-MVP phase (not in current 8 units)
- **NFR-12 (Cost)**: Cost optimization is secondary to operational simplicity per user preference

---

## Requirements Traceability Matrix

### Forward Traceability (Requirements → Units)

**Unit 1: Network Infrastructure**
- NFR-1 (High Availability)
- NFR-3 (Network Isolation) ✓ PRIMARY
- NFR-5 (Encryption)
- NFR-12 (Cost Optimization)
- NFR-14 (Infrastructure as Code)
- SECURITY-04 (Private Networking)
- SECURITY-05 (Security Group Rules)

**Unit 2: Database Infrastructure**
- FR-3 (Database Migration) ✓ PRIMARY
- FR-9 (Idempotency Preservation) ✓ PRIMARY
- NFR-1 (High Availability)
- NFR-4 (Secrets Management)
- NFR-5 (Encryption)
- NFR-9 (Performance - API Latency)
- NFR-11 (Scalability)
- NFR-12 (Cost Optimization)
- NFR-14 (Infrastructure as Code)
- SECURITY-01 (Encryption)
- SECURITY-03 (Secrets Management)

**Unit 3: Cache Infrastructure**
- FR-4 (Session Store Migration) ✓ PRIMARY
- NFR-1 (High Availability)
- NFR-4 (Secrets Management)
- NFR-5 (Encryption)
- NFR-9 (Performance - API Latency)
- NFR-11 (Scalability)
- NFR-12 (Cost Optimization)
- NFR-14 (Infrastructure as Code)
- SECURITY-01 (Encryption)
- SECURITY-03 (Secrets Management)

**Unit 4: Compute Infrastructure**
- FR-1 (Web Application Deployment) ✓ PRIMARY
- FR-5 (Email Service Migration) - Confirmation emails
- FR-7 (Public API Endpoints) ✓ PRIMARY
- FR-8 (Admin API Endpoints) ✓ PRIMARY
- FR-9 (Idempotency Preservation) - Endpoint logic
- FR-10 (Data Validation and Domain Logic) ✓ PRIMARY
- NFR-1 (High Availability)
- NFR-4 (Secrets Management)
- NFR-5 (Encryption)
- NFR-6 (Access Logging) ✓ PRIMARY
- NFR-7 (Observability - Monitoring)
- NFR-9 (Performance - API Latency) ✓ PRIMARY
- NFR-10 (Performance - Email Queueing)
- NFR-11 (Scalability)
- NFR-14 (Infrastructure as Code)
- NFR-15 (Maintainability - Code Quality) ✓ PRIMARY
- SECURITY-01 (Encryption)
- SECURITY-02 (Access Logging)
- SECURITY-03 (Secrets Management)
- SECURITY-04 (Least-Privilege IAM)
- SECURITY-06 (No Hardcoded Credentials)
- PBT-02, PBT-03, PBT-07, PBT-08, PBT-09

**Unit 5: Worker Infrastructure**
- FR-2 (Background Email Delivery Worker) ✓ PRIMARY
- FR-5 (Email Service Migration) ✓ PRIMARY
- NFR-1 (High Availability)
- NFR-4 (Secrets Management)
- NFR-5 (Encryption)
- NFR-7 (Observability - Monitoring)
- NFR-8 (Observability - Alerting)
- NFR-10 (Performance - Email Queueing) ✓ PRIMARY
- NFR-11 (Scalability)
- NFR-12 (Cost Optimization)
- NFR-14 (Infrastructure as Code)
- NFR-15 (Maintainability - Code Quality)
- SECURITY-04 (Least-Privilege IAM)
- SECURITY-06 (No Hardcoded Credentials)

**Unit 6: Authentication Infrastructure**
- FR-6 (Admin Authentication Migration) ✓ PRIMARY
- FR-7 (Public API Endpoints) - Login endpoint
- FR-8 (Admin API Endpoints) - Cognito auth required
- NFR-14 (Infrastructure as Code)

**Unit 7: Observability Infrastructure**
- NFR-6 (Access Logging) - S3 bucket encryption
- NFR-7 (Observability - Monitoring/Tracing) ✓ PRIMARY
- NFR-8 (Observability - Alerting) ✓ PRIMARY
- NFR-9 (Performance - API Latency) - Metrics
- NFR-14 (Infrastructure as Code)
- SECURITY-02 (Access Logging)

**Unit 8: CI/CD Infrastructure**
- NFR-13 (Operational Excellence - Deployment) ✓ PRIMARY
- NFR-14 (Infrastructure as Code)
- NFR-15 (Maintainability - Code Quality) - Automated testing
- PBT-02, PBT-03, PBT-07, PBT-08, PBT-09 (Enforced in CI)

---

### Backward Traceability (Units → Requirements)

**Unit 1 Requirements Coverage**: 7 NFRs, 2 Security Rules  
**Unit 2 Requirements Coverage**: 1 FR, 9 NFRs, 2 Security Rules  
**Unit 3 Requirements Coverage**: 1 FR, 7 NFRs, 2 Security Rules  
**Unit 4 Requirements Coverage**: 5 FRs, 12 NFRs, 6 Security Rules, 5 PBT Rules  
**Unit 5 Requirements Coverage**: 2 FRs, 10 NFRs, 2 Security Rules  
**Unit 6 Requirements Coverage**: 3 FRs, 1 NFR  
**Unit 7 Requirements Coverage**: 5 NFRs, 1 Security Rule  
**Unit 8 Requirements Coverage**: 3 NFRs, 5 PBT Rules  

---

## Gap Analysis

### Requirements with No Unit Coverage
**None** - All functional requirements have complete unit coverage.

### Requirements with Partial Coverage
1. **NFR-2: Reliability - Disaster Recovery**
   - **Gap**: Cross-region DR setup not included in current 8 units
   - **Rationale**: Deferred to post-MVP phase per project priorities
   - **Recommendation**: Add Unit 9 in future for DR infrastructure

2. **NFR-12: Cost Optimization**
   - **Gap**: Cost optimization is secondary to operational simplicity
   - **Rationale**: User preference for operations-first approach
   - **Recommendation**: Monitor costs with AWS Cost Explorer, optimize in future iterations

---

## Unit Coverage Heatmap

The following table shows requirements coverage intensity per unit (number of requirements addressed):

| Unit | Functional Reqs | Non-Functional Reqs | Security Rules | PBT Rules | Total |
|------|----------------|---------------------|----------------|-----------|-------|
| Unit 1 | 0 | 7 | 2 | 0 | 9 |
| Unit 2 | 2 | 9 | 2 | 0 | 13 |
| Unit 3 | 1 | 7 | 2 | 0 | 10 |
| Unit 4 | 5 | 12 | 6 | 5 | 28 |
| Unit 5 | 2 | 10 | 2 | 0 | 14 |
| Unit 6 | 3 | 1 | 0 | 0 | 4 |
| Unit 7 | 0 | 5 | 1 | 0 | 6 |
| Unit 8 | 0 | 3 | 0 | 5 | 8 |

**Insight**: Unit 4 (Compute Infrastructure) has the highest requirements coverage (28 requirements), indicating it is the most complex and critical unit. Units 6 and 7 have lower coverage, indicating they are enhancement units rather than core functionality.

---

## Requirements Prioritization by Unit

### Critical Path Requirements (Blocks Core Functionality)
1. **FR-3**: Database Migration (Unit 2) - BLOCKS all data operations
2. **FR-1**: Web Application Deployment (Unit 4) - BLOCKS all API endpoints
3. **FR-2**: Background Email Delivery Worker (Unit 5) - BLOCKS newsletter delivery
4. **NFR-3**: Security - Network Isolation (Unit 1) - FOUNDATION for all units
5. **NFR-5**: Security - Encryption (Units 1, 2, 3, 4, 5) - MANDATORY for production

### Important Requirements (Enhance Functionality)
1. **FR-6**: Admin Authentication Migration (Unit 6) - Modernizes auth but not blocking
2. **NFR-7**: Observability - Monitoring (Unit 7) - Enables operational excellence
3. **NFR-13**: Operational Excellence - Deployment (Unit 8) - Automates deployments

### Optional Requirements (Nice to Have)
1. **NFR-2**: Disaster Recovery (not in current units) - Future enhancement
2. **NFR-12**: Cost Optimization (partial) - Secondary to operational simplicity

---

## Validation Checklist

### Pre-Construction Validation
- [ ] All 10 functional requirements mapped to at least one unit
- [ ] All 15 non-functional requirements mapped to at least one unit
- [ ] All SECURITY extension rules mapped to at least one unit
- [ ] All enforced PBT extension rules mapped to at least one unit
- [ ] No requirements left unmapped (gap analysis complete)
- [ ] Critical path requirements identified and prioritized

### Per-Unit Validation (During Construction)
For each unit during construction, validate:
- [ ] Unit design addresses all mapped requirements
- [ ] Unit deliverables satisfy acceptance criteria for each requirement
- [ ] Unit testing validates requirement fulfillment
- [ ] Requirements traceability documented in unit artifacts

### Post-Construction Validation (Build & Test)
- [ ] Integration testing validates cross-unit requirement fulfillment
- [ ] End-to-end testing validates all functional requirements
- [ ] Security testing validates all SECURITY extension rules
- [ ] Property-based testing validates all enforced PBT rules
- [ ] Performance testing validates NFR-9 and NFR-10
- [ ] Scalability testing validates NFR-11

---

## Success Metrics

### Requirements Coverage Success Criteria
- **100% functional requirements coverage** - All 10 FRs mapped to units ✓
- **87% non-functional requirements coverage** - 13/15 NFRs with complete coverage ✓
- **100% security extension rules coverage** - All SECURITY rules mapped to units ✓
- **100% enforced PBT rules coverage** - All 5 enforced PBT rules mapped to units ✓
- **Zero unmapped requirements** - No requirements left without unit coverage ✓

### Traceability Success Criteria
- [ ] Forward traceability complete (requirements → units)
- [ ] Backward traceability complete (units → requirements)
- [ ] Gap analysis identifies only acceptable gaps (NFR-2, NFR-12)
- [ ] Critical path requirements prioritized correctly
- [ ] Unit coverage heatmap shows appropriate distribution

---

## Recommendations

### Recommendation 1: Prioritize Critical Path Units
**Rationale**: Critical path requirements (FR-1, FR-2, FR-3, NFR-3, NFR-5) must be completed first to deliver core functionality  
**Action**: Focus on Units 1, 2, 4, 5 before enhancements (Units 6, 7, 8)

### Recommendation 2: Defer DR Setup (NFR-2) to Post-MVP
**Rationale**: DR infrastructure not required for initial production deployment  
**Action**: Document DR gap, plan Unit 9 for future iteration

### Recommendation 3: Validate Security Rules Early
**Rationale**: All SECURITY extension rules are blocking constraints  
**Action**: Review security rule compliance during Functional Design stage for each unit

### Recommendation 4: Test Requirements Coverage During Build & Test
**Rationale**: Ensure all requirements are satisfied before production deployment  
**Action**: Create test cases mapped to each requirement, validate coverage in Phase 4

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-12  
**Status**: Ready for Review
