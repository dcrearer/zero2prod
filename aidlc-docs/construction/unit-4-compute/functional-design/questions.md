# Unit 4: Compute Infrastructure - Functional Design Questions

## Purpose

This document gathers decisions for the functional design of Unit 4: Compute Infrastructure. Your answers will guide the design of the ECS Fargate deployment, ALB configuration, auto-scaling, and IAM permissions.

---

## Question 1: ALB Certificate and Domain Configuration

**Context**: The ALB requires an ACM certificate for HTTPS listeners. The unit-of-work.md mentions ACM certificate but doesn't specify domain or certificate details.

**Question**: What domain name and ACM certificate should the ALB use?

**Options**:
A. Use existing ACM certificate for specific domain (e.g., newsletter.example.com)
B. Create a new self-signed certificate for testing
C. Skip HTTPS for now, use HTTP only (port 80)
D. Use AWS-managed certificate with auto-renewal

[Answer]: A

**Follow-up**: If A or D, what is the domain name? If C, should we plan for HTTPS in a future iteration?

[Answer]: newsletter.crearerd.people.aws.dev

---

## Question 2: ECS Task Resource Sizing

**Context**: The unit-of-work.md specifies 0.5 vCPU and 1 GB RAM. This is suitable for low-to-moderate traffic. The existing application runs in Docker with unknown resource requirements.

**Question**: Are the proposed ECS task resources (0.5 vCPU, 1 GB RAM) appropriate for the expected workload?

**Options**:
A. Yes, 0.5 vCPU / 1 GB RAM is appropriate (low traffic, <100 req/min)
B. Increase to 1 vCPU / 2 GB RAM (moderate traffic, 100-500 req/min)
C. Increase to 2 vCPU / 4 GB RAM (high traffic, 500+ req/min)
D. Not sure, need load testing to determine

[Answer]: B

**Follow-up**: If D, should we start with 0.5 vCPU / 1 GB RAM and adjust based on CloudWatch metrics?

[Answer]:

---

## Question 3: Auto-Scaling Parameters

**Context**: The unit-of-work.md specifies target CPU 70%, min 2 tasks, max 10 tasks. This balances availability and cost.

**Question**: Are the proposed auto-scaling parameters acceptable?

**Configuration**:
- **Target Metric**: CPU utilization
- **Target Value**: 70%
- **Min Capacity**: 2 tasks (Multi-AZ, 1 per AZ)
- **Max Capacity**: 10 tasks
- **Scale-Out Cooldown**: 60 seconds
- **Scale-In Cooldown**: 300 seconds (5 minutes)

**Options**:
A. Accept proposed configuration (balanced approach)
B. Increase max capacity to 20 tasks (handle traffic spikes)
C. Decrease target CPU to 50% (more aggressive scaling)
D. Use memory-based scaling instead of CPU-based

[Answer]: A

**Follow-up**: If B, C, or D, what specific values should be used?

[Answer]: 

---

## Question 4: Health Check Configuration

**Context**: The ALB health check validates ECS task health. The existing application has a `/health_check` endpoint that returns 200 OK. The health check must validate database connectivity.

**Question**: What health check configuration should the ALB use?

**Proposed Configuration**:
- **Path**: /health_check
- **Protocol**: HTTP
- **Port**: 8000 (container port)
- **Interval**: 30 seconds
- **Timeout**: 5 seconds
- **Healthy Threshold**: 2 consecutive successes
- **Unhealthy Threshold**: 3 consecutive failures
- **Health Check Grace Period**: 60 seconds (ECS service)

**Options**:
A. Accept proposed configuration
B. Increase interval to 60 seconds (reduce health check cost)
C. Decrease healthy threshold to 1 (faster task registration)
D. Increase grace period to 120 seconds (slower startup)

[Answer]: A

**Follow-up**: Should the health check endpoint validate both database and cache connectivity, or just database?

[Answer]: 

---

## Question 5: ECS Task IAM Permissions

**Context**: The ECS task needs IAM permissions to access Secrets Manager (database, cache, HMAC secrets), Aurora (read/write), and CloudWatch Logs (write).

**Question**: What IAM permissions should the ECS task role have?

**Proposed Permissions**:
- **Secrets Manager**: GetSecretValue on `zero2prod/database/*` and `zero2prod/cache/*`
- **Aurora**: Connect via IAM database authentication (optional)
- **CloudWatch Logs**: CreateLogStream, PutLogEvents
- **ECR**: GetAuthorizationToken, BatchCheckLayerAvailability, GetDownloadUrlForLayer, BatchGetImage (task execution role)

