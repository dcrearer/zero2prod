# Unit 4: Compute Infrastructure - Business Logic Model

## Overview

This document defines the business logic and operational processes for the ECS Fargate compute infrastructure that hosts the zero2prod web application.

**Design Date**: 2026-06-12  
**Unit**: 4 of 8 (Compute Infrastructure)

---

## Business Process 1: ALB Request Routing

**Process ID**: BP-COMPUTE-001  
**Purpose**: Route incoming HTTP/HTTPS requests to healthy ECS tasks

### Process Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Client Request                                                  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  DNS Resolution       │
                    │  newsletter.crearerd. │
                    │  people.aws.dev       │
                    │  → ALB Public IP      │
                    └───────────┬───────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
    ┌───────────────────────┐      ┌───────────────────────┐
    │  HTTP Listener        │      │  HTTPS Listener       │
    │  Port 80              │      │  Port 443             │
    │                       │      │  ACM Certificate      │
    │  Action: REDIRECT     │      │  TLS 1.2+             │
    │  → HTTPS (301)        │      └───────────┬───────────┘
    └───────────────────────┘                  │
                                               │
                                ┌──────────────▼──────────────┐
                                │  Target Group               │
                                │  Protocol: HTTP             │
                                │  Port: 8000                 │
                                │  Health Check: /health_check│
                                └──────────────┬──────────────┘
                                               │
                        ┌──────────────────────┼──────────────────────┐
                        │                      │                      │
                        ▼                      ▼                      ▼
            ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
            │  ECS Task 1       │  │  ECS Task 2       │  │  ECS Task N       │
            │  AZ: us-east-1a   │  │  AZ: us-east-1b   │  │  AZ: us-east-1a/b │
            │  Status: Healthy  │  │  Status: Healthy  │  │  Status: Healthy  │
            │  Port: 8000       │  │  Port: 8000       │  │  Port: 8000       │
            └───────────────────┘  └───────────────────┘  └───────────────────┘
```

### Business Rules Applied

1. **BR-COMPUTE-001**: All HTTP (port 80) requests MUST be redirected to HTTPS (port 443) with 301 status
2. **BR-COMPUTE-002**: HTTPS listener MUST use ACM certificate for `newsletter.crearerd.people.aws.dev`
3. **BR-COMPUTE-003**: ALB MUST only route to ECS tasks with "Healthy" status
4. **BR-COMPUTE-004**: ALB MUST distribute traffic across all healthy tasks in all AZs
5. **BR-COMPUTE-005**: ALB MUST perform health checks every 30 seconds on `/health_check`

### Routing Algorithm

```
IF request.protocol == HTTP (port 80):
    RETURN 301 Redirect to HTTPS
ELSE IF request.protocol == HTTPS (port 443):
    IF target_group.healthy_task_count == 0:
        RETURN 503 Service Unavailable
    ELSE:
        SELECT task FROM target_group.healthy_tasks
            USING round_robin_algorithm
        FORWARD request TO task:8000
        RETURN task.response
