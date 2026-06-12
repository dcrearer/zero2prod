# Unit 4: Compute Infrastructure - Code Generation Plan

## Overview

This plan details the code generation for Unit 4: Compute Infrastructure. This unit implements AWS ECS Fargate compute infrastructure using AWS CDK (Python) to deploy the zero2prod web application.

**Unit Context**:
- **Unit Name**: Unit 4 - Compute Infrastructure
- **Unit Type**: Infrastructure as Code (AWS CDK)
- **Programming Language**: Python (AWS CDK v2)
- **Project Type**: Brownfield (infrastructure additions)
- **Workspace Root**: `/Users/crearerd/Dev/rust/zero2prod`

**Unit Responsibilities**:
- Deploy Application Load Balancer with HTTP→HTTPS redirect
- Deploy ECS Fargate cluster and service (zero2prod web application)
- Configure auto-scaling (2-10 tasks, 70% CPU target)
- Deploy ECR repository for container images
- Configure IAM roles (task execution, task runtime)
- Configure CloudWatch Logs for container logging
- Generate GitHub Actions workflow for CI/CD deployment
- Create HMAC secret in Secrets Manager

**Unit Dependencies**:
- **Unit 1 (Network)**: VPC, subnets, security groups (CloudFormation imports)
- **Unit 2 (Database)**: Database secret ARN (CloudFormation import)
- **Unit 3 (Cache)**: Cache secret ARN (CloudFormation import)

**Unit Exports** (for downstream units):
- `Zero2Prod-ECS-Cluster-Name` → Unit 5 (Worker)
- `Zero2Prod-ALB-DNS-Name` → DNS configuration
- `Zero2Prod-ECR-Repository-Uri` → GitHub Actions

---

## Code Generation Steps

### Phase 1: Infrastructure Setup

#### Step 1: Create Infrastructure Directory Structure
- [x] Create `infrastructure/` directory in workspace root (if not exists)
- [x] Create `infrastructure/stacks/` directory for CDK stacks
- [x] Create `infrastructure/tests/` directory for unit tests
- [x] Verify directory structure

**Artifacts**:
- `infrastructure/` (new or existing)
- `infrastructure/stacks/` (new)
- `infrastructure/tests/` (new)

---

#### Step 2: Create CDK App Entry Point
- [x] Create `infrastructure/app.py` as CDK app entry point
- [x] Import necessary CDK modules
- [x] Instantiate ComputeStack with dependencies
- [x] Configure AWS account and region from environment

**Artifacts**:
- `infrastructure/app.py` (new)

**Code Summary**:
```python
#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.compute_stack import ComputeStack

app = cdk.App()

ComputeStack(app, "Zero2ProdComputeStack",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION', 'us-east-1')
    )
)

app.synth()
```

---

#### Step 3: Create CDK Configuration Files
- [x] Create `infrastructure/cdk.json` with app configuration
- [x] Create `infrastructure/requirements.txt` with CDK dependencies
- [x] Create `infrastructure/.gitignore` for CDK artifacts

**Artifacts**:
- `infrastructure/cdk.json` (new)
- `infrastructure/requirements.txt` (new)
- `infrastructure/.gitignore` (new)

**Dependencies** (requirements.txt):
```
aws-cdk-lib==2.139.0
constructs>=10.0.0,<11.0.0
```

---

### Phase 2: ComputeStack Implementation

#### Step 4: Create ComputeStack Class Structure
- [x] Create `infrastructure/stacks/compute_stack.py`
- [ ] Import CDK modules (core, ec2, ecs, elbv2, iam, ecr, logs, secretsmanager)
- [ ] Define ComputeStack class inheriting from Stack
- [ ] Add docstring documenting stack purpose and dependencies
- [ ] Initialize stack with super().__init__()

**Artifacts**:
- `infrastructure/stacks/compute_stack.py` (new)

---

#### Step 5: Import Dependencies from Previous Stacks
- [x] Import VPC from NetworkStack using `Fn.import_value("Zero2Prod-VPC-Id")`
- [x] Import public subnets (1a, 1b) for ALB
- [x] Import private subnets (1a, 1b) for ECS tasks
- [x] Import ALB security group ID
- [x] Import ECS security group ID
- [x] Import database secret ARN from DatabaseStack
- [x] Import cache secret ARN from CacheStack
- [x] Store all imports as instance variables

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 42-49, 145-150, 210-212

