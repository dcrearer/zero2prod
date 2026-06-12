# Unit 4: Compute Infrastructure - Domain Entities

## Overview

This document defines the domain entities for the ECS Fargate compute infrastructure. These entities represent the configuration and state of the application deployment platform.

**Design Date**: 2026-06-12  
**Unit**: 4 of 8 (Compute Infrastructure)

---

## Entity 1: Application Load Balancer Configuration

**Entity Name**: `ALBConfiguration`

**Purpose**: Defines the ALB configuration for routing HTTPS traffic to ECS tasks

### Attributes

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `name` | String | ALB resource name | `"zero2prod-alb"` |
| `scheme` | Enum | Internet-facing or internal | `InternetFacing` |
| `ip_address_type` | Enum | IPv4 or dualstack | `IPv4` |
| `subnets` | List[SubnetId] | Public subnets for ALB | 2 subnets (AZ-A, AZ-B) |
| `security_groups` | List[SecurityGroupId] | ALB security group | 1 security group |
| `deletion_protection` | Boolean | Prevent accidental deletion | `true` (production) |
| `access_logs_enabled` | Boolean | S3 access logging | `true` (SECURITY-02) |
| `access_logs_bucket` | String | S3 bucket for logs | Created in Unit 7 |
| `access_logs_prefix` | String | S3 key prefix | `"alb-logs/"` |
| `access_logs_retention` | Integer | Days to retain logs | `30` days |

### HTTP Listener Configuration

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `protocol` | Enum | HTTP or HTTPS | `HTTP` |
| `port` | Integer | Listener port | `80` |
| `default_action_type` | Enum | Redirect, forward, etc. | `Redirect` |
| `redirect_protocol` | Enum | HTTPS | `HTTPS` |
| `redirect_port` | Integer | Redirect port | `443` |
| `redirect_status_code` | Integer | HTTP status | `301` (permanent) |

### HTTPS Listener Configuration

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `protocol` | Enum | HTTP or HTTPS | `HTTPS` |
| `port` | Integer | Listener port | `443` |
| `ssl_policy` | String | TLS policy | `"ELBSecurityPolicy-TLS13-1-2-2021-06"` |
| `certificate_arn` | String | ACM certificate ARN | Existing cert for domain |
| `default_action_type` | Enum | Forward to target group | `Forward` |
| `target_group_arn` | String | ECS target group ARN | Reference to TargetGroup entity |

### Target Group Configuration

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `name` | String | Target group name | `"zero2prod-tg"` |
| `protocol` | Enum | HTTP or HTTPS | `HTTP` |
| `port` | Integer | Container port | `8000` |
| `vpc_id` | String | VPC ID | From Unit 1 |
| `target_type` | Enum | Instance or IP | `IP` (Fargate) |
| `deregistration_delay` | Integer | Connection draining | `300` seconds |
| `health_check_enabled` | Boolean | Health check enabled | `true` |
| `health_check_path` | String | Health check endpoint | `"/health_check"` |
| `health_check_protocol` | Enum | HTTP or HTTPS | `HTTP` |
| `health_check_port` | Integer | Health check port | `8000` |
| `health_check_interval` | Integer | Interval in seconds | `30` seconds |
| `health_check_timeout` | Integer | Timeout in seconds | `5` seconds |
| `healthy_threshold_count` | Integer | Healthy threshold | `2` consecutive successes |
| `unhealthy_threshold_count` | Integer | Unhealthy threshold | `3` consecutive failures |
| `health_check_matcher` | String | Expected status codes | `"200"` |

**Entity Constraints**:
- ALB MUST be deployed in at least 2 availability zones
- HTTPS listener MUST have valid ACM certificate
- Target group MUST use IP target type for Fargate

---

## Entity 2: ECS Cluster Configuration

**Entity Name**: `ECSClusterConfiguration`

**Purpose**: Defines the ECS cluster for hosting Fargate tasks

### Attributes

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `cluster_name` | String | ECS cluster name | `"zero2prod-cluster"` |
| `capacity_providers` | List[String] | Capacity providers | `["FARGATE"]` |
| `default_capacity_provider_strategy` | Object | Default strategy | Fargate with weight 1 |
| `container_insights_enabled` | Boolean | CloudWatch Container Insights | `true` (monitoring) |
| `tags` | Map[String, String] | Resource tags | Environment, Project, etc. |

