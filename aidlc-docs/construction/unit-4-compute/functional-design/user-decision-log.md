# Unit 4: Compute Infrastructure - User Decision Log

## Overview

This document records all user decisions made during the functional design of Unit 4: Compute Infrastructure. Each decision includes rationale, impact analysis, and traceability to business rules.

**Decision Date**: 2026-06-12  
**Unit**: 4 of 8 (Compute Infrastructure)  
**Total Decisions**: 13 (10 primary questions + 3 clarifications)

---

## Decision 1: ALB Certificate and Domain Configuration

**Question**: What domain name and ACM certificate should the ALB use?

**User Decision**: **Option A** - Use existing ACM certificate for `newsletter.crearerd.people.aws.dev`

**Domain Name**: `newsletter.crearerd.people.aws.dev`

**Rationale**:
- Existing ACM certificate already provisioned and validated
- Domain DNS already configured
- Production-ready HTTPS configuration
- No additional setup or cost for certificate

**Impact**:
- ALB HTTPS listener will use existing ACM certificate
- HTTP traffic will be redirected to HTTPS
- No manual certificate management required
- SSL/TLS Labs grade A expected

**Cost Impact**: $0 (ACM certificates are free)

**Implementation**:
- ALB HTTPS listener certificate ARN references existing cert
- ALB HTTP listener redirects to HTTPS (port 80 → 443)

**Business Rules**: BR-COMPUTE-001 (HTTP→HTTPS redirect), BR-COMPUTE-002 (ACM certificate)

**Traceability**: questions.md Q1

---

## Decision 2: ECS Task Resource Sizing

**Question**: Are the proposed ECS task resources (0.5 vCPU, 1 GB RAM) appropriate for the expected workload?

**User Decision**: **Option B** - Increase to 1 vCPU / 2 GB RAM

**Rationale**:
- Application handles moderate traffic (100-500 req/min expected)
- 0.5 vCPU may cause CPU throttling under load
- 2 GB RAM provides headroom for connection pooling and caching
- Fargate pricing scales linearly, modest cost increase acceptable

**Impact**:
- Task definition: cpu = "1024" (1 vCPU), memory = "2048" (2 GB)
- Improved performance under load
- Lower CPU utilization % = more headroom for traffic spikes
- Auto-scaling triggers at 70% CPU = ~140 requests/min capacity

**Cost Impact**:
- **Before** (0.5 vCPU / 1 GB): $0.04862/hour per task = $71.27/month for 2 tasks
- **After** (1 vCPU / 2 GB): $0.08870/hour per task = $130.00/month for 2 tasks
- **Difference**: +$58.73/month baseline (+82% increase)
- **Max cost** (10 tasks): $650/month (vs. $356 with 0.5 vCPU)

**Implementation**:
- Task definition cpu and memory fields updated
- Auto-scaling thresholds remain percentage-based (70% CPU)

**Business Rules**: BR-COMPUTE-006 (task resource allocation)

**Traceability**: questions.md Q2

---

## Decision 3: Auto-Scaling Parameters

**Question**: Are the proposed auto-scaling parameters acceptable?

**User Decision**: **Option A** - Accept proposed configuration

**Configuration Accepted**:
- **Target Metric**: CPU utilization
- **Target Value**: 70%
- **Min Capacity**: 2 tasks
- **Max Capacity**: 10 tasks
- **Scale-Out Cooldown**: 60 seconds
- **Scale-In Cooldown**: 300 seconds

**Rationale**:
- 70% CPU target balances utilization and headroom
- Min 2 tasks ensures Multi-AZ high availability
- Max 10 tasks provides cost cap ($650/month max with 1 vCPU / 2 GB)
- 60s scale-out cooldown allows quick response to traffic spikes
- 300s scale-in cooldown prevents premature scale-in during variable traffic

**Impact**:
- Auto-scaling responds to CPU utilization increases within 60 seconds
- Service maintains at least 2 tasks (1 per AZ) at all times
- Service caps at 10 tasks regardless of CPU utilization
- Gradual scaling prevents over-provisioning

**Cost Impact**:
- **Baseline**: 2 tasks × $0.08870/hour = $130/month
- **Average** (4 tasks): $260/month
- **Maximum**: 10 tasks × $0.08870/hour = $650/month

**Implementation**:
- Target tracking scaling policy with CPU metric
- Application Auto Scaling min/max capacity settings
- CloudWatch alarm triggers scaling actions

