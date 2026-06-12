# Unit 4: Compute Infrastructure - CDK Stack Design

## Overview

This document defines the AWS CDK implementation for the ComputeStack, mapping logical components to AWS CloudFormation resources.

**Design Date**: 2026-06-12  
**Unit**: 4 of 8 (Compute Infrastructure)  
**Stack Name**: `Zero2ProdComputeStack`

---

## CDK Stack Architecture

```python
class ComputeStack(Stack):
    """
    Compute infrastructure for zero2prod web application.
    
    Dependencies:
    - NetworkStack (Unit 1): VPC, subnets, security groups
    - DatabaseStack (Unit 2): Database secret ARN, SNS topic
    - CacheStack (Unit 3): Cache secret ARN
    
    Exports:
    - ECS cluster name (for Unit 5 - Worker)
    - ALB DNS name (for Route53/CloudFront)
    - ECR repository URI (for GitHub Actions)
    """
```

---

## Component Mapping to AWS CDK

### 1. Application Load Balancer

**AWS Service**: `aws_cdk.aws_elasticloadbalancingv2.ApplicationLoadBalancer`

**CDK Implementation** (~80 lines):
```python
# Import VPC and subnets from NetworkStack
vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id=Fn.import_value("Zero2Prod-VPC-Id"))
public_subnet_1a = Fn.import_value("Zero2Prod-PublicSubnet-1a-Id")
public_subnet_1b = Fn.import_value("Zero2Prod-PublicSubnet-1b-Id")

# Import ALB security group from NetworkStack
alb_sg_id = Fn.import_value("Zero2Prod-ALB-SG-Id")

# Create ALB
alb = elbv2.ApplicationLoadBalancer(
    self, "ALB",
    vpc=vpc,
    internet_facing=True,
    load_balancer_name="zero2prod-alb",
    security_group=ec2.SecurityGroup.from_security_group_id(self, "ALBSG", alb_sg_id),
    vpc_subnets=ec2.SubnetSelection(subnets=[
        ec2.Subnet.from_subnet_id(self, "PublicSubnet1a", public_subnet_1a),
        ec2.Subnet.from_subnet_id(self, "PublicSubnet1b", public_subnet_1b)
    ])
)

# HTTP Listener (redirect to HTTPS)
http_listener = alb.add_listener(
    "HttpListener",
    port=80,
    default_action=elbv2.ListenerAction.redirect(
        protocol="HTTPS",
        port="443",
        permanent=True  # 301 redirect
    )
)

# HTTPS Listener
https_listener = alb.add_listener(
    "HttpsListener",
    port=443,
    certificates=[elbv2.ListenerCertificate.from_arn(certificate_arn)],
    ssl_policy=elbv2.SslPolicy.TLS13_RES,  # TLS 1.3 + 1.2
    default_action=elbv2.ListenerAction.forward([target_group])
)

# Target Group
target_group = elbv2.ApplicationTargetGroup(
    self, "TargetGroup",
    vpc=vpc,
    port=8000,
    protocol=elbv2.ApplicationProtocol.HTTP,
    target_type=elbv2.TargetType.IP,  # Required for Fargate
    health_check=elbv2.HealthCheck(
        path="/health_check",
        interval=Duration.seconds(30),
        timeout=Duration.seconds(5),
        healthy_threshold_count=2,
        unhealthy_threshold_count=3
    ),
    deregistration_delay=Duration.seconds(300)  # Connection draining
)

# ALB Access Logs (S3 bucket created in Unit 7)
# alb.log_access_logs(bucket, prefix="alb-logs/")  # Enable after Unit 7
```

**Estimated Lines**: ~80 lines Python

---

### 2. ECS Cluster

**AWS Service**: `aws_cdk.aws_ecs.Cluster`

**CDK Implementation** (~15 lines):
```python
cluster = ecs.Cluster(
    self, "Cluster",
    cluster_name="zero2prod-cluster",
    vpc=vpc,
    container_insights=True,  # Enable Container Insights
    enable_fargate_capacity_providers=True
)
```

**Estimated Lines**: ~15 lines Python

---

### 3. ECS Task Definition

**AWS Service**: `aws_cdk.aws_ecs.FargateTaskDefinition`