```

---

## Business Process 2: ECS Task Lifecycle Management

**Process ID**: BP-COMPUTE-002  
**Purpose**: Manage ECS task startup, runtime, health monitoring, and shutdown

### Process Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  ECS Service Scheduler                                           │
│  Desired Count: 2                                                │
│  Current Count: 1 (needs to launch 1 more task)                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  1. Task Provisioning │
                    │  - Pull ECR image     │
                    │  - Allocate Fargate   │
                    │    compute (1 vCPU,   │
                    │    2 GB RAM)          │
                    │  - Attach ENI         │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  2. Secrets Loading   │
                    │  - Retrieve DATABASE_ │
                    │    URL from Secrets   │
                    │    Manager            │
                    │  - Retrieve REDIS_URI │
                    │    from Secrets Mgr   │
                    │  - Retrieve HMAC_     │
                    │    SECRET             │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  3. Container Startup │
                    │  - Run zero2prod app  │
                    │  - Bind to 0.0.0.0:   │
                    │    8000               │
                    │  - Connect to Aurora  │
                    │  - Connect to         │
                    │    ElastiCache        │
                    │  - Initialize X-Ray   │
                    │    tracing            │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  4. Health Check      │
                    │     Grace Period      │
                    │  - Wait 60 seconds    │
                    │  - ALB does not send  │
                    │    health checks yet  │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  5. Health Check      │
                    │     Validation        │
                    │  - ALB sends GET      │
                    │    /health_check      │
                    │  - App validates DB   │
                    │    connectivity       │
                    │  - Return 200 OK      │
                    │  - Repeat every 30s   │
                    └───────────┬───────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
    ┌───────────────────────┐      ┌───────────────────────┐
    │  6a. Healthy          │      │  6b. Unhealthy        │
    │  - 2 consecutive 200s │      │  - 3 consecutive      │
    │  - Register with ALB  │      │    failures           │
    │  - Receive traffic    │      │  - Deregister from    │
    │  - Monitor CPU/memory │      │    ALB                │
    │  - Send logs to       │      │  - ECS terminates     │
    │    CloudWatch         │      │    task               │
    └───────────────────────┘      │  - Launch replacement │
                                   └───────────────────────┘
```

### Business Rules Applied

1. **BR-COMPUTE-006**: ECS tasks MUST have 1 vCPU and 2 GB RAM allocated
2. **BR-COMPUTE-007**: ECS tasks MUST load secrets from Secrets Manager before accepting traffic
3. **BR-COMPUTE-008**: ECS tasks MUST wait 60 seconds (grace period) before health checks start
4. **BR-COMPUTE-009**: ECS tasks MUST pass 2 consecutive health checks to be registered with ALB
5. **BR-COMPUTE-010**: ECS tasks MUST be terminated after 3 consecutive health check failures
6. **BR-COMPUTE-011**: Health check endpoint MUST validate database connectivity (not cache)
7. **BR-COMPUTE-012**: ECS service MUST maintain desired count of 2 tasks across 2 AZs

---

## Business Process 3: Auto-Scaling Logic

**Process ID**: BP-COMPUTE-003  
**Purpose**: Automatically adjust ECS task count based on CPU utilization

### Process Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  CloudWatch Metrics Collection (every 60 seconds)                │
│  - Collect CPU utilization for all running tasks                 │
│  - Calculate average CPU across all tasks                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Auto-Scaling Policy  │
                    │  Target: 70% CPU      │
                    │  Min: 2 tasks         │
                    │  Max: 10 tasks        │
                    └───────────┬───────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
    ┌───────────────────────┐      ┌───────────────────────┐
    │  Scale-Out Trigger    │      │  Scale-In Trigger     │
    │  IF avg_cpu > 70%     │      │  IF avg_cpu < 70%     │
    │  FOR 1 data point     │      │  FOR 1 data point     │
    │  (1 minute)           │      │  (1 minute)           │
    └───────────┬───────────┘      └───────────┬───────────┘
                │                               │
                ▼                               ▼
    ┌───────────────────────┐      ┌───────────────────────┐
    │  Scale-Out Action     │      │  Scale-In Action      │
    │  - Calculate new      │      │  - Calculate new      │
    │    desired count      │      │    desired count      │
    │  - Launch new tasks   │      │  - Drain connections  │
    │  - Wait for healthy   │      │  - Terminate tasks    │
    │  - Cooldown: 60s      │      │  - Cooldown: 300s     │
    └───────────────────────┘      └───────────────────────┘
```

### Scaling Algorithm

```
# Scale-Out Decision
IF average_cpu > 70% FOR 1_minute:
    IF current_task_count < 10:  # Max capacity
        IF NOT in_scale_out_cooldown:
            new_desired_count = current_task_count + 1
            launch_new_task()
            start_cooldown(60_seconds)

# Scale-In Decision
IF average_cpu < 70% FOR 1_minute:
    IF current_task_count > 2:  # Min capacity
        IF NOT in_scale_in_cooldown:
            new_desired_count = current_task_count - 1
            drain_and_terminate_task()
            start_cooldown(300_seconds)