**Business Rules**: BR-COMPUTE-013 (70% CPU target), BR-COMPUTE-014 (min 2 tasks), BR-COMPUTE-015 (max 10 tasks), BR-COMPUTE-016 (scale-out cooldown), BR-COMPUTE-017 (scale-in cooldown), BR-COMPUTE-018 (gradual scaling)

**Traceability**: questions.md Q3

---

## Decision 4: Health Check Configuration

**Question**: What health check configuration should the ALB use?

**User Decision**: **Option A** - Accept proposed configuration

**Configuration Accepted**:
- **Path**: /health_check
- **Protocol**: HTTP
- **Port**: 8000
- **Interval**: 30 seconds
- **Timeout**: 5 seconds
- **Healthy Threshold**: 2 consecutive successes
- **Unhealthy Threshold**: 3 consecutive failures
- **Health Check Grace Period**: 60 seconds

**Rationale**:
- 30-second interval balances responsiveness and cost
- 2 consecutive successes prevents false positives
- 3 consecutive failures allows transient errors
- 60-second grace period allows database connection establishment at startup

**Impact**:
- New tasks become healthy within ~60 seconds (grace period + 2 checks)
- Failed tasks deregister within ~90 seconds (3 checks × 30s)
- Health check cost: 2 checks/min × 2 tasks = 86,400 checks/month (negligible cost)

**Cost Impact**: <$1/month (health checks are very low cost)

**Implementation**:
- ALB target group health check settings
- ECS service health check grace period
- Application `/health_check` endpoint implementation

**Business Rules**: BR-COMPUTE-005 (health check interval), BR-COMPUTE-008 (grace period), BR-COMPUTE-009 (healthy threshold), BR-COMPUTE-010 (unhealthy threshold)

**Traceability**: questions.md Q4

---

## Decision 5: ECS Task IAM Permissions

**Question**: What IAM permissions should the ECS task role have?

**User Decision**: **Option A** - Accept proposed permissions (minimal access)

**Permissions Accepted**:
- **Secrets Manager**: GetSecretValue on `zero2prod/database/*` and `zero2prod/cache/*`
- **CloudWatch Logs**: CreateLogStream, PutLogEvents
- **X-Ray**: PutTraceSegments, PutTelemetryRecords (added per Clarification Q3)
- **No** IAM database authentication (use password from Secrets Manager)
- **No** S3 permissions (not needed yet)
- **No** SES permissions (worker handles emails, not web tier)

**Rationale**:
- Least privilege principle: grant only required permissions
- Secrets Manager access limited to application secrets (not all secrets)
- IAM database authentication adds complexity without security benefit (Secrets Manager already rotates passwords)
- S3 and SES can be added later if needed

**Impact**:
- Task role follows security best practices
- Minimal blast radius if task role compromised
- No cross-service access beyond required dependencies

**Cost Impact**: $0 (IAM roles are free)

**Implementation**:
- Task role inline policy with scoped permissions
- Task execution role separate from task role
- CloudTrail logs all IAM actions for audit

**Business Rules**: BR-COMPUTE-030 (least privilege IAM)

**Traceability**: questions.md Q5

---

## Decision 6: Container Image Strategy

**Question**: What container image build and push strategy should we use?

**User Decision**: **Option B** - GitHub Actions CI/CD pipeline

**Image Tag Strategy**: `sha-<git-commit-hash>` (immutable tags)

**Rationale**:
- Automated builds on push to main branch
- CI/CD pipeline ensures consistent builds
- Immutable tags provide traceability from running task to source code
- Unit 8 (CI/CD Infrastructure) will extend with additional stages (tests, security scanning)

**Impact**:
- GitHub Actions workflow builds Docker image on every push to main
- Image pushed to ECR with `sha-<hash>` tag
- Task definition updated with new image URI
- ECS service updated to trigger rolling deployment

**Cost Impact**:
- **GitHub Actions**: Free for public repos, $0.008/min for private repos (~5 min build = $0.04/build)
- **ECR Storage**: $0.10/GB/month (~500 MB per image = $0.05/month per image)
- **ECR Transfer**: $0.00 (within AWS region)
- **Total**: ~$1-2/month for storage + negligible build cost

**Implementation**:
- `.github/workflows/deploy-ecs.yml` workflow file
- Dockerfile multi-stage build (builder + runtime)
- ECR repository with immutable tags
- GitHub OIDC role for secure AWS access

