# Unit 4: Compute Infrastructure - Logical Components

## Overview

This document defines the logical components that implement the NFR patterns for ECS Fargate compute infrastructure. Components are derived from NFR patterns and map to AWS resources.

**Design Date**: 2026-06-12  
**Unit**: 4 of 8 (Compute Infrastructure)

**Note**: Detailed component attributes are defined in `../functional-design/domain-entities.md`. This document focuses on NFR-specific aspects and pattern implementation.

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Application Load Balancer (ALB)                                 │
│  Pattern: TLS Termination, Multi-AZ Distribution                 │
│  ┌──────────────────────┐         ┌──────────────────────┐     │
│  │  HTTP Listener       │────────▶│  HTTPS Listener      │     │
│  │  Port 80             │  301    │  Port 443 + ACM Cert │     │
│  └──────────────────────┘         └───────────┬──────────┘     │
│                                                │                 │
│                                    ┌───────────▼───────────┐    │
│                                    │  Target Group         │    │
│                                    │  Pattern: Auto-Healing│    │
│                                    │  Health Check: 30s    │    │
│                                    └───────────┬───────────┘    │
└────────────────────────────────────────────────┼────────────────┘
                                                 │
                        ┌────────────────────────┼────────────────────┐
                        │                        │                    │
                        ▼                        ▼                    ▼
            ┌───────────────────┐    ┌───────────────────┐   ┌──────────────┐
            │  ECS Task 1       │    │  ECS Task 2       │   │  ECS Task N  │
            │  Pattern: Stateless│    │  Pattern: Stateless│   │  (Auto-Scale)│
            │  1 vCPU / 2 GB    │    │  1 vCPU / 2 GB    │   │              │
            │  us-east-1a       │    │  us-east-1b       │   │              │
            └───────────────────┘    └───────────────────┘   └──────────────┘
                        │                        │
                        └────────────┬───────────┘
                                     │
                        ┌────────────▼────────────┐
                        │  Auto-Scaling Policy    │
                        │  Pattern: Target        │
                        │  Tracking (70% CPU)     │
                        │  Min: 2, Max: 10        │
                        └─────────────────────────┘