**CDK Implementation** (~60 lines):
```python
# Task Execution Role
task_execution_role = iam.Role(
    self, "TaskExecutionRole",
    assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
    managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
            "service-role/AmazonECSTaskExecutionRolePolicy"
        )
    ]
)

# Grant Secrets Manager read access
database_secret_arn = Fn.import_value("Zero2Prod-Database-Secret-Arn")
cache_secret_arn = Fn.import_value("Zero2Prod-Cache-Secret-Arn")
task_execution_role.add_to_policy(iam.PolicyStatement(
    actions=["secretsmanager:GetSecretValue"],
    resources=[database_secret_arn, cache_secret_arn, "arn:aws:secretsmanager:*:*:secret:zero2prod/hmac/*"]
))

# Task Role
task_role = iam.Role(
    self, "TaskRole",
    assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com")
)
task_role.add_to_policy(iam.PolicyStatement(
    actions=["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
    resources=["*"]
))

# Task Definition
task_definition = ecs.FargateTaskDefinition(
    self, "TaskDefinition",
    family="zero2prod-web",
    cpu=1024,  # 1 vCPU
    memory_limit_mib=2048,  # 2 GB
    execution_role=task_execution_role,
    task_role=task_role
)

# Container
container = task_definition.add_container(
    "AppContainer",
    image=ecs.ContainerImage.from_ecr_repository(ecr_repository, tag="latest"),
    logging=ecs.LogDrivers.aws_logs(
        stream_prefix="zero2prod-web",
        log_group=log_group
    ),
    environment={
        "APP_ENVIRONMENT": "production",
        "APP_LOG_LEVEL": "info",
        "APP_APPLICATION__PORT": "8000",
        "APP_APPLICATION__HOST": "0.0.0.0",
        "AWS_XRAY_DAEMON_ADDRESS": "xray-daemon:2000",
        "AWS_XRAY_TRACING_NAME": "zero2prod-web",
        "AWS_REGION": "us-east-1"
    },
    secrets={
        "DATABASE_URL": ecs.Secret.from_secrets_manager(database_secret, field="connection_string"),
        "REDIS_URI": ecs.Secret.from_secrets_manager(cache_secret, field="connection_string"),
        "HMAC_SECRET": ecs.Secret.from_secrets_manager(hmac_secret, field="secret")
    }
)

container.add_port_mappings(ecs.PortMapping(container_port=8000))
```

**Estimated Lines**: ~60 lines Python

---

### 4. ECS Service

**AWS Service**: `aws_cdk.aws_ecs.FargateService`

**CDK Implementation** (~30 lines):
```python
# Import private subnets and ECS security group
private_subnet_1a = Fn.import_value("Zero2Prod-PrivateSubnet-1a-Id")
private_subnet_1b = Fn.import_value("Zero2Prod-PrivateSubnet-1b-Id")
ecs_sg_id = Fn.import_value("Zero2Prod-ECS-SG-Id")

service = ecs.FargateService(
    self, "Service",
    cluster=cluster,
    task_definition=task_definition,
    service_name="zero2prod-web-service",
    desired_count=2,
    min_healthy_percent=100,
    max_healthy_percent=200,
    health_check_grace_period=Duration.seconds(60),
    vpc_subnets=ec2.SubnetSelection(subnets=[
        ec2.Subnet.from_subnet_id(self, "PrivateSubnet1a", private_subnet_1a),
        ec2.Subnet.from_subnet_id(self, "PrivateSubnet1b", private_subnet_1b)
    ]),
    security_groups=[ec2.SecurityGroup.from_security_group_id(self, "ECSSG", ecs_sg_id)]
)

# Attach to target group
service.attach_to_application_target_group(target_group)
```

**Estimated Lines**: ~30 lines Python

---

### 5. Auto-Scaling

**AWS Service**: `aws_cdk.aws_applicationautoscaling.ScalableTarget`

**CDK Implementation** (~20 lines):
```python
scaling = service.auto_scale_task_count(
    min_capacity=2,
    max_capacity=10
)

scaling.scale_on_cpu_utilization(
    "CpuScaling",
    target_utilization_percent=70,
    scale_in_cooldown=Duration.seconds(300),
    scale_out_cooldown=Duration.seconds(60)
)
```

**Estimated Lines**: ~20 lines Python

---

### 6. ECR Repository

**AWS Service**: `aws_cdk.aws_ecr.Repository`