**Business Rules**: BR-COMPUTE-033 (sha-based image tags)

**Traceability**: questions.md Q6, clarification-questions.md Q2

---

## Decision 7: Environment Variable Configuration

**Question**: Which environment variables should be loaded from Secrets Manager vs. static values in task definition?

**User Decision**: **Option A** - Accept proposed configuration

**Configuration Accepted**:
- **From Secrets Manager** (sensitive):
  - `DATABASE_URL` (Aurora connection string with password)
  - `REDIS_URI` (ElastiCache connection string)
  - `HMAC_SECRET` (session signing key)
- **Static in Task Definition** (non-sensitive):
  - `APP_ENVIRONMENT=production`
  - `APP_LOG_LEVEL=info`
  - `APP_APPLICATION__PORT=8000`
  - `APP_APPLICATION__HOST=0.0.0.0`

**Rationale**:
- Clear separation: sensitive data in Secrets Manager, non-sensitive in task definition
- Secrets Manager supports automatic rotation
- Static values can be updated via task definition revision
- Configuration follows 12-factor app principles

**Impact**:
- Task fails to start if secrets unavailable (fail-fast)
- Secrets are never logged or exposed in task definition JSON
- Configuration changes require task definition update (non-sensitive) or secret update (sensitive)

**Cost Impact**: $0.40/month per secret × 3 secrets = $1.20/month

**Implementation**:
- Task definition `secrets` field for Secrets Manager references
- Task definition `environment` field for static variables
- Task execution role has GetSecretValue permission

**Business Rules**: BR-COMPUTE-025 (Secrets Manager integration), BR-COMPUTE-028 (static environment variables)

**Traceability**: questions.md Q7

---

## Decision 8: Deployment Strategy

**Question**: What deployment strategy should the ECS service use?

**User Decision**: **Option A** - Rolling Update

**Deployment Configuration Accepted**:
- **Minimum Healthy Percent**: 100%
- **Maximum Percent**: 200%

**Rationale**:
- Rolling update is simple and proven for moderate-traffic applications
- 100% minimum ensures zero downtime during deployments
- 200% maximum allows full new task set to start before draining old tasks
- Blue/green and canary add complexity without clear benefit for this workload

**Impact**:
- Deployments launch 2 new tasks (total 4: 2 old + 2 new)
- New tasks must pass health checks before old tasks drain
- Deployment time: ~3-5 minutes (1 min health check + 300s connection draining)
- Failed deployments automatically stop (no rollback needed, old tasks remain)

**Cost Impact**: Minimal (double capacity for ~5 minutes during deployment)

**Implementation**:
- ECS service deployment configuration
- Target group health check validates new tasks
- Connection draining allows graceful shutdown

**Business Rules**: BR-COMPUTE-019 (rolling update), BR-COMPUTE-020 (100% min healthy), BR-COMPUTE-021 (200% max), BR-COMPUTE-022 (health check before traffic), BR-COMPUTE-023 (connection draining), BR-COMPUTE-024 (rollback on failure)

**Traceability**: questions.md Q8

---

## Decision 9: ALB Access Logging

**Question**: Should ALB access logging be enabled?

**User Decision**: **Option B** - Enable access logging with 30-day retention

**S3 Bucket**: Created in **Unit 7** (Observability Infrastructure)

**Rationale**:
- Access logs provide audit trail for HTTP requests
- 30-day retention balances troubleshooting capability and cost
- Required for SECURITY-02 (audit logging)
- S3 bucket in Unit 7 provides centralized logging infrastructure

**Impact**:
- ALB writes access logs to S3 bucket every 5 minutes
- Logs include request/response details, client IP, latency, status codes
- 30-day lifecycle policy automatically deletes old logs
- Logs available for analysis with Athena or CloudWatch Logs Insights

**Cost Impact**:
- **S3 Storage**: ~5 GB/month × $0.023/GB = $0.12/month
- **S3 PUT Requests**: ~8,640 requests/month × $0.005/1000 = $0.04/month
- **Total**: ~$0.16/month (negligible)

**Implementation**:
- ALB access_logs_enabled = true
- ALB access_logs_bucket references S3 bucket from Unit 7
- S3 bucket policy allows ALB to write logs
- Lifecycle policy deletes logs after 30 days

**Business Rules**: BR-COMPUTE-035 (ALB access logging), SECURITY-02 (audit logging)