**Entity Constraints**:
- Cluster MUST use Fargate capacity provider
- Container Insights MUST be enabled for observability

---

## Entity 3: ECS Task Definition Configuration

**Entity Name**: `ECSTaskDefinitionConfiguration`

**Purpose**: Defines the ECS task definition for running the zero2prod application container

### Attributes

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `family` | String | Task definition family | `"zero2prod-web"` |
| `requires_compatibilities` | List[Enum] | Launch type | `["FARGATE"]` |
| `network_mode` | Enum | Network mode | `awsvpc` (required for Fargate) |
| `cpu` | String | CPU units | `"1024"` (1 vCPU) |
| `memory` | String | Memory in MB | `"2048"` (2 GB) |
| `execution_role_arn` | String | Task execution role ARN | Reference to TaskExecutionRole entity |
| `task_role_arn` | String | Task role ARN | Reference to TaskRole entity |
| `runtime_platform` | Object | OS and architecture | Linux/AMD64 or Linux/ARM64 |

### Container Definition

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `name` | String | Container name | `"zero2prod-app"` |
| `image` | String | ECR image URI | `"<account>.dkr.ecr.us-east-1.amazonaws.com/zero2prod:sha-<hash>"` |
| `port_mappings` | List[Object] | Container ports | Port 8000, Protocol TCP |
| `essential` | Boolean | Essential container | `true` (task stops if container stops) |
| `environment` | List[Object] | Static environment variables | See Environment Variables entity |
| `secrets` | List[Object] | Secrets from Secrets Manager | See Secrets entity |
| `log_configuration` | Object | CloudWatch Logs config | See Logging entity |
| `health_check` | Object | Container health check | Optional (ALB health check is primary) |

**Entity Constraints**:
- Task MUST use Fargate launch type
- Task MUST have exactly 1 essential container
- CPU/memory MUST be valid Fargate combinations (1 vCPU / 2 GB)
- Container port MUST match target group port (8000)

---

## Entity 4: Environment Variables Configuration

**Entity Name**: `EnvironmentVariablesConfiguration`

**Purpose**: Defines static environment variables injected into ECS task

### Static Environment Variables

| Name | Value | Purpose | Business Rule |
|------|-------|---------|---------------|
| `APP_ENVIRONMENT` | `"production"` | Application environment | Static value |
| `APP_LOG_LEVEL` | `"info"` | Log level | `info` for production |
| `APP_APPLICATION__PORT` | `"8000"` | Application port | MUST match container port mapping |
| `APP_APPLICATION__HOST` | `"0.0.0.0"` | Bind address | Bind to all interfaces |
| `AWS_XRAY_DAEMON_ADDRESS` | `"xray-daemon:2000"` | X-Ray daemon endpoint | Enable distributed tracing |
| `AWS_XRAY_TRACING_NAME` | `"zero2prod-web"` | X-Ray service name | Identify service in traces |
| `AWS_REGION` | `"us-east-1"` | AWS region | For SDK calls |

### Secrets from Secrets Manager

| Environment Variable | Secret Name | Secret Key | Purpose |
|---------------------|-------------|------------|---------|
| `DATABASE_URL` | `zero2prod/database/connection-string` | `connection_string` | Aurora connection |
| `REDIS_URI` | `zero2prod/cache/connection-string` | `connection_string` | ElastiCache connection |
| `HMAC_SECRET` | `zero2prod/hmac/secret` | `secret` | Session signing |

**Entity Constraints**:
- Static variables MUST NOT contain sensitive data
- Secrets MUST be loaded from Secrets Manager (not hardcoded)
- APP_APPLICATION__PORT MUST match container port mapping (8000)
- AWS_XRAY_DAEMON_ADDRESS MUST be configured for distributed tracing

---

## Entity 5: ECS Service Configuration

**Entity Name**: `ECSServiceConfiguration`

**Purpose**: Defines the ECS service for managing ECS tasks