**Options**:
A. Accept proposed permissions (minimal access)
B. Add S3 permissions for future file uploads
C. Add SES permissions for sending emails directly from ECS (instead of worker)
D. Use IAM database authentication for Aurora (no password in secrets)

[Answer]: A

**Follow-up**: If D, should we enable IAM database authentication for Aurora? (Requires RDS modification)

[Answer]: 

---

## Question 6: Container Image Strategy

**Context**: The ECS task pulls container images from ECR. The application must be built as a Docker image and pushed to ECR.

**Question**: What container image build and push strategy should we use?

**Options**:
A. Manual build and push (`docker build` + `docker push` to ECR)
B. GitHub Actions CI/CD pipeline (build on push to main, push to ECR)
C. AWS CodeBuild + CodePipeline (full CI/CD)
D. Local build for now, CI/CD in Unit 8 (CI/CD Infrastructure)

[Answer]: 

**Follow-up**: If A or D, what is the initial image tag? (e.g., `latest`, `v0.16.0`, `sha-<git-hash>`)

[Answer]: B

---

## Question 7: Environment Variable Configuration

**Context**: The ECS task definition specifies environment variables for application configuration. Some values come from Secrets Manager, others are static.

**Question**: Which environment variables should be loaded from Secrets Manager vs. static values in task definition?

**Proposed Configuration**:
- **From Secrets Manager**:
  - `DATABASE_URL` (full connection string with password)
  - `REDIS_URI` (full connection string with TLS)
  - `HMAC_SECRET` (for session signing)
- **Static in Task Definition**:
  - `APP_ENVIRONMENT=production`
  - `APP_LOG_LEVEL=info`
  - `APP_APPLICATION__PORT=8000`
  - `APP_APPLICATION__HOST=0.0.0.0`

**Options**:
A. Accept proposed configuration
B. Move all configuration to Secrets Manager (including log level)
C. Move HMAC_SECRET to AWS Systems Manager Parameter Store (cheaper for non-rotating secrets)
D. Use AWS AppConfig for dynamic configuration

[Answer]: A

**Follow-up**: Should we add environment variables for feature flags or observability integrations (e.g., AWS X-Ray)?

[Answer]: 

---

## Question 8: Deployment Strategy

**Context**: The ECS service deployment strategy determines how new tasks replace old tasks during updates.

**Question**: What deployment strategy should the ECS service use?

**Options**:
A. Rolling Update (default): Deploy new tasks, drain old tasks gradually
B. Blue/Green Deployment: Deploy full new task set, switch traffic atomically
C. Canary Deployment: Deploy 10% new tasks, monitor, then deploy 100%
D. Rolling Update with Circuit Breaker: Rollback automatically on health check failures

[Answer]: A

**Follow-up**: If A or D, what are the deployment configuration parameters?
- **Minimum Healthy Percent**: % of desired tasks that must remain healthy during deployment
- **Maximum Percent**: % of desired tasks that can run during deployment

**Proposed**:
- Minimum Healthy Percent: 100% (no downtime)
- Maximum Percent: 200% (deploy new tasks before draining old)

[Answer]: used the proposed values

---

## Question 9: ALB Access Logging

**Context**: ALB access logs provide visibility into HTTP requests. The unit-of-work.md mentions access logging enabled to S3 (SECURITY-02).

**Question**: Should ALB access logging be enabled?

**Options**:
A. Yes, enable access logging to S3 bucket (7-day retention)
B. Yes, enable access logging to S3 bucket (30-day retention)
C. Yes, enable access logging to S3 bucket (90-day retention for compliance)
D. No, skip access logging (save cost)

[Answer]: B

**Follow-up**: If A, B, or C, should the S3 bucket be created in this unit or Unit 7 (Observability)?

[Answer]: Observability

---

## Question 10: ECS Service Desired Count

**Context**: The unit-of-work.md specifies desired count of 2 tasks (Multi-AZ for HA). This ensures at least 1 task per AZ.

**Question**: Is a desired count of 2 tasks appropriate for production?

**Options**:
A. Yes, 2 tasks (1 per AZ, minimal HA)
B. Increase to 4 tasks (2 per AZ, better redundancy)
C. Start with 1 task (save cost, no HA)
D. Let auto-scaling determine count (start with min capacity)

[Answer]: A

**Follow-up**: If C, is this acceptable for a production system? (No HA during task failures)

[Answer]: 

---

## Summary

Once you've answered all questions, I will:
1. Analyze your responses for ambiguities
2. Generate follow-up questions if needed
3. Create functional design artifacts (business-logic-model.md, domain-entities.md, business-rules.md)
4. Document all decisions in user-decision-log.md