```

---

## Component 1: Application Load Balancer

**NFR Patterns Implemented**:
- Pattern 10: TLS Termination at Load Balancer
- Pattern 5: Multi-AZ Load Distribution
- Pattern 1: Auto-Healing via Health Checks

**NFR Requirements Supported**:
- NFR-4 (Security): TLS 1.2+ encryption, HTTP→HTTPS redirect
- NFR-3 (Availability): Multi-AZ, auto-healing targets
- NFR-5 (Reliability): Health check every 30s

**Configuration Summary** (see domain-entities.md for full details):
- Scheme: Internet-facing
- Subnets: 2 public subnets (us-east-1a, us-east-1b)
- Listeners: HTTP (port 80 → redirect), HTTPS (port 443, ACM cert)
- Target Group: HTTP port 8000, health check `/health_check`
- Access Logs: S3 bucket (30-day retention, created in Unit 7)

**Integration Points**:
- Unit 1 (Network): Public subnets, ALB security group
- Unit 7 (Observability): S3 bucket for access logs

---

## Component 2: ECS Cluster

**NFR Patterns Implemented**:
- Pattern 4: Horizontal Auto-Scaling
- Pattern 5: Multi-AZ Load Distribution

**NFR Requirements Supported**:
- NFR-1 (Scalability): Auto-scaling 2-10 tasks
- NFR-3 (Availability): Multi-AZ deployment

**Configuration Summary**:
- Capacity Provider: FARGATE (serverless)
- Container Insights: Enabled (observability)
- Placement Strategy: Spread across AZs

---

## Component 3: ECS Service

**NFR Patterns Implemented**:
- Pattern 15: Rolling Deployment (Zero Downtime)
- Pattern 16: Health Check Grace Period
- Pattern 2: Graceful Shutdown via Connection Draining

**NFR Requirements Supported**:
- NFR-3 (Availability): 99.9% uptime, zero downtime deployments
- NFR-5 (Reliability): MTTD <90s, MTTR <2min

**Configuration Summary**:
- Desired Count: 2 tasks (Multi-AZ, 1 per AZ)
- Launch Type: FARGATE
- Deployment Config: Min 100%, Max 200% (rolling update)
- Health Check Grace Period: 60 seconds
- Load Balancer: Attached to ALB target group

**Integration Points**:
- Unit 1 (Network): Private subnets, ECS security group
- Component 1 (ALB): Target group attachment

---

## Component 4: ECS Task Definition

**NFR Patterns Implemented**:
- Pattern 9: Right-Sizing (Task Resources)
- Pattern 6: Stateless Task Design
- Pattern 11: Secrets Management via AWS Secrets Manager

**NFR Requirements Supported**:
- NFR-2 (Performance): <200ms p50 response time
- NFR-4 (Security): No hardcoded secrets
- NFR-7 (Cost): $130/month baseline (2 tasks)

**Configuration Summary**:
- CPU: 1 vCPU (1024 CPU units)
- Memory: 2 GB (2048 MB)
- Network Mode: awsvpc (required for Fargate)
- Task Execution Role: ECR pull, logs write, secrets read
- Task Role: Runtime permissions (Secrets Manager, X-Ray)

**Container Definition**:
- Image: ECR `zero2prod:sha-<hash>` (immutable tag)
- Port: 8000 (HTTP)
- Environment: Static variables (APP_ENVIRONMENT, LOG_LEVEL, X-Ray config)
- Secrets: DATABASE_URL, REDIS_URI, HMAC_SECRET (from Secrets Manager)
- Logging: CloudWatch Logs (30-day retention)

**Integration Points**:
- Unit 2 (Database): DATABASE_URL secret
- Unit 3 (Cache): REDIS_URI secret
- Component 9 (ECR): Container image
- Component 7 (Task Execution Role): IAM permissions

---

## Component 5: Auto-Scaling Policy

**NFR Patterns Implemented**:
- Pattern 4: Horizontal Auto-Scaling (Target Tracking)

**NFR Requirements Supported**:
- NFR-1 (Scalability): Auto-scaling 2-10 tasks, 70% CPU target
- NFR-7 (Cost): Scale down during low traffic

**Configuration Summary**:
- Policy Type: TargetTrackingScaling
- Metric: ECSServiceAverageCPUUtilization
- Target Value: 70%
- Min Capacity: 2 tasks
- Max Capacity: 10 tasks
- Scale-Out Cooldown: 60 seconds
- Scale-In Cooldown: 300 seconds

**Behavior**:
- Scale-Out: Avg CPU >70% for 1 min → add 1 task
- Scale-In: Avg CPU <70% for 1 min (after 300s cooldown) → remove 1 task

---

## Component 6: Target Group

**NFR Patterns Implemented**:
- Pattern 1: Auto-Healing via Health Checks
- Pattern 2: Graceful Shutdown via Connection Draining

**NFR Requirements Supported**:
- NFR-5 (Reliability): MTTD <90s (3 × 30s)
- NFR-3 (Availability): Auto-healing targets

**Configuration Summary**:
- Protocol: HTTP, Port: 8000
- Target Type: IP (Fargate requires IP mode)
- Deregistration Delay: 300 seconds (connection draining)
- Health Check: Path `/health_check`, Interval 30s, Timeout 5s
- Healthy Threshold: 2 consecutive successes
- Unhealthy Threshold: 3 consecutive failures
- Success Codes: 200

**Health Check Logic** (application responsibility):
- Validate database connectivity (SELECT 1)
- Return 200 OK if database reachable
- Return 503 Service Unavailable if database unreachable
- Cache connectivity NOT validated (non-critical)

---

## Component 7: IAM Task Execution Role

**NFR Patterns Implemented**:
- Pattern 12: Least Privilege IAM
- Pattern 11: Secrets Management

**NFR Requirements Supported**:
- NFR-4 (Security): SECURITY-04 least privilege

**Permissions** (scoped to specific resources):
- **ECR**: GetAuthorizationToken, BatchCheckLayerAvailability, GetDownloadUrlForLayer, BatchGetImage
- **CloudWatch Logs**: CreateLogStream, PutLogEvents (log group: `/ecs/zero2prod-web`)
- **Secrets Manager**: GetSecretValue (secrets: `zero2prod/database/*`, `zero2prod/cache/*`, `zero2prod/hmac/*`)

**Purpose**: Allows ECS agent to pull images, write logs, retrieve secrets at task startup

---

## Component 8: IAM Task Role

**NFR Patterns Implemented**:
- Pattern 12: Least Privilege IAM
- Pattern 8: Distributed Tracing

**NFR Requirements Supported**:
- NFR-4 (Security): SECURITY-04 least privilege
- NFR-2 (Performance): X-Ray tracing for optimization

**Permissions** (scoped to specific resources):
- **Secrets Manager**: GetSecretValue (runtime secret access)
- **CloudWatch Logs**: CreateLogStream, PutLogEvents
- **X-Ray**: PutTraceSegments, PutTelemetryRecords

**Purpose**: Allows application code to access secrets at runtime, write logs, send traces

---

## Component 9: ECR Repository

**NFR Patterns Implemented**:
- Pattern 14: Image Scanning

**NFR Requirements Supported**:
- NFR-4 (Security): Vulnerability scanning
- NFR-6 (Maintainability): Immutable tags, lifecycle policies

**Configuration Summary**:
- Repository Name: `zero2prod`
- Image Tag Mutability: IMMUTABLE (cannot overwrite tags)
- Image Scanning: On push (detect vulnerabilities)
- Lifecycle Policy: Keep last 10 images, delete untagged after 1 day
- Encryption: AES-256 (default)

**Image Tag Strategy**: `sha-<git-commit-hash>` (traceability from running task to source code)

---

## Component 10: CloudWatch Log Group

**NFR Patterns Implemented**:
- Pattern 17: Structured Logging

**NFR Requirements Supported**:
- NFR-5 (Reliability): Troubleshooting capability
- NFR-6 (Maintainability): 30-day log retention

**Configuration Summary**:
- Log Group Name: `/ecs/zero2prod-web`
- Retention: 30 days
- Encryption: CloudWatch default (AES-256)
- Log Streams: One per task (named with task ID)

**Log Format** (application responsibility):
- JSON structured logs (tracing-bunyan-formatter)
- Fields: timestamp, level, message, request_id, trace_id, user_id
- CloudWatch Logs Insights for queries

---

## Component 11: AWS X-Ray Integration

**NFR Patterns Implemented**:
- Pattern 8: Distributed Tracing

**NFR Requirements Supported**:
- NFR-2 (Performance): Identify bottlenecks
- NFR-5 (Reliability): Error diagnosis

**Configuration Summary**:
- X-Ray SDK: Integrated into application
- Daemon: X-Ray daemon sidecar container OR Fargate X-Ray integration
- Environment Variables: AWS_XRAY_DAEMON_ADDRESS, AWS_XRAY_TRACING_NAME
- Trace Context: Propagated via HTTP headers (X-Amzn-Trace-Id)

**Traces Include**:
- ALB → ECS → Aurora (database queries)
- ALB → ECS → ElastiCache (cache operations)
- Subsegments for each database query and cache operation

---

## Component 12: GitHub Actions Workflow

**NFR Patterns Implemented**:
- Pattern 14: Image Scanning (via ECR)

**NFR Requirements Supported**:
- NFR-6 (Maintainability): Automated builds, <5 min deployment

**Workflow Steps**:
1. Checkout source code
2. Configure AWS credentials (OIDC)
3. Login to ECR
4. Build Docker image (multi-stage build)
5. Tag image `sha-<git-commit-hash>`
6. Push to ECR (triggers image scan)
7. Update ECS task definition (new image URI)
8. Deploy to ECS service (triggers rolling update)
9. Wait for service steady state

**Trigger**: Push to main branch

---

## Component Summary

| Component | AWS Service | NFR Patterns | Lines of Code (CDK) |
|-----------|-------------|--------------|---------------------|
| 1. ALB | Application Load Balancer | 1, 5, 10 | ~80 lines |
| 2. ECS Cluster | ECS | 4, 5 | ~15 lines |
| 3. ECS Service | ECS | 2, 15, 16 | ~30 lines |
| 4. Task Definition | ECS | 6, 9, 11 | ~60 lines |
| 5. Auto-Scaling Policy | Application Auto Scaling | 4 | ~20 lines |
| 6. Target Group | ALB | 1, 2 | ~30 lines (part of ALB) |
| 7. Task Execution Role | IAM | 11, 12 | ~25 lines |
| 8. Task Role | IAM | 8, 12 | ~20 lines |
| 9. ECR Repository | ECR | 14 | ~15 lines |
| 10. CloudWatch Log Group | CloudWatch Logs | 17 | ~10 lines |
| 11. X-Ray Integration | X-Ray | 8 | ~10 lines (env vars) |
| 12. GitHub Actions | GitHub Actions | 14 | ~100 lines (YAML) |

**Total Estimated CDK Code**: ~315 lines Python

---

## Component Dependencies

```
GitHub Actions Workflow
        │
        ▼
    ECR Repository ───────┐
                         │
                         ▼
                  Task Definition ──────┐
                         │              │
                         │              ▼
Task Execution Role ─────┤         Task Role
                         │              │
                         ▼              │
                    ECS Service ────────┘
                         │
                         ├──────▶ Auto-Scaling Policy
                         │
                         ▼
                   Target Group
                         │
                         ▼
                        ALB
                         │
                         ▼
                  CloudWatch Logs
                  AWS X-Ray
```

**External Dependencies**:
- Unit 1 (Network): VPC, subnets, security groups
- Unit 2 (Database): Aurora endpoint, DATABASE_URL secret
- Unit 3 (Cache): ElastiCache endpoint, REDIS_URI secret
- Unit 7 (Observability): S3 bucket for ALB access logs (future)

---

## References

- Domain Entities (detailed attributes): `../functional-design/domain-entities.md`
- NFR Patterns: `nfr-patterns.md`
- NFR Requirements: `../nfr-requirements/nfr-assessment.md`
- Technology Stack: `../nfr-requirements/technology-stack.md`