### Attributes

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `service_name` | String | ECS service name | `"zero2prod-web-service"` |
| `cluster` | String | ECS cluster ARN | Reference to ECSCluster entity |
| `task_definition` | String | Task definition ARN | Reference to TaskDefinition entity |
| `launch_type` | Enum | Fargate or EC2 | `FARGATE` |
| `desired_count` | Integer | Desired task count | `2` (Multi-AZ HA) |
| `platform_version` | String | Fargate platform version | `"LATEST"` |
| `health_check_grace_period_seconds` | Integer | Health check grace period | `60` seconds |
| `enable_ecs_managed_tags` | Boolean | ECS-managed tags | `true` |
| `enable_execute_command` | Boolean | ECS Exec (debugging) | `true` (optional) |

### Network Configuration

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `subnets` | List[SubnetId] | Private subnets | 2 subnets (AZ-A, AZ-B) |
| `security_groups` | List[SecurityGroupId] | ECS security group | 1 security group |
| `assign_public_ip` | Enum | Public IP assignment | `DISABLED` (private subnets) |

### Load Balancer Configuration

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `target_group_arn` | String | ALB target group ARN | Reference to TargetGroup entity |
| `container_name` | String | Container name | `"zero2prod-app"` |
| `container_port` | Integer | Container port | `8000` |

### Deployment Configuration

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `deployment_maximum_percent` | Integer | Max percent during deployment | `200` (double capacity) |
| `deployment_minimum_healthy_percent` | Integer | Min healthy percent | `100` (no downtime) |
| `deployment_controller_type` | Enum | Deployment controller | `ECS` (rolling update) |

**Entity Constraints**:
- Service MUST have minimum 2 desired tasks (Multi-AZ HA)
- Service MUST be deployed in private subnets
- Service MUST NOT have public IP assigned
- Service MUST use load balancer with target group
- Deployment config MUST ensure zero downtime (100% min healthy)

---

## Entity 6: Auto-Scaling Configuration

**Entity Name**: `AutoScalingConfiguration`

**Purpose**: Defines auto-scaling policy for ECS service

### Attributes

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `policy_name` | String | Scaling policy name | `"zero2prod-cpu-scaling-policy"` |
| `policy_type` | Enum | Scaling policy type | `TargetTrackingScaling` |
| `target_tracking_scaling_policy_configuration` | Object | Policy config | See below |
| `min_capacity` | Integer | Minimum task count | `2` tasks |
| `max_capacity` | Integer | Maximum task count | `10` tasks |

### Target Tracking Policy Configuration

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `predefined_metric_type` | Enum | Metric to track | `ECSServiceAverageCPUUtilization` |
| `target_value` | Float | Target value | `70.0` (70% CPU) |
| `scale_out_cooldown` | Integer | Scale-out cooldown | `60` seconds |
| `scale_in_cooldown` | Integer | Scale-in cooldown | `300` seconds |

**Entity Constraints**:
- Min capacity MUST be 2 (Multi-AZ HA)
- Max capacity MUST be 10 (cost control)
- Target value MUST be 70% CPU utilization
- Scale-in cooldown MUST be longer than scale-out (prevent thrashing)

---

## Entity 7: IAM Task Execution Role

**Entity Name**: `TaskExecutionRoleConfiguration`

**Purpose**: IAM role for ECS task execution (pull images, write logs)

### Attributes

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `role_name` | String | IAM role name | `"zero2prod-task-execution-role"` |
| `assume_role_policy` | Object | Trust policy | ECS tasks service principal |
| `managed_policy_arns` | List[String] | Managed policies | `["arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"]` |
| `inline_policies` | List[Object] | Custom policies | Secrets Manager read access |

### Permissions

| Service | Actions | Resources | Purpose |
|---------|---------|-----------|---------|
| ECR | `GetAuthorizationToken`, `BatchCheckLayerAvailability`, `GetDownloadUrlForLayer`, `BatchGetImage` | All ECR repositories | Pull container images |
| CloudWatch Logs | `CreateLogStream`, `PutLogEvents` | Task log group | Write application logs |
| Secrets Manager | `GetSecretValue` | `zero2prod/database/*`, `zero2prod/cache/*`, `zero2prod/hmac/*` | Load secrets at startup |

**Entity Constraints**:
- Role MUST have ECS tasks service principal in trust policy
- Role MUST have AmazonECSTaskExecutionRolePolicy managed policy
- Role MUST have GetSecretValue permission for application secrets
- Role MUST follow least privilege principle