```

### Business Rules Applied

1. **BR-COMPUTE-013**: Auto-scaling MUST target 70% average CPU utilization
2. **BR-COMPUTE-014**: Minimum task count MUST be 2 (Multi-AZ HA)
3. **BR-COMPUTE-015**: Maximum task count MUST be 10 (cost control)
4. **BR-COMPUTE-016**: Scale-out cooldown MUST be 60 seconds (prevent thrashing)
5. **BR-COMPUTE-017**: Scale-in cooldown MUST be 300 seconds (prevent premature scale-in)
6. **BR-COMPUTE-018**: Auto-scaling MUST only scale one task at a time (gradual scaling)

---

## Business Process 4: Deployment Rollout

**Process ID**: BP-COMPUTE-004  
**Purpose**: Deploy new container images with zero downtime

### Process Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  GitHub Actions CI/CD                                            │
│  - Push to main branch triggers build                            │
│  - Build Docker image                                            │
│  - Push to ECR with tag: sha-<git-hash>                         │
│  - Update ECS task definition with new image                    │
│  - Trigger ECS service update                                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  ECS Service Update   │
                    │  Deployment Config:   │
                    │  - Min Healthy: 100%  │
                    │  - Max Percent: 200%  │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  1. Launch New Tasks  │
                    │  - Launch 2 new tasks │
                    │    with new image     │
                    │  - Total tasks: 4     │
                    │    (2 old + 2 new)    │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  2. Health Check New  │
                    │  - Wait 60s grace     │
                    │  - Validate /health_  │
                    │    check              │
                    │  - Wait for 2         │
                    │    consecutive 200s   │
                    └───────────┬───────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
    ┌───────────────────────┐      ┌───────────────────────┐
    │  3a. New Tasks Healthy│      │  3b. New Tasks Failed │
    │  - Register with ALB  │      │  - Deregister from    │
    │  - Start receiving    │      │    ALB                │
    │    traffic            │      │  - Terminate new      │
    │  - Proceed to drain   │      │    tasks              │
    │    old tasks          │      │  - Rollback           │
    └───────────┬───────────┘      │    deployment         │
                │                  └───────────────────────┘
                ▼
    ┌───────────────────────┐
    │  4. Drain Old Tasks   │
    │  - Deregister from    │
    │    ALB                │
    │  - Wait for           │
    │    connections to     │
    │    drain (300s max)   │
    │  - Terminate old      │
    │    tasks              │
    └───────────┬───────────┘
                │
                ▼
    ┌───────────────────────┐
    │  5. Deployment        │
    │     Complete          │
    │  - 2 new tasks        │
    │    running            │
    │  - 0 old tasks        │
    │  - Total tasks: 2     │
    └───────────────────────┘
```

### Business Rules Applied

1. **BR-COMPUTE-019**: Deployment MUST use rolling update strategy
2. **BR-COMPUTE-020**: Minimum healthy percent MUST be 100% (no downtime)
3. **BR-COMPUTE-021**: Maximum percent MUST be 200% (double capacity during deployment)
4. **BR-COMPUTE-022**: New tasks MUST pass health checks before old tasks are drained
5. **BR-COMPUTE-023**: Connection draining MUST wait up to 300 seconds before terminating tasks
6. **BR-COMPUTE-024**: Deployment MUST rollback if new tasks fail health checks

---

## Business Process 5: Secrets and Configuration Loading

**Process ID**: BP-COMPUTE-005  
**Purpose**: Securely load secrets and configuration at task startup

