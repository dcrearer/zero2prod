# Requirements Verification Questions

Please answer the following questions to clarify the AWS modernization requirements for the zero2prod newsletter service. Answer each question by filling in the letter choice after the [Answer]: tag.

---

## Section 1: AWS Architecture Strategy

### Question 1: Primary Deployment Model
What is your preferred AWS deployment model for the web application component?

A) ECS Fargate (serverless containers) - fully managed, auto-scaling, no EC2 management
B) EKS (Kubernetes) - maximum portability, advanced orchestration, multi-cloud ready
C) EC2 with Auto Scaling Groups - full control, custom configurations, self-managed
D) AWS App Runner - simplest deployment, automatic scaling, source-to-production
E) Lambda with API Gateway - serverless, event-driven, pay-per-request
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 2: Background Worker Architecture
How should the background email delivery worker be modernized?

A) SQS + Lambda - fully serverless, auto-scaling, pay-per-message
B) ECS Fargate scheduled tasks - container-based, scheduled polling
C) EventBridge + Step Functions + Lambda - orchestrated workflow, complex retry logic
D) Keep as sidecar container - deploy worker alongside web server in same task
E) AWS Batch - optimized for batch processing, queue-based job execution
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 3: Database Strategy
What is your preferred approach for the PostgreSQL database?

A) Amazon RDS for PostgreSQL - fully managed, automated backups, Multi-AZ
B) Amazon Aurora PostgreSQL - high performance, auto-scaling storage, serverless option
C) Self-managed PostgreSQL on EC2 - full control, custom configurations
D) Migrate to DynamoDB - fully serverless NoSQL (requires schema redesign)
E) Keep existing PostgreSQL - connect from AWS via VPN/Direct Connect
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 4: Session Store Strategy
How should Redis session storage be handled in AWS?

A) Amazon ElastiCache for Redis - fully managed, in-memory, Multi-AZ
B) DynamoDB with TTL - serverless, pay-per-request, no Redis management
C) ElastiCache Serverless - automatic scaling, pay-per-use Redis
D) Self-managed Redis on EC2 - full control, custom configurations
E) Keep existing Redis - connect from AWS via VPN/Direct Connect
X) Other (please describe after [Answer]: tag below)

[Answer]: C

### Question 5: Email Service Strategy
What email service should replace the current Postmark integration?

A) Amazon SES - native AWS, lower cost, requires warm-up period
B) Keep Postmark - maintain existing integration, minimal changes
C) Amazon Pinpoint - advanced analytics, multi-channel campaigns
D) Third-party (SendGrid, Mailgun) - advanced features, easier migration
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Section 2: Well-Architected Framework Priorities

### Question 6: Pillar Priorities
Which AWS Well-Architected pillars are your TOP priorities? (Choose your highest priority)

A) Operational Excellence - automation, monitoring, continuous improvement
B) Security - identity management, data protection, compliance
C) Reliability - fault tolerance, disaster recovery, auto-healing
D) Performance Efficiency - optimal resource selection, elasticity
E) Cost Optimization - right-sizing, cost visibility, waste elimination
F) Sustainability - energy efficiency, resource optimization
X) Other (please describe after [Answer]: tag below)

[Answer]: C

### Question 7: High Availability Requirements
What are your availability requirements for the newsletter service?

A) Standard (99.5%) - single AZ, automated backups, acceptable downtime
B) High (99.9%) - Multi-AZ deployment, automatic failover, minimal downtime
C) Very High (99.95%+) - Multi-region, active-active, zero downtime
D) Development/Test - no HA requirements, optimize for cost
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 8: Disaster Recovery Requirements
What is your disaster recovery strategy?

A) Backup and Restore (RTO: hours, RPO: hours) - automated backups, lower cost
B) Pilot Light (RTO: 10-60 min, RPO: minutes) - minimal standby, quick activation
C) Warm Standby (RTO: minutes, RPO: seconds) - scaled-down replica, always running
D) Multi-Region Active-Active (RTO: seconds, RPO: near-zero) - highest availability
E) No DR requirements - development/test environment only
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Section 3: Security & Compliance

### Question 9: Secrets Management
How should application secrets (database passwords, API keys, HMAC secrets) be managed?

A) AWS Secrets Manager - automatic rotation, audit logging, encrypted storage
B) AWS Systems Manager Parameter Store - simpler, lower cost, encrypted parameters
C) Environment variables in ECS/Lambda - simplest approach, limited auditability
D) HashiCorp Vault - third-party, advanced features, multi-cloud
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 10: Network Security
What network isolation level is required?

A) Public subnets - simplest, direct internet access, public IPs
B) Private subnets with NAT Gateway - better security, controlled egress
C) Private subnets with VPC endpoints - highest security, no internet egress
D) Hybrid - web tier public, database/worker private
X) Other (please describe after [Answer]: tag below)

[Answer]: C

### Question 11: Authentication & Authorization
Should AWS IAM be integrated for admin authentication?

A) Yes - migrate to AWS Cognito for user management
B) Yes - integrate IAM Identity Center (SSO) for admin access
C) No - keep existing password-based authentication
D) Enhance - add MFA to existing authentication system
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 12: Compliance Requirements
Are there specific compliance requirements (GDPR, HIPAA, PCI-DSS, SOC2)?