---

## Entity 8: IAM Task Role

**Entity Name**: `TaskRoleConfiguration`

**Purpose**: IAM role for application code running in ECS task (Aurora, CloudWatch, X-Ray)

### Attributes

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `role_name` | String | IAM role name | `"zero2prod-task-role"` |
| `assume_role_policy` | Object | Trust policy | ECS tasks service principal |
| `inline_policies` | List[Object] | Custom policies | Aurora, X-Ray, Secrets Manager |

### Permissions

| Service | Actions | Resources | Purpose |
|---------|---------|-----------|---------|
| Secrets Manager | `GetSecretValue` | `zero2prod/database/*`, `zero2prod/cache/*` | Runtime secret access |
| CloudWatch Logs | `CreateLogStream`, `PutLogEvents` | Application log group | Write application logs |
| X-Ray | `PutTraceSegments`, `PutTelemetryRecords` | All resources | Send distributed traces |
| RDS | `rds-db:connect` | Aurora cluster resource (optional) | IAM database authentication |

**Entity Constraints**:
- Role MUST have ECS tasks service principal in trust policy
- Role MUST have minimal permissions (least privilege)
- Role MUST have X-Ray permissions for distributed tracing
- Role MUST NOT have write access to Secrets Manager (read-only)

---

## Entity 9: ECR Repository Configuration

**Entity Name**: `ECRRepositoryConfiguration`

**Purpose**: Container registry for zero2prod Docker images

### Attributes

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `repository_name` | String | ECR repository name | `"zero2prod"` |
| `image_tag_mutability` | Enum | Tag mutability | `IMMUTABLE` (prevent tag overwrites) |
| `image_scanning_on_push` | Boolean | Scan on push | `true` (security scanning) |
| `lifecycle_policy` | Object | Image retention policy | Keep last 10 images |
| `encryption_configuration` | Object | Encryption at rest | AES-256 (default) |

### Lifecycle Policy

| Rule | Description | Action |
|------|-------------|--------|
| Keep Last 10 Images | Retain only 10 most recent images | Delete older images |
| Untagged Images | Delete untagged images after 1 day | Cleanup orphaned layers |

**Entity Constraints**:
- Repository MUST have immutable tags (prevent accidental overwrites)
- Repository MUST enable image scanning on push (security)
- Repository MUST have lifecycle policy (cost optimization)
- Repository MUST be encrypted at rest

---

## Entity 10: CloudWatch Log Group Configuration

**Entity Name**: `CloudWatchLogGroupConfiguration`

**Purpose**: Centralized logging for ECS tasks

### Attributes

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `log_group_name` | String | Log group name | `"/ecs/zero2prod-web"` |
| `retention_in_days` | Integer | Log retention period | `30` days |
| `kms_key_id` | String | KMS encryption key (optional) | Default CloudWatch encryption |

### Log Stream Configuration

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `log_stream_prefix` | String | Stream prefix | `"ecs"` |
| `awslogs_region` | String | AWS region | `"us-east-1"` |
| `awslogs_stream_prefix` | String | Stream prefix | `"zero2prod-web"` |

**Entity Constraints**:
- Log group MUST have 30-day retention (balance cost and troubleshooting)
- Log streams MUST be named with task ID for traceability
- Logs MUST be encrypted at rest (CloudWatch default encryption)

---

## Entity 11: GitHub Actions Deployment Configuration

**Entity Name**: `GitHubActionsDeploymentConfiguration`

**Purpose**: CI/CD pipeline configuration for building and deploying container images

### Attributes

| Attribute | Type | Description | Business Rule |
|-----------|------|-------------|---------------|
| `workflow_name` | String | GitHub Actions workflow | `"Deploy to ECS"` |
| `trigger` | Object | Workflow trigger | Push to main branch |
| `docker_build_args` | List[String] | Docker build arguments | None (use defaults) |
| `ecr_repository` | String | ECR repository name | `"zero2prod"` |
| `image_tag_strategy` | Enum | Image tagging | `sha-<git-hash>` |
| `ecs_cluster_name` | String | ECS cluster name | `"zero2prod-cluster"` |
| `ecs_service_name` | String | ECS service name | `"zero2prod-web-service"` |
| `ecs_task_definition` | String | Task definition family | `"zero2prod-web"` |