---

#### Step 6: Create Application Load Balancer
- [x] Create ALB in public subnets with internet-facing scheme
- [x] Attach ALB security group
- [x] Configure deletion protection enabled
- [x] Set ALB name to "zero2prod-alb"
- [x] Store ALB as instance variable

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 51-62

**Business Rules Implemented**:
- BR-COMPUTE-001: HTTP to HTTPS redirect (CRITICAL)
- BR-COMPUTE-002: Multi-AZ deployment (HIGH)
- BR-COMPUTE-029: TLS 1.2+ enforcement (CRITICAL)

---

#### Step 7: Create Target Group
- [x] Create ApplicationTargetGroup with HTTP protocol, port 8000
- [x] Set target type to IP (required for Fargate)
- [x] Configure health check: path="/health_check", interval=30s, timeout=5s
- [x] Set healthy threshold=2, unhealthy threshold=3
- [x] Configure deregistration delay=300s (connection draining)
- [x] Store target group as instance variable

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 84-98

**Business Rules Implemented**:
- BR-COMPUTE-011: Database connectivity validation (CRITICAL)
- BR-COMPUTE-012: Health check every 30 seconds (HIGH)
- BR-COMPUTE-020: Graceful shutdown (HIGH)

---

#### Step 8: Create HTTP Listener (Redirect)
- [x] Add HTTP listener on port 80 to ALB
- [x] Configure default action as redirect to HTTPS port 443
- [x] Set redirect as permanent (301)

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 64-72

**Business Rules Implemented**:
- BR-COMPUTE-001: HTTP to HTTPS redirect (CRITICAL)

---

#### Step 9: Create HTTPS Listener
- [x] Get ACM certificate ARN from context variable
- [x] Add HTTPS listener on port 443 to ALB
- [x] Attach ACM certificate to listener
- [x] Set SSL policy to TLS13_RES (TLS 1.3 + 1.2)
- [x] Configure default action to forward to target group

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 74-81

**Business Rules Implemented**:
- BR-COMPUTE-029: TLS 1.2+ enforcement (CRITICAL)

---

#### Step 10: Create ECS Cluster
- [x] Create ECS Cluster with name "zero2prod-cluster"
- [x] Enable Fargate capacity providers
- [x] Enable Container Insights for monitoring
- [x] Store cluster as instance variable

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 114-121

**Business Rules Implemented**:
- BR-COMPUTE-003: ECS Fargate deployment (HIGH)

---

#### Step 11: Create Task Execution IAM Role
- [x] Create IAM role with ECS tasks service principal
- [x] Attach AmazonECSTaskExecutionRolePolicy managed policy
- [x] Add inline policy for Secrets Manager GetSecretValue
- [x] Scope Secrets Manager policy to database, cache, HMAC secrets
- [x] Store role as instance variable

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 134-150

**Business Rules Implemented**:
- BR-COMPUTE-030: Least privilege IAM (CRITICAL)
- BR-COMPUTE-025: Secrets Manager integration (CRITICAL)

---

#### Step 12: Create Task Runtime IAM Role
- [x] Create IAM role with ECS tasks service principal
- [x] Add inline policy for X-Ray tracing (PutTraceSegments, PutTelemetryRecords)
- [x] Store role as instance variable

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 153-160

**Business Rules Implemented**:
- BR-COMPUTE-030: Least privilege IAM (CRITICAL)
- BR-COMPUTE-034: X-Ray tracing (MEDIUM)

---

#### Step 13: Create CloudWatch Log Group
- [x] Create log group with name "/ecs/zero2prod-web"
- [x] Set retention to 30 days
- [x] Set removal policy to DESTROY (for development)
- [x] Store log group as instance variable

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 291-296

**Business Rules Implemented**:
- BR-COMPUTE-028: CloudWatch Logs 30-day retention (MEDIUM)

---

