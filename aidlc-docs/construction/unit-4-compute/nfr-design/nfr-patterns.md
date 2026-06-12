# Unit 4: Compute Infrastructure - NFR Design Patterns

## Overview

This document defines the design patterns used to implement non-functional requirements for the ECS Fargate compute infrastructure. Each pattern maps to specific NFR requirements and business rules.

**Design Date**: 2026-06-12  
**Unit**: 4 of 8 (Compute Infrastructure)  
**Total Patterns**: 18

---

## Resilience Patterns

### Pattern 1: Auto-Healing via Health Checks

**Purpose**: Automatically detect and replace failed ECS tasks

**NFR Requirement**: NFR-5 (Reliability - MTTD <90s, MTTR <2min)

**Implementation**:
- ALB performs HTTP health checks every 30 seconds on `/health_check`
- Health check validates database connectivity (critical path)
- 3 consecutive failures (90 seconds) marks task unhealthy
- ECS automatically terminates unhealthy task and launches replacement
- Replacement task healthy within 120 seconds (60s grace + 60s health check)

**Benefits**:
- No manual intervention required for task failures
- Fast failure detection (90 seconds)
- Quick recovery (2 minutes total: MTTD + MTTR)

**Trade-offs**:
- Health checks add minor load to application
- False positives possible (network blips) - mitigated by 3-failure threshold

**Traceability**: BR-COMPUTE-005, BR-COMPUTE-009 to BR-COMPUTE-011, NFR-5

---

### Pattern 2: Graceful Shutdown via Connection Draining

**Purpose**: Allow in-flight requests to complete before task termination

**NFR Requirement**: NFR-3 (Availability - zero downtime deployments)

**Implementation**:
- Target group deregistration delay = 300 seconds
- When task marked for termination:
  1. ALB deregisters task from target group (no new requests)
  2. Wait up to 300 seconds for existing connections to complete
  3. Send SIGTERM to container (application graceful shutdown)
  4. Wait 30 seconds for container to exit
  5. Send SIGKILL if still running

**Benefits**:
- No dropped connections during deployments
- Clean application shutdown (close database connections, flush logs)

**Trade-offs**:
- Longer deployment time (300s drain + new task startup)
- Tasks with long-running connections may delay deployments

**Traceability**: BR-COMPUTE-023, NFR-3

---

### Pattern 3: Retry with Exponential Backoff (Application-Level)

**Purpose**: Retry transient failures without overwhelming downstream services

**NFR Requirement**: NFR-5 (Reliability)

**Implementation**:
- Application implements retry logic for database and cache connections
- Exponential backoff: 100ms, 200ms, 400ms, 800ms, 1600ms (max 5 retries)
- Only retry idempotent operations (SELECT queries, GET requests)
- Fail fast for non-idempotent operations (INSERT, UPDATE, DELETE)

**Benefits**:
- Resilience to transient network issues
- Avoids thundering herd problem (exponential backoff)

**Trade-offs**:
- Increased latency for failed requests
- Complexity in application code

**Traceability**: BR-COMPUTE-027, NFR-5

---

## Scalability Patterns

### Pattern 4: Horizontal Auto-Scaling (Target Tracking)

**Purpose**: Automatically scale task count based on CPU utilization

**NFR Requirement**: NFR-1 (Scalability - 2-10 tasks, 70% CPU target)

**Implementation**:
- CloudWatch collects CPU utilization metrics every 60 seconds
- Application Auto Scaling evaluates target (70% CPU)
- Scale-out trigger: avg CPU >70% for 1 minute → add 1 task
- Scale-in trigger: avg CPU <70% for 1 minute → remove 1 task
- Cooldown: 60s scale-out, 300s scale-in

**Benefits**:
- Automatic response to traffic changes
- Cost optimization (scale down during low traffic)
- Predictable behavior (target-based)

**Trade-offs**:
- CPU may not be perfect metric for all workloads
- Lag between traffic spike and scale-out (60-120 seconds)

**Traceability**: BR-COMPUTE-013 to BR-COMPUTE-018, NFR-1

---

### Pattern 5: Multi-AZ Load Distribution

**Purpose**: Distribute traffic across multiple availability zones for fault tolerance

**NFR Requirement**: NFR-3 (Availability - 99.9% uptime, AZ failure tolerance)

**Implementation**:
- ALB deployed in 2 public subnets (us-east-1a, us-east-1b)
- ECS tasks deployed in 2 private subnets (us-east-1a, us-east-1b)
- ALB round-robin load balancing across all healthy tasks in all AZs
- ECS placement strategy ensures even distribution across AZs

**Benefits**:
- Survive single AZ failure (entire AZ can go down)
- Reduced latency (users routed to nearest AZ)