A) GDPR - EU data protection regulations
B) HIPAA - healthcare data protection
C) PCI-DSS - payment card data security
D) SOC2 - service organization controls
E) Multiple compliance frameworks (please specify in Other)
F) No specific compliance requirements
X) Other (please describe after [Answer]: tag below)

[Answer]: F

---

## Section 4: Observability & Operations

### Question 13: Monitoring & Logging Strategy
What observability strategy should be implemented?

A) CloudWatch only - native AWS, logs + metrics + alarms
B) CloudWatch + X-Ray - add distributed tracing for requests
C) CloudWatch + third-party APM (Datadog, New Relic) - advanced features
D) ELK/EFK Stack - self-managed, centralized logging
E) Minimal - basic health checks only
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 14: Alerting Requirements
What should trigger operational alerts?

A) Critical only - service down, database failures, critical errors
B) Standard - above plus high error rates, performance degradation
C) Comprehensive - above plus queue depth, email failures, security events
D) Minimal - no automated alerting
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 15: Deployment Strategy
What deployment automation is required?

A) AWS CodePipeline + CodeBuild + CodeDeploy - native AWS CI/CD
B) GitHub Actions + AWS deployment - integrated with existing repo
C) GitLab CI/CD - self-hosted or managed
D) Jenkins or other CI/CD tool
E) Manual deployment - no automation needed
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Section 5: Performance & Scalability

### Question 16: Expected Load & Growth
What is the expected newsletter subscriber scale?

A) Small (< 10K subscribers) - minimal scaling needs
B) Medium (10K - 100K subscribers) - moderate scaling required
C) Large (100K - 1M subscribers) - significant scaling required
D) Very Large (> 1M subscribers) - enterprise-scale architecture
E) Unknown - plan for flexible scaling
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 17: Email Delivery Performance
What are the email delivery rate requirements?

A) Slow (hours to deliver) - batch processing overnight
B) Standard (30-60 minutes to deliver) - normal newsletter delivery
C) Fast (5-15 minutes to deliver) - priority delivery with parallelization
D) Real-time (< 1 minute) - immediate delivery required
X) Other (please describe after [Answer]: tag below)

[Answer]: D

### Question 18: API Response Time Requirements
What are acceptable response times for web endpoints?

A) Relaxed (< 1 second) - standard web application
B) Fast (< 500ms) - good user experience
C) Very Fast (< 200ms) - premium user experience
D) Real-time (< 100ms) - high-performance requirements
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Section 6: Cost & Operations

### Question 19: Cost Optimization Priority
What is your approach to AWS cost management?

A) Cost-first - minimize costs, accept some operational overhead
B) Balanced - optimize for both cost and operational simplicity
C) Operations-first - prioritize simplicity, fully managed services
D) No constraints - optimize for performance and features
X) Other (please describe after [Answer]: tag below)

[Answer]: D

### Question 20: Infrastructure as Code
What IaC tool should be used for AWS infrastructure?

A) AWS CDK (TypeScript or Python) - type-safe, programmatic, AWS-native
B) Terraform - multi-cloud, declarative, large ecosystem
C) CloudFormation - native AWS, declarative YAML/JSON
D) AWS SAM - serverless-focused, simplified CloudFormation
E) Pulumi - modern IaC, multiple languages
F) No IaC - manual provisioning via console
X) Other (please describe after [Answer]: tag below)

[Answer]: X AWS CDK with Python

---

## Section 7: Migration Strategy

### Question 21: Migration Approach
What is your preferred migration strategy?

A) Lift-and-shift first, optimize later - fastest migration, minimize changes
B) Re-architect for cloud-native - modernize architecture, leverage AWS services
C) Incremental hybrid - migrate components gradually, dual-run period
D) Greenfield rebuild - fresh start, incorporate all learnings
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 22: Migration Timeline
What is your target timeline for AWS migration?

A) Urgent (< 1 month) - fast-track migration
B) Standard (1-3 months) - balanced approach
C) Gradual (3-6 months) - phased migration with extensive testing
D) Flexible (6+ months) - no urgency, optimize for quality
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 23: Database Migration Strategy
How should the database be migrated?

A) AWS DMS with minimal downtime - continuous replication, cutover window
B) Backup/restore with maintenance window - simpler, requires downtime
C) Blue-green deployment - parallel environments, zero downtime
D) Export/import with application-level dual-write - gradual migration
X) Other (please describe after [Answer]: tag below)

[Answer]: X create new database schema and migrate data manually  

---

## Section 8: Extension Configuration

### Question 24: Security Extensions
Should security extension rules be enforced for this project?

A) Yes - enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)
B) No - skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 25: Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes - enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)
B) Partial - enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity)
C) No - skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Instructions

1. Review each question carefully
2. Fill in your answer choice (A, B, C, D, E, F, or X) after each [Answer]: tag
3. If you choose "X) Other", please describe your specific requirement after the [Answer]: tag
4. Save this file when complete
5. Notify me when you have answered all questions

**Note**: Your answers will be used to generate comprehensive AWS modernization requirements aligned with the Well-Architected Framework.
