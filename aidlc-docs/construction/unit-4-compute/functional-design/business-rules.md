# Unit 4: Compute Infrastructure - Business Rules

## Overview

This document defines all business rules governing the ECS Fargate compute infrastructure deployment. Business rules are categorized by priority: CRITICAL, HIGH, MEDIUM.

**Design Date**: 2026-06-12  
**Unit**: 4 of 8 (Compute Infrastructure)  
**Total Rules**: 35 (13 CRITICAL, 15 HIGH, 7 MEDIUM)

---

## ALB Configuration Rules

### BR-COMPUTE-001: HTTP to HTTPS Redirect (CRITICAL)
**Rule**: All HTTP (port 80) requests MUST be redirected to HTTPS (port 443) with 301 Permanent Redirect status.

**Rationale**: Enforce encryption in transit for all traffic (SECURITY-02).

**Implementation**: ALB HTTP listener default action type = Redirect to HTTPS.

**Validation**: `curl -I http://newsletter.crearerd.people.aws.dev` returns 301 with Location header pointing to HTTPS.

**Traceability**: SECURITY-02 (Encryption in transit)

---

### BR-COMPUTE-002: ACM Certificate Requirement (CRITICAL)
**Rule**: HTTPS listener MUST use ACM certificate for domain `newsletter.crearerd.people.aws.dev`.

**Rationale**: Valid TLS certificate required for secure HTTPS connections.

**Implementation**: HTTPS listener certificate ARN references existing ACM certificate.

**Validation**: `openssl s_client -connect newsletter.crearerd.people.aws.dev:443 -servername newsletter.crearerd.people.aws.dev` shows valid certificate.

**Traceability**: User Decision Q1

---

### BR-COMPUTE-003: Healthy Target Routing Only (CRITICAL)
**Rule**: ALB MUST only route traffic to ECS tasks with "Healthy" status in target group.

**Rationale**: Prevent traffic to failing or starting tasks.

**Implementation**: ALB target group health check with 2 consecutive successes = healthy, 3 consecutive failures = unhealthy.

**Validation**: Terminate task, verify ALB stops routing to it within 90 seconds (3 × 30s interval).

**Traceability**: BR-COMPUTE-009, BR-COMPUTE-010

---

### BR-COMPUTE-004: Multi-AZ Distribution (HIGH)
**Rule**: ALB MUST distribute traffic across all healthy tasks in all availability zones.

**Rationale**: Balanced load distribution and AZ-level fault tolerance.

**Implementation**: ALB deployed in 2 public subnets (us-east-1a, us-east-1b).

**Validation**: Check ALB metrics in CloudWatch for even distribution across AZs.

**Traceability**: Unit 1 (Network Infrastructure)

---

### BR-COMPUTE-005: Health Check Interval (HIGH)
**Rule**: ALB MUST perform health checks every 30 seconds on `/health_check` endpoint.

**Rationale**: Balance between responsiveness and cost.

**Implementation**: Target group health check interval = 30 seconds.

**Validation**: CloudWatch metric `HealthCheckCount` shows ~2 checks per minute per task.

**Traceability**: User Decision Q4

---

## ECS Task Configuration Rules

### BR-COMPUTE-006: Task Resource Allocation (CRITICAL)
**Rule**: ECS tasks MUST be allocated exactly 1 vCPU (1024 CPU units) and 2 GB RAM (2048 MB memory).

**Rationale**: Sized for moderate traffic (100-500 req/min).

**Implementation**: Task definition cpu = "1024", memory = "2048".

**Validation**: Describe task definition, verify cpu and memory fields.

**Traceability**: User Decision Q2

---

### BR-COMPUTE-007: Secrets Loading Requirement (CRITICAL)
**Rule**: ECS tasks MUST load DATABASE_URL, REDIS_URI, and HMAC_SECRET from Secrets Manager before accepting traffic.

**Rationale**: Secure secret management, no hardcoded credentials.

**Implementation**: Task definition secrets field references Secrets Manager ARNs.

**Validation**: Task fails to start if secrets unavailable; check CloudWatch logs for error message.

**Traceability**: BR-COMPUTE-025, SECURITY-03

---

### BR-COMPUTE-008: Health Check Grace Period (HIGH)
**Rule**: ECS service MUST wait 60 seconds (grace period) before ALB starts sending health checks to new tasks.

**Rationale**: Allow time for application startup (database connections, initialization).

**Implementation**: ECS service health_check_grace_period_seconds = 60.

**Validation**: New task receives first health check ~60 seconds after start.

**Traceability**: User Decision Q4