**Trade-offs**:
- Cross-AZ data transfer costs (minimal for HTTP traffic)
- Slightly higher complexity (2 subnets vs 1)

**Traceability**: BR-COMPUTE-004, BR-COMPUTE-012, NFR-3

---

### Pattern 6: Stateless Task Design

**Purpose**: Enable horizontal scaling without session affinity requirements

**NFR Requirement**: NFR-1 (Scalability)

**Implementation**:
- All session state stored in ElastiCache (external to tasks)
- No local filesystem state (ephemeral Fargate storage)
- Tasks are interchangeable (any task can handle any request)
- ALB uses round-robin routing (no sticky sessions)

**Benefits**:
- Simple horizontal scaling (add/remove tasks freely)
- Fast task replacement (no state migration)
- Simplified load balancing (no affinity tracking)

**Trade-offs**:
- Dependency on ElastiCache availability
- Network latency for session lookups

**Traceability**: Unit 3 (Cache Infrastructure), NFR-1

---

## Performance Patterns

### Pattern 7: Connection Pooling (Application-Level)

**Purpose**: Reduce database and cache connection overhead

**NFR Requirement**: NFR-2 (Performance - <200ms p50 response time)

**Implementation**:
- Database connection pool: 2-10 connections per task (sqlx pool)
- Cache connection pool: 2-10 connections per task (deadpool-redis)
- Connections kept alive, reused across requests
- Pool validates connections before use (detect stale connections)

**Benefits**:
- Eliminate connection establishment latency (50-100ms per connection)
- Reduced load on database and cache (fewer connections)

**Trade-offs**:
- Memory overhead (idle connections)
- Stale connection handling complexity

**Traceability**: NFR-2, Unit 2 (Database), Unit 3 (Cache)

---

### Pattern 8: Distributed Tracing

**Purpose**: Identify performance bottlenecks across service boundaries

**NFR Requirement**: NFR-2 (Performance optimization), NFR-5 (Reliability - error diagnosis)

**Implementation**:
- AWS X-Ray SDK integrated into application
- Trace context propagated via HTTP headers (X-Amzn-Trace-Id)
- Traces include ALB → ECS → Aurora → ElastiCache
- Subsegments track database queries, cache operations, external calls

**Benefits**:
- Visualize end-to-end request flow
- Identify slow queries and operations
- Correlate errors across services

**Trade-offs**:
- Minor overhead (~1-2% CPU, <1ms latency)
- Trace sampling required at high traffic (100% sampling up to 100k traces/month free)

**Traceability**: BR-COMPUTE-029, NFR-2, NFR-5

---

### Pattern 9: Right-Sizing (Task Resources)

**Purpose**: Balance performance and cost through appropriate resource allocation

**NFR Requirement**: NFR-2 (Performance), NFR-7 (Cost Optimization)

**Implementation**:
- Task allocation: 1 vCPU (1024 CPU units), 2 GB RAM (2048 MB)
- CPU sufficient for moderate traffic (100-500 req/min)
- RAM sufficient for application + connection pools + OS overhead
- Headroom: 70% CPU target = 30% buffer for spikes

**Benefits**:
- Adequate performance for workload
- Cost-effective ($130/month for 2 tasks)
- Headroom for traffic spikes

**Trade-offs**:
- May need adjustment based on actual usage patterns
- Under-provisioning risks CPU throttling

**Traceability**: BR-COMPUTE-006, NFR-2, NFR-7, User Decision Q2

---

## Security Patterns

### Pattern 10: TLS Termination at Load Balancer

**Purpose**: Encrypt HTTP traffic in transit

**NFR Requirement**: NFR-4 (Security - SECURITY-02 encryption in transit)

**Implementation**:
- ALB HTTPS listener (port 443) with ACM certificate
- TLS 1.2+ enforced (security policy: ELBSecurityPolicy-TLS13-1-2-2021-06)
- HTTP listener (port 80) redirects to HTTPS with 301
- ALB → ECS traffic unencrypted (within VPC, private network)

**Benefits**:
- Strong encryption (TLS 1.3 preferred, TLS 1.2 fallback)
- Offload TLS overhead from application
- Automatic certificate renewal (ACM)

**Trade-offs**:
- ALB → ECS traffic unencrypted (acceptable within VPC)
- Older clients may not support TLS 1.2+ (negligible in 2026)

**Traceability**: BR-COMPUTE-001, BR-COMPUTE-002, NFR-4, SECURITY-02

---

### Pattern 11: Secrets Management via AWS Secrets Manager

**Purpose**: Securely store and rotate sensitive configuration

**NFR Requirement**: NFR-4 (Security - SECURITY-03 no hardcoded secrets)