### Process Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  ECS Task Startup                                                │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  1. Task Execution    │
                    │     Role Assumed      │
                    │  - IAM role grants    │
                    │    access to Secrets  │
                    │    Manager            │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  2. Load Secrets from │
                    │     Secrets Manager   │
                    │  - DATABASE_URL       │
                    │  - REDIS_URI          │
                    │  - HMAC_SECRET        │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  3. Load Static Env   │
                    │     Variables         │
                    │  - APP_ENVIRONMENT    │
                    │  - APP_LOG_LEVEL      │
                    │  - APP_APPLICATION__  │
                    │    PORT               │
                    │  - APP_APPLICATION__  │
                    │    HOST               │
                    │  - AWS_XRAY_DAEMON_   │
                    │    ADDRESS            │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  4. Validate Database │
                    │     Connectivity      │
                    │  - Connect to Aurora  │
                    │  - Run health query   │
                    │  - Exit if failure    │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  5. Initialize App    │
                    │  - Start web server   │
                    │  - Bind to port 8000  │
                    │  - Initialize X-Ray   │
                    │    client             │
                    │  - Ready for traffic  │
                    └───────────────────────┘
```

### Business Rules Applied

1. **BR-COMPUTE-025**: Secrets MUST be loaded from Secrets Manager (not hardcoded)
2. **BR-COMPUTE-026**: Database connectivity MUST be validated before accepting traffic
3. **BR-COMPUTE-027**: Task MUST exit with error if secrets cannot be loaded
4. **BR-COMPUTE-028**: Static environment variables MUST be injected at task definition
5. **BR-COMPUTE-029**: AWS X-Ray daemon address MUST be configured for distributed tracing

---

## Data Flow Diagrams

### Request Processing Data Flow

```
┌─────────┐
│ Client  │
└────┬────┘
     │ HTTP/HTTPS Request
     ▼
┌────────────┐
│    ALB     │
└────┬───────┘
     │ HTTP Request (decrypted)
     ▼
┌──────────────┐
│  ECS Task    │
│  Container   │
└────┬─────────┘
     │ SQL Query
     ▼
┌──────────────┐      ┌──────────────┐
│   Aurora     │      │ ElastiCache  │
│  PostgreSQL  │      │   Redis      │
└──────────────┘      └──────────────┘
     │ Query Result        │ Session Data
     ▼                     ▼
┌──────────────┐
│  ECS Task    │
│  Container   │
└────┬─────────┘
     │ HTTP Response
     ▼
┌────────────┐
│    ALB     │
└────┬───────┘
     │ HTTPS Response (encrypted)
     ▼
┌─────────┐
│ Client  │
└─────────┘
```

---

## Integration Points

### 1. Network Infrastructure (Unit 1)
- **VPC**: ECS tasks deployed in private subnets
- **Security Groups**: ALB SG allows inbound 80/443, ECS SG allows inbound 8000 from ALB SG
- **Subnets**: ALB in public subnets, ECS tasks in private subnets

### 2. Database Infrastructure (Unit 2)
- **Aurora Endpoint**: ECS tasks connect via DATABASE_URL from Secrets Manager
- **Database Secret**: ECS task role has GetSecretValue permission

### 3. Cache Infrastructure (Unit 3)
- **ElastiCache Endpoint**: ECS tasks connect via REDIS_URI from Secrets Manager
- **Cache Secret**: ECS task role has GetSecretValue permission

### 4. Container Registry (ECR)
- **Image Storage**: GitHub Actions pushes images to ECR
- **Image Pull**: ECS task execution role pulls images from ECR

### 5. Observability (Unit 7 - Future)
- **CloudWatch Logs**: ECS tasks write logs to CloudWatch log group
- **AWS X-Ray**: ECS tasks send traces to X-Ray daemon
- **CloudWatch Metrics**: Auto-scaling consumes CPU/memory metrics

---

## Summary

The compute infrastructure business logic encompasses 5 core processes:
1. **ALB Request Routing**: HTTP→HTTPS redirect, target group distribution
2. **ECS Task Lifecycle**: Provisioning, secrets loading, health checks, termination
3. **Auto-Scaling**: CPU-based scaling with 70% target, 2-10 tasks
4. **Deployment Rollout**: Zero-downtime rolling updates with 100%/200% config
5. **Secrets Loading**: Secure loading from Secrets Manager with database validation

All processes enforce strict business rules for reliability, security, and cost optimization.