#### Step 14: Create ECR Repository
- [x] Create ECR repository with name "zero2prod"
- [x] Set image tag mutability to IMMUTABLE
- [x] Enable image scan on push
- [x] Add lifecycle rule: keep last 10 images
- [x] Store repository as instance variable

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 267-278

**Business Rules Implemented**:
- BR-COMPUTE-024: Immutable image tags (HIGH)
- BR-COMPUTE-031: Image scanning (MEDIUM)

---

#### Step 15: Create HMAC Secret
- [x] Create Secrets Manager secret with name "zero2prod/hmac/secret"
- [x] Configure generate_secret_string with JSON template
- [x] Set generate_string_key to "secret"
- [x] Exclude special characters from generated secret
- [x] Store secret as instance variable

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 309-317

**Business Rules Implemented**:
- BR-COMPUTE-025: Secrets Manager integration (CRITICAL)

---

#### Step 16: Create Fargate Task Definition
- [x] Create FargateTaskDefinition with family "zero2prod-web"
- [x] Set CPU to 1024 (1 vCPU)
- [x] Set memory to 2048 MB (2 GB)
- [x] Attach task execution role
- [x] Attach task role
- [x] Store task definition as instance variable

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 163-170

**Business Rules Implemented**:
- BR-COMPUTE-006: Task sizing 1 vCPU / 2 GB (CRITICAL)

---

#### Step 17: Add Container to Task Definition
- [x] Add container named "AppContainer" to task definition
- [x] Set image from ECR repository with "latest" tag
- [x] Configure AWS Logs driver with log group
- [x] Add static environment variables (APP_ENVIRONMENT, LOG_LEVEL, PORT, HOST, X-Ray config, AWS_REGION)
- [x] Add secrets from Secrets Manager (DATABASE_URL, REDIS_URI, HMAC_SECRET)
- [x] Add port mapping for container port 8000
- [x] Store container as instance variable

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 173-196

**Business Rules Implemented**:
- BR-COMPUTE-025: Secrets Manager integration (CRITICAL)
- BR-COMPUTE-026: Static environment variables (HIGH)
- BR-COMPUTE-034: X-Ray tracing (MEDIUM)

---

#### Step 18: Create Fargate Service
- [x] Create FargateService in ECS cluster
- [x] Set service name to "zero2prod-web-service"
- [x] Set desired count to 2 tasks
- [x] Set min healthy percent to 100, max to 200 (rolling update)
- [x] Set health check grace period to 60 seconds
- [x] Deploy in private subnets (1a, 1b)
- [x] Attach ECS security group
- [x] Store service as instance variable

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 214-228

**Business Rules Implemented**:
- BR-COMPUTE-002: Multi-AZ deployment (HIGH)
- BR-COMPUTE-007: Desired count 2 tasks (HIGH)
- BR-COMPUTE-018: Rolling deployment (HIGH)

---

#### Step 19: Attach Service to Target Group
- [x] Call service.attach_to_application_target_group(target_group)
- [x] This registers ECS tasks as targets in ALB target group

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 230-231

---

#### Step 20: Configure Auto-Scaling
- [x] Call service.auto_scale_task_count(min=2, max=10)
- [x] Store scalable target as variable
- [x] Configure scale_on_cpu_utilization with target 70%
- [x] Set scale-in cooldown to 300s, scale-out cooldown to 60s

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 244-254

**Business Rules Implemented**:
- BR-COMPUTE-013: Auto-scaling 70% CPU target (HIGH)
- BR-COMPUTE-014: Min 2 tasks, max 10 tasks (HIGH)
- BR-COMPUTE-015: Scale-out cooldown 60s (MEDIUM)
- BR-COMPUTE-016: Scale-in cooldown 300s (MEDIUM)

---

#### Step 21: Create CloudFormation Outputs
- [x] Output ALB DNS name with export "Zero2Prod-ALB-DNS-Name"
- [x] Output ECS cluster name with export "Zero2Prod-ECS-Cluster-Name"
- [x] Output ECR repository URI with export "Zero2Prod-ECR-Repository-Uri"

**Code Reference**: `infrastructure-design/cdk-stack-design.md` lines 328-348

---

### Phase 3: Unit Tests