---

### BR-COMPUTE-009: Healthy Threshold (HIGH)
**Rule**: ECS tasks MUST pass 2 consecutive health checks (returning 200 OK) to be registered as "Healthy" in target group.

**Rationale**: Avoid routing to intermittently failing tasks.

**Implementation**: Target group healthy_threshold_count = 2.

**Validation**: Task status transitions to Healthy after 2 consecutive 200 responses (~60 seconds).

**Traceability**: User Decision Q4

---

### BR-COMPUTE-010: Unhealthy Threshold (HIGH)
**Rule**: ECS tasks MUST be deregistered as "Unhealthy" and terminated after 3 consecutive health check failures.

**Rationale**: Quickly remove failing tasks and launch replacements.

**Implementation**: Target group unhealthy_threshold_count = 3.

**Validation**: Simulate failure, verify task deregistered within 90 seconds (3 × 30s).

**Traceability**: User Decision Q4

---

### BR-COMPUTE-011: Database Connectivity Validation (CRITICAL)
**Rule**: Health check endpoint `/health_check` MUST validate database connectivity by executing a simple query (e.g., `SELECT 1`). Cache connectivity validation is NOT required.

**Rationale**: Database is critical path; cache failures are non-fatal (graceful degradation).

**Implementation**: `/health_check` endpoint executes test query against Aurora, returns 200 if successful, 503 if database unavailable.

**Validation**: Stop Aurora writer instance, verify health check returns 503 and task becomes unhealthy.

**Traceability**: Clarification Q1

---

### BR-COMPUTE-012: Desired Count Multi-AZ (CRITICAL)
**Rule**: ECS service MUST maintain desired count of 2 tasks, with tasks distributed across 2 availability zones (us-east-1a, us-east-1b).

**Rationale**: Multi-AZ high availability, survive single AZ failure.

**Implementation**: ECS service desired_count = 2, tasks placed in private subnets across 2 AZs.

**Validation**: Describe tasks, verify one task in each AZ.

**Traceability**: User Decision Q10

---

## Auto-Scaling Rules

### BR-COMPUTE-013: CPU Target Utilization (HIGH)
**Rule**: Auto-scaling MUST target 70% average CPU utilization across all running tasks.

**Rationale**: Balance between resource utilization and headroom for traffic spikes.

**Implementation**: Auto-scaling policy target value = 70.0 (70% CPU).

**Validation**: Load test to drive CPU >70%, verify scale-out within 60 seconds.

**Traceability**: User Decision Q3

---

### BR-COMPUTE-014: Minimum Task Count (CRITICAL)
**Rule**: Auto-scaling MUST maintain minimum of 2 tasks at all times (never scale below 2).

**Rationale**: Multi-AZ high availability requirement.

**Implementation**: Auto-scaling min_capacity = 2.

**Validation**: Verify service cannot scale below 2 tasks even with 0% CPU.

**Traceability**: User Decision Q3, BR-COMPUTE-012

---

### BR-COMPUTE-015: Maximum Task Count (HIGH)
**Rule**: Auto-scaling MUST NOT exceed maximum of 10 tasks (cost control).

**Rationale**: Cap maximum cost at 10 tasks × 1 vCPU / 2 GB RAM.

**Implementation**: Auto-scaling max_capacity = 10.

**Validation**: Load test to drive CPU >70% with 10 tasks, verify no additional tasks launched.

**Traceability**: User Decision Q3

---

### BR-COMPUTE-016: Scale-Out Cooldown (MEDIUM)
**Rule**: After scale-out action, auto-scaling MUST wait 60 seconds before evaluating next scale-out.

**Rationale**: Allow new task to start and register with ALB before evaluating again.

**Implementation**: Auto-scaling scale_out_cooldown = 60 seconds.

**Validation**: Trigger scale-out, verify no additional scale-out for 60 seconds.

**Traceability**: User Decision Q3

---

### BR-COMPUTE-017: Scale-In Cooldown (MEDIUM)
**Rule**: After scale-in action, auto-scaling MUST wait 300 seconds (5 minutes) before evaluating next scale-in.

**Rationale**: Prevent premature scale-in when traffic is variable.

**Implementation**: Auto-scaling scale_in_cooldown = 300 seconds.

**Validation**: Trigger scale-in, verify no additional scale-in for 300 seconds.

**Traceability**: User Decision Q3

---

### BR-COMPUTE-018: Gradual Scaling (MEDIUM)
**Rule**: Auto-scaling MUST only add or remove 1 task at a time (no batch scaling).

**Rationale**: Gradual scaling provides smoother transitions and avoids over-provisioning.