**Traceability**: questions.md Q9

---

## Decision 10: ECS Service Desired Count

**Question**: Is a desired count of 2 tasks appropriate for production?

**User Decision**: **Option A** - 2 tasks (1 per AZ, minimal HA)

**Rationale**:
- 2 tasks provide Multi-AZ high availability (survive single AZ failure)
- Auto-scaling will add tasks during high traffic
- Cost-efficient baseline for moderate-traffic application
- Minimal HA is acceptable for newsletter service (not mission-critical)

**Impact**:
- Normal operation: 2 tasks running (1 in us-east-1a, 1 in us-east-1b)
- Single task failure: ALB routes all traffic to remaining healthy task
- Single AZ failure: All traffic routes to remaining AZ
- High traffic: Auto-scaling adds tasks up to 10

**Cost Impact**:
- **Baseline**: 2 tasks × $0.08870/hour × 730 hours/month = $130/month
- **Alternative** (4 tasks): $260/month (+$130/month for better redundancy)
- **Decision**: Baseline cost acceptable, auto-scaling provides headroom

**Implementation**:
- ECS service desired_count = 2
- Auto-scaling min_capacity = 2 (cannot scale below desired count)
- Tasks distributed across 2 AZs

**Business Rules**: BR-COMPUTE-012 (desired count multi-AZ), BR-COMPUTE-014 (min 2 tasks)

**Traceability**: questions.md Q10

---

## Clarification 1: Health Check Validation Scope

**Question**: Should the health check endpoint validate both database and cache connectivity, or just database?

**User Decision**: **Option A** - Database connectivity only