**Implementation**:
- DATABASE_URL, REDIS_URI, HMAC_SECRET stored in Secrets Manager
- KMS encryption at rest (AWS-managed key)
- Task execution role has GetSecretValue permission (scoped to specific secrets)
- ECS retrieves secrets at task startup, injects as environment variables
- Secrets never appear in task definition JSON or CloudWatch logs

**Benefits**:
- Centralized secret management
- Automatic rotation support (RDS passwords)
- Audit trail (CloudTrail logs all GetSecretValue calls)

**Trade-offs**:
- Slight startup latency (secrets retrieval adds ~100ms)
- Cost ($0.40/secret/month)

**Traceability**: BR-COMPUTE-025, BR-COMPUTE-027, NFR-4, SECURITY-03

---

### Pattern 12: Least Privilege IAM

**Purpose**: Minimize blast radius of security breaches

**NFR Requirement**: NFR-4 (Security - SECURITY-04 least privilege)

**Implementation**:
- **Task Execution Role** (ECS agent): ECR pull, CloudWatch logs write, Secrets Manager read
- **Task Role** (application): Secrets Manager read (runtime), X-Ray write, CloudWatch logs write
- All policies scoped to specific resources (no `*` wildcards)
- No write permissions to Secrets Manager (read-only)

**Benefits**:
- Minimal permissions reduce security risk
- IAM Access Analyzer validates policies

**Trade-offs**:
- More granular permissions = more complex policies
- Policy updates required when adding new resources

**Traceability**: BR-COMPUTE-030, NFR-4, SECURITY-04, User Decision Q5

---

### Pattern 13: Network Isolation (Private Subnets)

**Purpose**: Prevent external access to ECS tasks

**NFR Requirement**: NFR-4 (Security - SECURITY-05 network isolation)

**Implementation**:
- ECS tasks deployed in private subnets (no internet gateway route)
- Tasks have no public IP addresses
- Ingress: Only ALB security group can reach port 8000 on tasks
- Egress: Tasks can reach Aurora (port 5432), ElastiCache (port 6379), VPC endpoints

**Benefits**:
- No direct internet access to tasks
- Defense in depth (ALB + security groups + private subnets)

**Trade-offs**:
- VPC endpoints required for AWS services (ECR, Secrets Manager, CloudWatch)
- Debugging more complex (no SSH, must use ECS Exec)

**Traceability**: BR-COMPUTE-005, NFR-4, SECURITY-05, Unit 1 (Network)

---

### Pattern 14: Image Scanning

**Purpose**: Detect security vulnerabilities in container images

**NFR Requirement**: NFR-4 (Security), NFR-6 (Maintainability)

**Implementation**:
- ECR image scanning enabled on push
- Scan results available in ECR console
- GitHub Actions workflow can fail build on critical vulnerabilities (optional)

**Benefits**:
- Early detection of vulnerable dependencies
- Compliance requirement for some organizations

**Trade-offs**:
- Scan time adds ~30 seconds to build
- False positives require triage

**Traceability**: BR-COMPUTE-032, NFR-4, Technology Decision 3 (ECR)

---

## Availability Patterns

### Pattern 15: Rolling Deployment (Zero Downtime)

**Purpose**: Deploy new versions without service interruption

**NFR Requirement**: NFR-3 (Availability - zero downtime deployments)

**Implementation**:
1. Launch 2 new tasks with new image (total 4: 2 old + 2 new)
2. New tasks pass health checks (2 consecutive successes = ~60s)
3. ALB registers new tasks (start receiving traffic)
4. ALB deregisters old tasks (stop receiving new requests)
5. Wait for connection draining (up to 300s)
6. Terminate old tasks

**Benefits**:
- Zero downtime (at least 2 tasks always healthy)
- Automatic rollback if new tasks fail health checks

**Trade-offs**:
- Deployment time ~5 minutes (startup + health check + draining)
- Temporary double capacity (4 tasks for ~5 minutes)

**Traceability**: BR-COMPUTE-019 to BR-COMPUTE-024, NFR-3, User Decision Q8

---

### Pattern 16: Health Check Grace Period

**Purpose**: Allow task initialization before health checks begin

**NFR Requirement**: NFR-3 (Availability), NFR-5 (Reliability)

**Implementation**:
- ECS service health check grace period = 60 seconds
- During grace period: task is not health-checked by ALB
- After grace period: ALB begins health checks every 30 seconds
- Purpose: Allow database connections, application startup, warmup

**Benefits**:
- Prevents premature task termination during startup
- Reduces false positives (task not yet ready)

**Trade-offs**:
- Truly failed tasks take longer to detect (60s grace + 90s health checks = 150s)

**Traceability**: BR-COMPUTE-008, NFR-3, NFR-5

---

## Observability Patterns

### Pattern 17: Structured Logging

**Purpose**: Enable log analysis and troubleshooting