**Implementation**: Target tracking scaling policy automatically scales gradually.

**Validation**: Trigger scale-out, verify only 1 task added per scaling action.

**Traceability**: Best practice for target tracking scaling

---

## Deployment Rules

### BR-COMPUTE-019: Rolling Update Strategy (HIGH)
**Rule**: ECS service MUST use rolling update deployment strategy (not blue/green or canary).

**Rationale**: Simple, zero-downtime deployment for moderate-traffic application.

**Implementation**: ECS service deployment_controller_type = "ECS".

**Validation**: Update task definition, verify rolling update (new tasks launched before old tasks terminated).

**Traceability**: User Decision Q8

---

### BR-COMPUTE-020: Zero-Downtime Deployment (CRITICAL)
**Rule**: During deployment, minimum healthy percent MUST be 100% (no downtime).

**Rationale**: Maintain service availability during deployments.

**Implementation**: ECS service deployment_minimum_healthy_percent = 100.

**Validation**: Update task definition, verify at least 2 tasks always running during deployment.

**Traceability**: User Decision Q8

---

### BR-COMPUTE-021: Double Capacity During Deployment (HIGH)
**Rule**: During deployment, maximum percent MUST be 200% (deploy new tasks before draining old).

**Rationale**: Deploy new version completely before terminating old version.

**Implementation**: ECS service deployment_maximum_percent = 200.

**Validation**: Update task definition, verify 4 tasks running during deployment (2 old + 2 new).

**Traceability**: User Decision Q8

---

### BR-COMPUTE-022: Health Check Before Traffic (CRITICAL)
**Rule**: New tasks MUST pass health checks before receiving traffic from ALB. Old tasks MUST NOT be terminated until new tasks are healthy.

**Rationale**: Prevent traffic routing to unhealthy new tasks during deployment.

**Implementation**: ALB health check with 2 consecutive successes required before registration.

**Validation**: Deploy bad image (fails health check), verify old tasks remain serving traffic and deployment rolls back.

**Traceability**: BR-COMPUTE-009

---

### BR-COMPUTE-023: Connection Draining (HIGH)
**Rule**: Before terminating old tasks, ALB MUST wait up to 300 seconds for connections to drain.

**Rationale**: Allow in-flight requests to complete gracefully.

**Implementation**: Target group deregistration_delay = 300 seconds.

**Validation**: Establish long-running connection, terminate task, verify connection completes within 300 seconds.

**Traceability**: Best practice for graceful shutdown

---

### BR-COMPUTE-024: Deployment Rollback (HIGH)
**Rule**: If new tasks fail health checks during deployment, ECS service MUST stop deployment and retain old tasks.

**Rationale**: Automatic rollback on failure preserves service availability.

**Implementation**: ECS rolling update stops if health checks fail.

**Validation**: Deploy bad image, verify deployment stops and old tasks remain running.

**Traceability**: ECS rolling update behavior

---

## Security and IAM Rules

### BR-COMPUTE-025: Secrets Manager Integration (CRITICAL)
**Rule**: Sensitive configuration (DATABASE_URL, REDIS_URI, HMAC_SECRET) MUST be loaded from Secrets Manager, NOT hardcoded in task definition or container image.

**Rationale**: Secure secret management, rotation support.

**Implementation**: Task definition secrets field references Secrets Manager ARNs; task execution role has GetSecretValue permission.

**Validation**: Task fails to start if secrets unavailable; verify no secrets in task definition JSON.

**Traceability**: SECURITY-03, User Decision Q7

---

### BR-COMPUTE-026: Database Connectivity Validation (CRITICAL)
**Rule**: Application MUST validate database connectivity during startup and exit with non-zero code if database is unreachable.

**Rationale**: Fail fast if critical dependency unavailable.

**Implementation**: Application startup code tests database connection, exits if connection fails.

**Validation**: Stop Aurora writer, launch task, verify task exits with error.

**Traceability**: BR-COMPUTE-011

---

### BR-COMPUTE-027: Startup Failure Handling (HIGH)
**Rule**: Task MUST exit with non-zero exit code if secrets cannot be loaded or database is unreachable. ECS will automatically launch replacement task.

**Rationale**: Fail fast and retry, don't start partially-initialized task.

**Implementation**: Application startup validation exits with code 1 on failure.

**Validation**: Delete secret, launch task, verify task exits and ECS launches replacement.

**Traceability**: BR-COMPUTE-026

---