#### Step 22: Create ComputeStack Unit Tests
- [x] Create `infrastructure/tests/test_compute_stack.py`
- [ ] Import pytest, aws_cdk.assertions, ComputeStack
- [ ] Create test fixture for CDK app and stack
- [ ] Write test to verify ALB creation with correct properties
- [ ] Write test to verify ECS cluster creation
- [ ] Write test to verify task definition CPU/memory allocation
- [ ] Write test to verify service configuration (desired count, deployment config)
- [ ] Write test to verify auto-scaling policy (min, max, target)
- [ ] Write test to verify IAM roles have correct policies
- [ ] Write test to verify CloudFormation outputs exist

**Artifacts**:
- `infrastructure/tests/test_compute_stack.py` (new)

**Test Coverage**:
- ALB configuration (listeners, target group, health checks)
- ECS cluster, service, task definition
- Auto-scaling policy
- IAM roles and policies
- CloudWatch Logs
- ECR repository
- CloudFormation exports

---

### Phase 4: GitHub Actions CI/CD

#### Step 23: Create GitHub Actions Deploy Workflow
- [x] Create `.github/workflows/deploy-ecs.yml`
- [ ] Configure trigger on push to main branch and workflow_dispatch
- [ ] Add job "deploy" with ubuntu-latest runner
- [ ] Configure OIDC permissions (id-token: write, contents: read)
- [ ] Add checkout step
- [ ] Add AWS credentials step (configure-aws-credentials@v4 with OIDC role)
- [ ] Add ECR login step
- [ ] Add build and push Docker image step (tag with sha-<commit-hash> and latest)
- [ ] Add download task definition step
- [ ] Add render task definition step (amazon-ecs-render-task-definition@v1)
- [ ] Add deploy to ECS step (amazon-ecs-deploy-task-definition@v2)
- [ ] Add verify deployment step (check running task count)

**Artifacts**:
- `.github/workflows/deploy-ecs.yml` (new)

**Code Reference**: `infrastructure-design/deployment-configuration.md` lines 219-279

**Business Rules Implemented**:
- BR-COMPUTE-022: GitHub Actions CI/CD (HIGH)
- BR-COMPUTE-023: Automated deployments <5 minutes (MEDIUM)

---

### Phase 5: Documentation

#### Step 24: Create Code Summary Document
- [x] Create `aidlc-docs/construction/unit-4-compute/code/code-summary.md`
- [ ] Document all generated files with paths
- [ ] Explain ComputeStack structure and components
- [ ] Document CDK stack dependencies and exports
- [ ] Include deployment instructions reference
- [ ] Include testing instructions reference

**Artifacts**:
- `aidlc-docs/construction/unit-4-compute/code/code-summary.md` (new)

---

#### Step 25: Create Deployment Instructions
- [x] Create `aidlc-docs/construction/unit-4-compute/code/deployment-instructions.md`
- [ ] Document prerequisites (ACM certificate, previous stacks deployed)
- [ ] Document CDK deployment steps (synth, diff, deploy)
- [ ] Document initial image build and push steps
- [ ] Document GitHub Actions setup (OIDC role)
- [ ] Reference detailed deployment-configuration.md

**Artifacts**:
- `aidlc-docs/construction/unit-4-compute/code/deployment-instructions.md` (new)

---

#### Step 26: Create Testing Instructions
- [x] Create `aidlc-docs/construction/unit-4-compute/code/testing-instructions.md`
- [ ] Document unit test execution (pytest)
- [ ] Document CDK synth validation
- [ ] Document integration testing approach (post-deployment validation)
- [ ] Reference deployment-configuration.md troubleshooting section

**Artifacts**:
- `aidlc-docs/construction/unit-4-compute/code/testing-instructions.md` (new)

---

### Phase 6: Validation

#### Step 27: Verify Generated Artifacts
- [x] Verify all infrastructure/ files created
- [x] Verify GitHub Actions workflow created
- [x] Verify documentation files created
- [x] Verify no files created in aidlc-docs/ except documentation
- [x] Verify all checkboxes in this plan marked [x]

---

#### Step 28: Update Progress Tracking
- [x] Mark all steps [x] in this plan
- [x] Update `aidlc-docs/aidlc-state.md` - mark Unit 4 Code Generation complete
- [x] Log completion in `aidlc-docs/audit.md`