**Rationale**:
- Database is critical path: application cannot function without database
- Cache is non-critical: sessions degrade gracefully if cache unavailable (fall back to database)
- Fast health checks: database query is faster than database + cache validation
- Cache failures should not trigger task replacement (alert + investigate, don't restart)

**Impact**:
- `/health_check` endpoint executes `SELECT 1` against Aurora
- Returns 200 OK if database query succeeds
- Returns 503 Service Unavailable if database query fails
- Cache connectivity issues are logged but do not fail health check

**Cost Impact**: $0 (simplifies health check logic)

**Implementation**:
- Application `/health_check` endpoint implementation
- Database connection pool validation
- Cache connectivity monitoring via CloudWatch metrics (not health check)

**Business Rules**: BR-COMPUTE-011 (database connectivity validation)

**Traceability**: clarification-questions.md Q1

---

## Clarification 2: Container Image Strategy Confirmation

**Question**: Confirm GitHub Actions CI/CD pipeline (Option B) from follow-up field.

**User Decision**: **Confirmed** - GitHub Actions CI/CD pipeline

**Rationale**: (See Decision 6)

**Traceability**: clarification-questions.md Q2

---

## Clarification 3: Observability Environment Variables

**Question**: Should we add environment variables for feature flags or observability integrations (e.g., AWS X-Ray)?

**User Decision**: **Option A** - Add AWS X-Ray environment variables

**Environment Variables Added**:
- `AWS_XRAY_DAEMON_ADDRESS=xray-daemon:2000`
- `AWS_XRAY_TRACING_NAME=zero2prod-web`
- `AWS_REGION=us-east-1`

**Rationale**:
- AWS X-Ray provides distributed tracing for request flows across services
- Minimal overhead: X-Ray SDK integrated into application
- Valuable for troubleshooting latency and errors
- No additional infrastructure needed (X-Ray daemon runs as sidecar)

**Impact**:
- Application sends trace segments to X-Ray daemon
- X-Ray console displays request flows (ALB → ECS → Aurora/ElastiCache)
- Task role requires X-Ray permissions (PutTraceSegments, PutTelemetryRecords)

**Cost Impact**:
- **X-Ray**: First 100,000 traces/month free, then $5.00/million traces
- **Expected**: <10,000 traces/month = $0 (within free tier)

**Implementation**:
- Task definition environment variables
- Task role X-Ray permissions
- Application X-Ray SDK initialization
- X-Ray daemon sidecar container (optional, or use Fargate X-Ray integration)

**Business Rules**: BR-COMPUTE-029 (X-Ray tracing configuration)

**Traceability**: clarification-questions.md Q3

---

## Decision Summary Table

| Decision # | Topic | User Choice | Cost Impact | Business Rules |
|-----------|-------|-------------|-------------|----------------|
| 1 | Domain & Certificate | Existing cert for `newsletter.crearerd.people.aws.dev` | $0 | BR-COMPUTE-001, BR-COMPUTE-002 |
| 2 | Task Resources | 1 vCPU / 2 GB RAM | +$58.73/month baseline | BR-COMPUTE-006 |
| 3 | Auto-Scaling | 70% CPU, 2-10 tasks, 60s/300s cooldowns | $130-650/month | BR-COMPUTE-013 to BR-COMPUTE-018 |
| 4 | Health Checks | 30s interval, 2/3 thresholds, 60s grace | <$1/month | BR-COMPUTE-005, BR-COMPUTE-008 to BR-COMPUTE-010 |
| 5 | IAM Permissions | Minimal (Secrets Manager, CloudWatch, X-Ray) | $0 | BR-COMPUTE-030 |
| 6 | Image Strategy | GitHub Actions + sha tags | ~$1-2/month | BR-COMPUTE-033 |
| 7 | Environment Vars | Secrets Manager (sensitive) + static (non-sensitive) | $1.20/month | BR-COMPUTE-025, BR-COMPUTE-028 |
| 8 | Deployment | Rolling update 100%/200% | Minimal | BR-COMPUTE-019 to BR-COMPUTE-024 |
| 9 | ALB Logging | Enabled, 30-day retention, S3 in Unit 7 | ~$0.16/month | BR-COMPUTE-035 |
| 10 | Desired Count | 2 tasks (Multi-AZ) | $130/month baseline | BR-COMPUTE-012, BR-COMPUTE-014 |
| C1 | Health Check Scope | Database only (not cache) | $0 | BR-COMPUTE-011 |
| C2 | Image Strategy | Confirmed GitHub Actions | (See #6) | (See #6) |
| C3 | Observability | AWS X-Ray tracing enabled | $0 (free tier) | BR-COMPUTE-029 |

---

## Total Cost Summary

### Baseline Cost (2 Tasks, Normal Operation)
- **ECS Fargate**: 2 tasks × 1 vCPU / 2 GB × $0.08870/hour × 730 hours = **$130.00/month**
- **Secrets Manager**: 3 secrets × $0.40/month = **$1.20/month**
- **ALB**: $16.20/month (fixed) + $0.008/LCU-hour × ~10 LCUs = **~$25/month**
- **ECR Storage**: ~3 images × 500 MB × $0.10/GB = **$0.15/month**
- **CloudWatch Logs**: ~5 GB/month × $0.50/GB = **$2.50/month**
- **ALB Access Logs**: ~5 GB/month × $0.023/GB = **$0.12/month**
- **X-Ray**: <10,000 traces/month = **$0** (free tier)
- **Total Baseline**: **~$159/month**

### Maximum Cost (10 Tasks, High Traffic)
- **ECS Fargate**: 10 tasks × $0.08870/hour × 730 hours = **$650.00/month**
- **Other Services**: Same as baseline = **$29.00/month**
- **Total Maximum**: **~$679/month**

### Cost Comparison vs. Original Proposal (0.5 vCPU / 1 GB)
- **Original Baseline** (0.5 vCPU / 1 GB, 2 tasks): ~$100/month
- **Selected Baseline** (1 vCPU / 2 GB, 2 tasks): ~$159/month
- **Difference**: +$59/month (+59%)
- **Justification**: Better performance, lower CPU utilization, headroom for traffic spikes

---

## Compliance Summary

### Security Extension Rules
| Rule | Status | Implementation |
|------|--------|----------------|
| SECURITY-01 | ✅ Compliant | Secrets in Secrets Manager (encrypted at rest) |
| SECURITY-02 | ✅ Compliant | TLS 1.2+ (ALB), ALB access logs to S3 |
| SECURITY-03 | ✅ Compliant | No hardcoded secrets, Secrets Manager integration |
| SECURITY-04 | ✅ Compliant | Least privilege IAM roles |
| SECURITY-05 | ✅ Compliant | Tasks in private subnets, no public IP |
| SECURITY-06 | ✅ Compliant | CloudTrail logs all API calls (account-level) |

**Overall**: 100% compliant (6/6 rules met)

---

## References

- Questions: `questions.md`
- Clarifications: `clarification-questions.md`
- Business Logic: `business-logic-model.md`
- Domain Entities: `domain-entities.md`
- Business Rules: `business-rules.md`
