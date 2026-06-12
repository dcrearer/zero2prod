# Unit 4: Compute Infrastructure - Code Summary

## Overview

This document summarizes the generated code for Unit 4: Compute Infrastructure. All code implements AWS ECS Fargate compute infrastructure using AWS CDK (Python).

**Generation Date**: 2026-06-12  
**Unit**: 4 of 8 (Compute Infrastructure)  
**Programming Language**: Python (AWS CDK v2)

---

## Generated Files Summary

### Application Code (Workspace Root)

| File Path | Status | Description | Lines |
|-----------|--------|-------------|-------|
| `cdk/app.py` | Modified | CDK app entry point - added ComputeStack instantiation | ~110 |
| `cdk/stacks/compute_stack.py` | Created | ComputeStack implementation with ALB, ECS, auto-scaling | ~370 |
| `.github/workflows/deploy-ecs.yml` | Created | GitHub Actions CI/CD workflow for ECS deployment | ~105 |

### Tests (Workspace Root)

| File Path | Status | Description | Lines |
|-----------|--------|-------------|-------|
| `cdk/tests/test_compute_stack.py` | Created | Unit tests for ComputeStack with pytest and CDK assertions | ~360 |

### Documentation (aidlc-docs/)

| File Path | Description |
|-----------|-------------|
| `aidlc-docs/construction/unit-4-compute/code/code-summary.md` | This document |
| `aidlc-docs/construction/unit-4-compute/code/deployment-instructions.md` | CDK deployment instructions |
| `aidlc-docs/construction/unit-4-compute/code/testing-instructions.md` | Unit test execution instructions |

---

## ComputeStack Structure

### File: `cdk/stacks/compute_stack.py`

**Overview**: Implements ECS Fargate compute infrastructure with Application Load Balancer, auto-scaling, and supporting services.

**Class**: `ComputeStack(Stack)`

**Constructor Parameters**:
- `vpc`: VPC from NetworkStack
- `public_subnets`: Public subnets for ALB
- `private_subnets`: Private subnets for ECS tasks
- `alb_sg`: ALB security group
- `ecs_sg`: ECS security group
- `database_secret`: Database secret from DatabaseStack
- `cache_secret`: Cache secret from CacheStack

**Resources Created** (in order):
1. **CloudWatch Log Group** (`/ecs/zero2prod-web`, 30-day retention)
2. **ECR Repository** (`zero2prod`, immutable tags, scan on push)
3. **HMAC Secret** (Secrets Manager, auto-generated)
4. **Task Execution IAM Role** (ECR pull, logs write, secrets read)
5. **Task Runtime IAM Role** (X-Ray tracing permissions)
6. **ECS Cluster** (`zero2prod-cluster`, Container Insights enabled)
7. **Fargate Task Definition** (1 vCPU / 2 GB, environment vars + secrets)
8. **Container** (`AppContainer`, port 8000, AWS Logs driver)
9. **Target Group** (HTTP port 8000, health check `/health_check`)
10. **Application Load Balancer** (internet-facing, public subnets)
11. **HTTP Listener** (port 80 → HTTPS redirect)
12. **HTTPS Listener** (port 443, TLS 1.3/1.2, requires ACM certificate)
13. **Fargate Service** (desired count 2, rolling deployment 100%/200%)
14. **Auto-Scaling** (CPU target 70%, min 2, max 10 tasks)
15. **CloudFormation Outputs** (ALB DNS, cluster name, ECR URI)

**Dependencies**:
- NetworkStack (VPC, subnets, security groups)
- DatabaseStack (database secret ARN)
- CacheStack (cache secret ARN)

**Exports**:
- `Zero2Prod-ALB-DNS-Name` → ALB DNS for Route53/CloudFront
- `Zero2Prod-ECS-Cluster-Name` → For Unit 5 (Worker)
- `Zero2Prod-ECR-Repository-Uri` → For GitHub Actions CI/CD

---

## CDK App Integration

### File: `cdk/app.py`

**Modifications**:
- Added `from stacks.compute_stack import ComputeStack` import
- Instantiated ComputeStack after CacheStack
- Passed VPC, subnets, security groups, and secrets as parameters
- Added stack dependencies: NetworkStack, DatabaseStack, CacheStack

**Stack Deployment Order**:
1. NetworkStack (Unit 1)
2. DatabaseStack (Unit 2)
3. CacheStack (Unit 3)
4. **ComputeStack (Unit 4)** ← New