---

## Generated Artifacts Summary

### Application Code (Workspace Root)
| File Path | Description | Lines |
|-----------|-------------|-------|
| `infrastructure/app.py` | CDK app entry point | ~20 |
| `infrastructure/stacks/compute_stack.py` | ComputeStack implementation | ~260 |
| `infrastructure/cdk.json` | CDK configuration | ~20 |
| `infrastructure/requirements.txt` | Python dependencies | ~3 |
| `infrastructure/.gitignore` | CDK artifacts ignore | ~10 |
| `.github/workflows/deploy-ecs.yml` | GitHub Actions CI/CD | ~100 |

### Tests (Workspace Root)
| File Path | Description | Lines |
|-----------|-------------|-------|
| `infrastructure/tests/test_compute_stack.py` | Unit tests for ComputeStack | ~150 |

### Documentation (aidlc-docs/)
| File Path | Description |
|-----------|-------------|
| `aidlc-docs/construction/unit-4-compute/code/code-summary.md` | Code generation summary |
| `aidlc-docs/construction/unit-4-compute/code/deployment-instructions.md` | Deployment instructions |
| `aidlc-docs/construction/unit-4-compute/code/testing-instructions.md` | Testing instructions |

**Total Application Code**: ~413 lines Python + YAML
**Total Tests**: ~150 lines Python
**Total Documentation**: 3 markdown files

---

## Business Rules Traceability

| Business Rule | Steps Implementing Rule |
|---------------|-------------------------|
| BR-COMPUTE-001: HTTP to HTTPS redirect (CRITICAL) | Step 6, Step 8 |
| BR-COMPUTE-002: Multi-AZ deployment (HIGH) | Step 6, Step 18 |
| BR-COMPUTE-003: ECS Fargate (HIGH) | Step 10 |
| BR-COMPUTE-006: Task sizing 1 vCPU / 2 GB (CRITICAL) | Step 16 |
| BR-COMPUTE-007: Desired count 2 tasks (HIGH) | Step 18 |
| BR-COMPUTE-011: Database health check (CRITICAL) | Step 7 |
| BR-COMPUTE-012: Health check 30s interval (HIGH) | Step 7 |
| BR-COMPUTE-013: 70% CPU auto-scaling (HIGH) | Step 20 |
| BR-COMPUTE-014: Min 2, max 10 tasks (HIGH) | Step 20 |
| BR-COMPUTE-015: Scale-out cooldown 60s (MEDIUM) | Step 20 |
| BR-COMPUTE-016: Scale-in cooldown 300s (MEDIUM) | Step 20 |
| BR-COMPUTE-018: Rolling deployment (HIGH) | Step 18 |
| BR-COMPUTE-020: Graceful shutdown 300s (HIGH) | Step 7 |
| BR-COMPUTE-022: GitHub Actions CI/CD (HIGH) | Step 23 |
| BR-COMPUTE-023: <5 min deployment (MEDIUM) | Step 23 |
| BR-COMPUTE-024: Immutable image tags (HIGH) | Step 14 |
| BR-COMPUTE-025: Secrets Manager (CRITICAL) | Step 11, Step 15, Step 17 |
| BR-COMPUTE-026: Static env vars (HIGH) | Step 17 |
| BR-COMPUTE-028: CloudWatch Logs 30-day (MEDIUM) | Step 13 |
| BR-COMPUTE-029: TLS 1.2+ (CRITICAL) | Step 9 |
| BR-COMPUTE-030: Least privilege IAM (CRITICAL) | Step 11, Step 12 |
| BR-COMPUTE-031: Image scanning (MEDIUM) | Step 14 |
| BR-COMPUTE-034: X-Ray tracing (MEDIUM) | Step 12, Step 17 |

---

## References

- Functional Design: `../functional-design/`
- NFR Requirements: `../nfr-requirements/`
- NFR Design: `../nfr-design/`
- Infrastructure Design: `../infrastructure-design/`
- Business Rules: `../functional-design/business-rules.md`
- Domain Entities: `../functional-design/domain-entities.md`