### BR-COMPUTE-028: Static Environment Variables (MEDIUM)
**Rule**: Non-sensitive configuration (APP_ENVIRONMENT, APP_LOG_LEVEL, APP_APPLICATION__PORT, APP_APPLICATION__HOST) MUST be injected as static environment variables in task definition.

**Rationale**: Clear separation of sensitive (Secrets Manager) and non-sensitive (task definition) configuration.

**Implementation**: Task definition environment field contains static variables.

**Validation**: Describe task definition, verify environment variables present.

**Traceability**: User Decision Q7

---

### BR-COMPUTE-029: X-Ray Tracing Configuration (HIGH)
**Rule**: Task MUST configure AWS X-Ray environment variables (AWS_XRAY_DAEMON_ADDRESS, AWS_XRAY_TRACING_NAME) for distributed tracing.

**Rationale**: Enable distributed tracing for observability (Clarification Q3).

**Implementation**: Task definition environment includes X-Ray variables; task role has X-Ray permissions.

**Validation**: Send request, verify trace appears in X-Ray console.

**Traceability**: Clarification Q3

---

### BR-COMPUTE-030: Least Privilege IAM (CRITICAL)
**Rule**: Task execution role and task role MUST follow least privilege principle, granting only minimum required permissions.

**Rationale**: Minimize blast radius of security breach.

**Implementation**: Task execution role: ECR pull, CloudWatch logs write, Secrets Manager read. Task role: Secrets Manager read, X-Ray write.

**Validation**: Remove permission, verify task fails with access denied error.

**Traceability**: SECURITY-04, User Decision Q5

---

## Container Registry Rules

### BR-COMPUTE-031: Immutable Image Tags (HIGH)
**Rule**: ECR repository MUST enforce immutable image tags (tags cannot be overwritten).

**Rationale**: Prevent accidental or malicious tag overwrites; ensure reproducibility.

**Implementation**: ECR repository image_tag_mutability = "IMMUTABLE".

**Validation**: Push image with existing tag, verify error.

**Traceability**: Best practice for container security

---

### BR-COMPUTE-032: Image Scanning on Push (HIGH)
**Rule**: ECR repository MUST scan images for vulnerabilities on push.

**Rationale**: Early detection of security vulnerabilities in dependencies.

**Implementation**: ECR repository image_scanning_on_push = true.

**Validation**: Push image, verify scan results appear in ECR console.

**Traceability**: SECURITY extension

---

### BR-COMPUTE-033: Image Tag Strategy (MEDIUM)
**Rule**: Container images MUST be tagged with git commit SHA (format: `sha-<commit-hash>`), NOT `latest` or semantic versions.

**Rationale**: Traceability from running task to source code commit.

**Implementation**: GitHub Actions workflow tags image with `sha-<git-hash>`.

**Validation**: Deploy task, describe task definition, verify image tag format.

**Traceability**: User Decision Q6

---

## Logging and Observability Rules

### BR-COMPUTE-034: CloudWatch Logs Retention (MEDIUM)
**Rule**: CloudWatch log group MUST retain logs for 30 days.

**Rationale**: Balance between troubleshooting capability and cost.

**Implementation**: CloudWatch log group retention_in_days = 30.

**Validation**: Check log group settings, verify retention period.

**Traceability**: User Decision Q9

---

### BR-COMPUTE-035: ALB Access Logging (HIGH)
**Rule**: ALB MUST enable access logging to S3 bucket with 30-day retention.

**Rationale**: Audit trail for HTTP requests, troubleshooting, security analysis (SECURITY-02).

**Implementation**: ALB access_logs_enabled = true, retention = 30 days. S3 bucket created in Unit 7.

**Validation**: Send requests, verify access logs appear in S3 bucket.

**Traceability**: User Decision Q9, SECURITY-02

---

## Business Rules Summary by Category

### CRITICAL Rules (13)
- BR-COMPUTE-001: HTTP to HTTPS redirect
- BR-COMPUTE-002: ACM certificate requirement
- BR-COMPUTE-003: Healthy target routing only
- BR-COMPUTE-006: Task resource allocation (1 vCPU / 2 GB RAM)
- BR-COMPUTE-007: Secrets loading requirement
- BR-COMPUTE-011: Database connectivity validation
- BR-COMPUTE-012: Desired count multi-AZ (2 tasks)
- BR-COMPUTE-014: Minimum task count (2 tasks)
- BR-COMPUTE-020: Zero-downtime deployment (100% min healthy)
- BR-COMPUTE-022: Health check before traffic
- BR-COMPUTE-025: Secrets Manager integration
- BR-COMPUTE-026: Database connectivity validation
- BR-COMPUTE-030: Least privilege IAM