---

## Unit Tests

### File: `cdk/tests/test_compute_stack.py`

**Test Classes**:
1. **TestApplicationLoadBalancer**: ALB configuration, HTTP redirect, target group
2. **TestECSCluster**: Cluster name, Container Insights
3. **TestTaskDefinition**: CPU/memory allocation, container configuration
4. **TestIAMRoles**: Task execution role, task runtime role policies
5. **TestECSService**: Service name, desired count, deployment configuration
6. **TestAutoScaling**: Scalable target, CPU-based scaling policy
7. **TestECRRepository**: Repository name, immutable tags, image scanning
8. **TestCloudWatchLogs**: Log group name, retention period
9. **TestSecretsManager**: HMAC secret creation
10. **TestCloudFormationOutputs**: Required exports exist

**Test Coverage**:
- 15 test methods covering all major resources
- Uses CDK assertions (Template.from_stack, Match)
- Validates resource properties against business rules

**Execution**:
```bash
cd cdk/
pytest tests/test_compute_stack.py -v
```

---

## GitHub Actions Workflow

### File: `.github/workflows/deploy-ecs.yml`

**Trigger**: Push to `main` branch or manual workflow dispatch

**Jobs**:
1. **Checkout code**
2. **Configure AWS credentials** (OIDC with role assumption)
3. **Login to Amazon ECR**
4. **Build, tag, and push Docker image**:
   - Tag: `sha-<commit-hash>` (immutable, traceability)
   - Tag: `latest` (convenience)
5. **Download current task definition** from ECS
6. **Render task definition** with new image URI
7. **Deploy to ECS** (rolling update, wait for stability)
8. **Verify deployment** (check running task count ≥ 2)
9. **Display ALB DNS** (application URL)

**Environment Variables**:
- `AWS_REGION`: `us-east-1`
- `ECR_REPOSITORY`: `zero2prod`
- `ECS_CLUSTER`: `zero2prod-cluster`
- `ECS_SERVICE`: `zero2prod-web-service`
- `CONTAINER_NAME`: `AppContainer`

**Secrets Required**:
- `AWS_OIDC_ROLE_ARN`: IAM role ARN for GitHub Actions OIDC authentication

**Permissions**:
- `id-token: write` (OIDC authentication)
- `contents: read` (repository access)

---

## Business Rules Implementation

| Business Rule | Implementation Location | Status |
|---------------|------------------------|--------|
| BR-COMPUTE-001: HTTP→HTTPS redirect | `compute_stack.py` line 299 (HTTP listener) | ✅ |
| BR-COMPUTE-002: Multi-AZ deployment | `compute_stack.py` line 281 (ALB), line 329 (service) | ✅ |
| BR-COMPUTE-003: ECS Fargate | `compute_stack.py` line 181 (cluster) | ✅ |
| BR-COMPUTE-006: 1 vCPU / 2 GB | `compute_stack.py` line 191-194 (task definition) | ✅ |
| BR-COMPUTE-007: Desired count 2 | `compute_stack.py` line 332 (service) | ✅ |
| BR-COMPUTE-011: Database health check | `compute_stack.py` line 260-268 (target group) | ✅ |
| BR-COMPUTE-012: Health check 30s | `compute_stack.py` line 265 (interval) | ✅ |
| BR-COMPUTE-013: 70% CPU auto-scaling | `compute_stack.py` line 355 (scaling policy) | ✅ |
| BR-COMPUTE-014: Min 2, max 10 tasks | `compute_stack.py` line 349-352 (auto-scaling) | ✅ |
| BR-COMPUTE-015: Scale-out cooldown 60s | `compute_stack.py` line 357 (scale-out) | ✅ |
| BR-COMPUTE-016: Scale-in cooldown 300s | `compute_stack.py` line 356 (scale-in) | ✅ |
| BR-COMPUTE-018: Rolling deployment | `compute_stack.py` line 333-334 (min/max healthy) | ✅ |
| BR-COMPUTE-020: Graceful shutdown 300s | `compute_stack.py` line 271 (deregistration delay) | ✅ |
| BR-COMPUTE-022: GitHub Actions CI/CD | `.github/workflows/deploy-ecs.yml` | ✅ |
| BR-COMPUTE-023: <5 min deployment | `.github/workflows/deploy-ecs.yml` (automated) | ✅ |
| BR-COMPUTE-024: Immutable image tags | `compute_stack.py` line 96 (ECR), `deploy-ecs.yml` line 43 | ✅ |
| BR-COMPUTE-025: Secrets Manager | `compute_stack.py` line 113, 228-241 (secrets) | ✅ |
| BR-COMPUTE-026: Static env vars | `compute_stack.py` line 218-226 (environment) | ✅ |
| BR-COMPUTE-028: CloudWatch Logs 30-day | `compute_stack.py` line 82 (log group) | ✅ |
| BR-COMPUTE-029: TLS 1.2+ | `compute_stack.py` line 316 (SSL policy) | ✅ |
| BR-COMPUTE-030: Least privilege IAM | `compute_stack.py` line 126-149, 158-170 (IAM roles) | ✅ |
| BR-COMPUTE-031: Image scanning | `compute_stack.py` line 97 (scan on push) | ✅ |
| BR-COMPUTE-034: X-Ray tracing | `compute_stack.py` line 161-167 (task role), line 223 (env vars) | ✅ |