### Workflow Steps

1. **Checkout Code**: Clone repository
2. **Configure AWS Credentials**: Assume IAM role with ECR/ECS permissions
3. **Login to ECR**: Authenticate Docker to ECR
4. **Build Docker Image**: Multi-stage build from Dockerfile
5. **Tag Image**: `sha-<git-commit-hash>`
6. **Push to ECR**: Push image to ECR repository
7. **Update Task Definition**: Create new revision with new image
8. **Deploy to ECS**: Update ECS service with new task definition
9. **Wait for Deployment**: Poll until service reaches steady state

**Entity Constraints**:
- Workflow MUST trigger on push to main branch only
- Image tag MUST be immutable (sha-based)
- Workflow MUST wait for deployment to reach steady state before completing
- Workflow MUST fail if health checks fail

---

## Entity Relationships

```
┌───────────────────────────────────────────────────────────────────┐
│  Application Load Balancer                                         │
│  ┌─────────────────┐     ┌─────────────────┐                     │
│  │  HTTP Listener  │     │  HTTPS Listener │                     │
│  │  (Port 80)      │────▶│  (Port 443)     │                     │
│  │  Redirect       │     │  ACM Certificate│                     │
│  └─────────────────┘     └────────┬────────┘                     │
│                                    │                               │
│                           ┌────────▼────────┐                     │
│                           │  Target Group   │                     │
│                           │  (Port 8000)    │                     │
│                           │  Health Check   │                     │
│                           └────────┬────────┘                     │
└────────────────────────────────────┼──────────────────────────────┘
                                     │
                        ┌────────────┼────────────┐
                        │            │            │
                        ▼            ▼            ▼
            ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
            │  ECS Task 1     │ │  ECS Task 2     │ │  ECS Task N     │
            │  ┌───────────┐  │ │  ┌───────────┐  │ │  ┌───────────┐  │
            │  │Container  │  │ │  │Container  │  │ │  │Container  │  │
            │  │Port 8000  │  │ │  │Port 8000  │  │ │  │Port 8000  │  │
            │  └───────────┘  │ │  └───────────┘  │ │  └───────────┘  │
            │  ┌───────────┐  │ │  ┌───────────┐  │ │  ┌───────────┐  │
            │  │Task Role  │  │ │  │Task Role  │  │ │  │Task Role  │  │
            │  └───────────┘  │ │  └───────────┘  │ │  └───────────┘  │
            └─────────────────┘ └─────────────────┘ └─────────────────┘
                        │            │            │
                        └────────────┼────────────┘
                                     │
                        ┌────────────▼────────────┐
                        │  ECS Service            │
                        │  ┌──────────────────┐   │
                        │  │ Auto-Scaling     │   │
                        │  │ Policy           │   │
                        │  │ Target: 70% CPU  │   │
                        │  └──────────────────┘   │
                        └─────────────────────────┘
                                     │
                        ┌────────────▼────────────┐
                        │  ECS Cluster            │
                        │  (Fargate)              │
                        └─────────────────────────┘
```

---

## Summary

The compute infrastructure domain model defines 11 core entities:
1. **ALB Configuration**: HTTP→HTTPS redirect, target group, health checks
2. **ECS Cluster**: Fargate capacity provider, Container Insights
3. **Task Definition**: 1 vCPU / 2 GB RAM, container configuration
4. **Environment Variables**: Static config + Secrets Manager secrets
5. **ECS Service**: 2 desired tasks, rolling update deployment
6. **Auto-Scaling**: CPU-based scaling, 2-10 tasks
7. **Task Execution Role**: ECR pull, CloudWatch logs, Secrets Manager read
8. **Task Role**: Runtime permissions (Aurora, X-Ray, Secrets Manager)
9. **ECR Repository**: Immutable tags, image scanning, lifecycle policy
10. **CloudWatch Log Group**: 30-day retention, encrypted logs
11. **GitHub Actions Deployment**: CI/CD pipeline for builds and deployments

These entities collectively define the complete ECS Fargate deployment platform for the zero2prod web application.