### HIGH Rules (15)
- BR-COMPUTE-004: Multi-AZ distribution
- BR-COMPUTE-005: Health check interval (30 seconds)
- BR-COMPUTE-008: Health check grace period (60 seconds)
- BR-COMPUTE-009: Healthy threshold (2 consecutive successes)
- BR-COMPUTE-010: Unhealthy threshold (3 consecutive failures)
- BR-COMPUTE-013: CPU target utilization (70%)
- BR-COMPUTE-015: Maximum task count (10 tasks)
- BR-COMPUTE-019: Rolling update strategy
- BR-COMPUTE-021: Double capacity during deployment (200% max)
- BR-COMPUTE-023: Connection draining (300 seconds)
- BR-COMPUTE-024: Deployment rollback on failure
- BR-COMPUTE-027: Startup failure handling
- BR-COMPUTE-029: X-Ray tracing configuration
- BR-COMPUTE-031: Immutable image tags
- BR-COMPUTE-032: Image scanning on push
- BR-COMPUTE-035: ALB access logging

### MEDIUM Rules (7)
- BR-COMPUTE-016: Scale-out cooldown (60 seconds)
- BR-COMPUTE-017: Scale-in cooldown (300 seconds)
- BR-COMPUTE-018: Gradual scaling (1 task at a time)
- BR-COMPUTE-028: Static environment variables
- BR-COMPUTE-033: Image tag strategy (sha-based)
- BR-COMPUTE-034: CloudWatch logs retention (30 days)

---

## Validation Matrix

| Rule ID | Validation Method | Expected Result |
|---------|-------------------|----------------|
| BR-COMPUTE-001 | `curl -I http://...` | 301 redirect to HTTPS |
| BR-COMPUTE-002 | `openssl s_client -connect ...` | Valid certificate |
| BR-COMPUTE-003 | Terminate task | ALB stops routing within 90s |
| BR-COMPUTE-006 | Describe task definition | cpu=1024, memory=2048 |
| BR-COMPUTE-007 | Delete secret | Task fails to start |
| BR-COMPUTE-011 | Stop Aurora writer | Health check returns 503 |
| BR-COMPUTE-012 | Describe tasks | 1 task per AZ |
| BR-COMPUTE-013 | Load test >70% CPU | Scale-out within 60s |
| BR-COMPUTE-014 | 0% CPU utilization | Never scales below 2 tasks |
| BR-COMPUTE-015 | Load test with 10 tasks | No 11th task launched |
| BR-COMPUTE-020 | Deploy new version | Always ≥2 tasks running |
| BR-COMPUTE-025 | Check task definition JSON | No secrets in plaintext |
| BR-COMPUTE-029 | Send request | Trace in X-Ray console |
| BR-COMPUTE-031 | Push existing tag | Error: tag immutable |
| BR-COMPUTE-035 | Send requests | Logs in S3 bucket |

---

## Traceability to User Decisions

| User Decision | Business Rules |
|---------------|----------------|
| Q1: Domain `newsletter.crearerd.people.aws.dev` | BR-COMPUTE-002 |
| Q2: 1 vCPU / 2 GB RAM | BR-COMPUTE-006 |
| Q3: Auto-scaling 70% CPU, 2-10 tasks | BR-COMPUTE-013, BR-COMPUTE-014, BR-COMPUTE-015, BR-COMPUTE-016, BR-COMPUTE-017 |
| Q4: Health check config | BR-COMPUTE-005, BR-COMPUTE-008, BR-COMPUTE-009, BR-COMPUTE-010 |
| Q5: Minimal IAM permissions | BR-COMPUTE-030 |
| Q6: GitHub Actions + sha tags | BR-COMPUTE-033 |
| Q7: Secrets Manager + static env vars | BR-COMPUTE-025, BR-COMPUTE-028 |
| Q8: Rolling update 100%/200% | BR-COMPUTE-019, BR-COMPUTE-020, BR-COMPUTE-021 |
| Q9: ALB logging 30-day retention | BR-COMPUTE-035, BR-COMPUTE-034 |
| Q10: 2 tasks desired count | BR-COMPUTE-012, BR-COMPUTE-014 |
| Clarification Q1: Database-only health check | BR-COMPUTE-011 |
| Clarification Q3: X-Ray tracing | BR-COMPUTE-029 |

---

## References

- Functional Design: `business-logic-model.md`
- Domain Entities: `domain-entities.md`
- User Decisions: `questions.md`, `clarification-questions.md`
- Security Extension: SECURITY-01 through SECURITY-06