**Total Business Rules**: 23  
**Implemented**: 23 ✅  
**Compliance**: 100%

---

## Key Features

### 1. Application Load Balancer
- **HTTP→HTTPS redirect**: All HTTP traffic (port 80) redirected to HTTPS (port 443) with 301 permanent redirect
- **TLS 1.3 + 1.2**: Modern SSL policy for secure communication
- **Target Group**: Health check every 30s on `/health_check` endpoint
- **Connection Draining**: 300-second deregistration delay for graceful shutdown

### 2. ECS Fargate
- **Serverless**: No EC2 instance management required
- **Right-Sized**: 1 vCPU / 2 GB memory per task
- **Multi-AZ**: Tasks spread across us-east-1a and us-east-1b
- **Container Insights**: Enabled for enhanced observability

### 3. Auto-Scaling
- **Target Tracking**: CPU-based scaling with 70% target
- **Capacity**: Min 2 tasks, max 10 tasks
- **Cooldowns**: Scale-out 60s, scale-in 300s
- **Cost-Effective**: Scales down during low traffic

### 4. Security
- **Secrets Manager**: DATABASE_URL, REDIS_URI, HMAC_SECRET injected at runtime
- **Least Privilege IAM**: Separate task execution and task runtime roles
- **Private Subnets**: ECS tasks run in isolated subnets
- **Image Scanning**: ECR scans images on push for vulnerabilities
- **Immutable Tags**: sha-based tags prevent image tampering

### 5. Observability
- **CloudWatch Logs**: Structured JSON logs with 30-day retention
- **X-Ray Tracing**: Distributed tracing for performance analysis
- **Container Insights**: Cluster and task-level metrics
- **CloudWatch Alarms**: (to be added in Unit 7 - Observability)

### 6. CI/CD
- **GitHub Actions**: Automated deployment on push to main
- **OIDC Authentication**: Secure AWS credential management
- **Immutable Tags**: sha-based tags for traceability
- **Rolling Deployment**: Zero-downtime updates (100% min, 200% max)
- **Verification**: Automated health check after deployment

---

## Next Steps

### Deployment
1. Review deployment instructions: `deployment-instructions.md`
2. Ensure ACM certificate exists for domain
3. Deploy ComputeStack: `cdk deploy Zero2ProdComputeStack`
4. Build and push initial Docker image to ECR
5. Verify ECS service is running with 2 healthy tasks

### Testing
1. Review testing instructions: `testing-instructions.md`
2. Run unit tests: `pytest cdk/tests/test_compute_stack.py -v`
3. Validate CDK synthesis: `cdk synth Zero2ProdComputeStack`
4. Perform post-deployment validation (see deployment-configuration.md)

### CI/CD Setup
1. Create GitHub OIDC provider in AWS IAM (one-time)
2. Create IAM role for GitHub Actions with ECR + ECS permissions
3. Add `AWS_OIDC_ROLE_ARN` to GitHub repository secrets
4. Push to main branch to trigger automated deployment

---

## References

- Infrastructure Design: `../infrastructure-design/`
- Functional Design: `../functional-design/`
- NFR Requirements: `../nfr-requirements/`
- NFR Design: `../nfr-design/`
- CDK Stack Design: `../infrastructure-design/cdk-stack-design.md`
- Deployment Configuration: `../infrastructure-design/deployment-configuration.md`