**CDK Implementation** (~15 lines):
```python
ecr_repository = ecr.Repository(
    self, "Repository",
    repository_name="zero2prod",
    image_tag_mutability=ecr.TagMutability.IMMUTABLE,
    image_scan_on_push=True,
    lifecycle_rules=[
        ecr.LifecycleRule(
            description="Keep last 10 images",
            max_image_count=10
        )
    ]
)
```

**Estimated Lines**: ~15 lines Python

---

### 7. CloudWatch Log Group

**AWS Service**: `aws_cdk.aws_logs.LogGroup`

**CDK Implementation** (~10 lines):
```python
log_group = logs.LogGroup(
    self, "LogGroup",
    log_group_name="/ecs/zero2prod-web",
    retention=logs.RetentionDays.ONE_MONTH,
    removal_policy=RemovalPolicy.DESTROY
)
```

**Estimated Lines**: ~10 lines Python

---

### 8. Secrets Manager (HMAC Secret)

**AWS Service**: `aws_cdk.aws_secretsmanager.Secret`

**CDK Implementation** (~10 lines):
```python
hmac_secret = secretsmanager.Secret(
    self, "HmacSecret",
    secret_name="zero2prod/hmac/secret",
    generate_secret_string=secretsmanager.SecretStringGenerator(
        secret_string_template=json.dumps({}),
        generate_string_key="secret",
        exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/@\"\\"
    )
)
```

**Estimated Lines**: ~10 lines Python

---

### 9. CloudFormation Outputs

**CDK Implementation** (~20 lines):
```python
# ALB DNS name (for Route53 or CloudFront)
CfnOutput(self, "AlbDnsName",
    value=alb.load_balancer_dns_name,
    description="ALB DNS name",
    export_name="Zero2Prod-ALB-DNS-Name"
)

# ECS cluster name (for Unit 5 - Worker)
CfnOutput(self, "ClusterName",
    value=cluster.cluster_name,
    description="ECS cluster name",
    export_name="Zero2Prod-ECS-Cluster-Name"
)

# ECR repository URI (for GitHub Actions)
CfnOutput(self, "EcrRepositoryUri",
    value=ecr_repository.repository_uri,
    description="ECR repository URI",
    export_name="Zero2Prod-ECR-Repository-Uri"
)
```

**Estimated Lines**: ~20 lines Python

---

## Stack Dependencies

```python
class ComputeStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Import dependencies from previous units
        # Unit 1 (Network): VPC, subnets, security groups
        # Unit 2 (Database): Database secret ARN
        # Unit 3 (Cache): Cache secret ARN
```

**Dependencies Required**:
- `Zero2Prod-VPC-Id` (from NetworkStack)
- `Zero2Prod-PublicSubnet-1a-Id`, `Zero2Prod-PublicSubnet-1b-Id` (NetworkStack)
- `Zero2Prod-PrivateSubnet-1a-Id`, `Zero2Prod-PrivateSubnet-1b-Id` (NetworkStack)
- `Zero2Prod-ALB-SG-Id` (NetworkStack)
- `Zero2Prod-ECS-SG-Id` (NetworkStack)
- `Zero2Prod-Database-Secret-Arn` (DatabaseStack)
- `Zero2Prod-Cache-Secret-Arn` (CacheStack)

---

## Total CDK Code Estimate

| Component | Lines of Python |
|-----------|-----------------|
| ALB + Listeners + Target Group | ~80 |
| ECS Cluster | ~15 |
| Task Definition + IAM Roles | ~60 |
| ECS Service | ~30 |
| Auto-Scaling | ~20 |
| ECR Repository | ~15 |
| CloudWatch Log Group | ~10 |
| HMAC Secret | ~10 |
| CloudFormation Outputs | ~20 |
| **Total** | **~260 lines** |

---

## GitHub Actions Integration

**Workflow**: `.github/workflows/deploy-ecs.yml`

**Key Steps**:
1. Checkout code
2. Configure AWS credentials (OIDC role)
3. Login to ECR
4. Build Docker image
5. Tag image `sha-<git-hash>`
6. Push to ECR
7. Update task definition JSON (new image URI)
8. Register new task definition revision
9. Update ECS service (triggers rolling deployment)
10. Wait for service to reach steady state

**Estimated Lines**: ~100 lines YAML

---

## References

- Logical Components: `../nfr-design/logical-components.md`
- Domain Entities: `../functional-design/domain-entities.md`
- Technology Stack: `../nfr-requirements/technology-stack.md`
- NFR Patterns: `../nfr-design/nfr-patterns.md`