**NFR Requirement**: NFR-5 (Reliability - troubleshooting), NFR-6 (Maintainability)

**Implementation**:
- Application logs in JSON format (tracing-bunyan-formatter)
- Logs include: timestamp, level, message, request_id, trace_id, user_id
- CloudWatch Logs aggregates logs from all tasks
- Log retention: 30 days
- CloudWatch Logs Insights for queries

**Benefits**:
- Structured logs easy to query (filter by request_id, user_id)
- Correlation with X-Ray traces (trace_id)
- 30-day retention balances cost and troubleshooting

**Trade-offs**:
- JSON logs more verbose than plaintext
- Log volume = ~5 GB/month ($2.50 cost)

**Traceability**: BR-COMPUTE-034, NFR-5, NFR-6

---

### Pattern 18: Centralized Metrics (CloudWatch)

**Purpose**: Monitor infrastructure and application health

**NFR Requirement**: NFR-1 (Scalability - auto-scaling), NFR-5 (Reliability)

**Implementation**:
- **ECS Metrics**: CPU utilization, memory utilization, task count
- **ALB Metrics**: Request count, target response time, 5xx errors, healthy/unhealthy targets
- **X-Ray Metrics**: Latency distribution, error rate, trace count
- **Auto-Scaling**: Consumes CPU utilization metric for scaling decisions

**Benefits**:
- Single pane of glass (CloudWatch console)
- Metrics retained for 15 months
- Alarms can trigger SNS notifications (future)

**Trade-offs**:
- CloudWatch costs scale with metric volume
- Detailed metrics (1-minute granularity) cost extra

**Traceability**: NFR-1, NFR-5, Auto-Scaling Pattern 4

---

## Pattern Summary Matrix

| Pattern | Type | NFR | Risk | Implementation Complexity |
|---------|------|-----|------|---------------------------|
| 1. Auto-Healing | Resilience | NFR-5 | LOW | Simple (ALB health checks) |
| 2. Connection Draining | Resilience | NFR-3 | LOW | Simple (target group config) |
| 3. Retry with Backoff | Resilience | NFR-5 | MEDIUM | Medium (application code) |
| 4. Auto-Scaling | Scalability | NFR-1 | LOW | Simple (target tracking) |
| 5. Multi-AZ Distribution | Scalability | NFR-3 | LOW | Simple (ALB + ECS config) |
| 6. Stateless Tasks | Scalability | NFR-1 | LOW | Simple (architecture choice) |
| 7. Connection Pooling | Performance | NFR-2 | MEDIUM | Medium (application code) |
| 8. Distributed Tracing | Performance | NFR-2, NFR-5 | LOW | Medium (X-Ray SDK) |
| 9. Right-Sizing | Performance | NFR-2, NFR-7 | LOW | Simple (task definition) |
| 10. TLS Termination | Security | NFR-4 | LOW | Simple (ALB + ACM) |
| 11. Secrets Management | Security | NFR-4 | LOW | Simple (Secrets Manager) |
| 12. Least Privilege IAM | Security | NFR-4 | LOW | Medium (IAM policies) |
| 13. Network Isolation | Security | NFR-4 | LOW | Simple (private subnets) |
| 14. Image Scanning | Security | NFR-4 | LOW | Simple (ECR config) |
| 15. Rolling Deployment | Availability | NFR-3 | LOW | Simple (ECS config) |
| 16. Health Check Grace | Availability | NFR-3, NFR-5 | LOW | Simple (ECS service config) |
| 17. Structured Logging | Observability | NFR-5, NFR-6 | MEDIUM | Medium (application code) |
| 18. Centralized Metrics | Observability | NFR-1, NFR-5 | LOW | Simple (CloudWatch) |

---

## Pattern Interactions

### Positive Interactions (Synergies)
- **Auto-Healing + Multi-AZ**: Failed tasks replaced quickly without service disruption
- **Distributed Tracing + Structured Logging**: Correlated traces and logs (trace_id)
- **TLS Termination + Network Isolation**: Defense in depth (encryption + access control)
- **Auto-Scaling + Stateless Tasks**: Scaling works seamlessly (no session affinity)
- **Connection Pooling + Right-Sizing**: Efficient resource utilization

### Negative Interactions (Conflicts)
- **Connection Draining + Fast Deployments**: 300s draining slows deployments (acceptable trade-off)
- **Health Check Grace + Fast Failure Detection**: 60s grace delays failure detection (acceptable trade-off)

---

## References

- NFR Requirements: `../nfr-requirements/nfr-assessment.md`
- Technology Stack: `../nfr-requirements/technology-stack.md`
- Business Rules: `../functional-design/business-rules.md`
- User Decisions: `../functional-design/user-decision-log.md`
