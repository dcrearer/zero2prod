# CDK Stack Design - Unit 1: Network Infrastructure

## Overview

This document defines the AWS CDK stack structure, construct hierarchy, and deployment architecture for the network infrastructure. It provides the blueprint for implementing the network foundation using CDK Python.

**Scope**: NetworkStack class structure, CDK constructs, cross-stack exports, and deployment organization.

**Related Documents**:
- Functional Design: `/aidlc-docs/construction/unit-1-network/functional-design/`
- NFR Design: `/aidlc-docs/construction/unit-1-network/nfr-design/`
- Resource Specifications: `resource-specifications.md` (sibling document)

---

## 1. Stack Architecture

### 1.1 Stack Overview

**Stack Name**: `NetworkStack`

**Purpose**: Foundation infrastructure stack that creates VPC, subnets, security groups, VPC endpoints, routing, and internet gateway. This stack is deployed first and exports network resource IDs for consumption by other stacks (compute, database, cache).

**Stack Type**: Foundation stack (no dependencies, exports resources for other stacks)

**CDK Stack Class**: `NetworkStack` (extends `aws_cdk.Stack`)

**Deployment Order**: 1 (deployed first, before all other stacks)

---

### 1.2 Stack Dependencies

**Incoming Dependencies**: None (foundation stack)

**Outgoing Dependencies**: Exports network resource IDs for consumption by:
- **ComputeStack** (Unit 4): ALB security group ID, ECS security group ID, public subnet IDs, private subnet IDs
- **DatabaseStack** (Unit 2): Aurora security group ID, private subnet IDs, VPC ID
- **CacheStack** (Unit 3): ElastiCache security group ID, private subnet IDs, VPC ID
- **LambdaStack** (Unit 5): Lambda security group ID, VPC endpoint security group ID, private subnet IDs, VPC ID

**Dependency Graph**:

```
NetworkStack (Unit 1)
    ↓ (exports VPC ID, subnet IDs, security group IDs)
    ├── ComputeStack (Unit 4: ALB, ECS)
    ├── DatabaseStack (Unit 2: Aurora)
    ├── CacheStack (Unit 3: ElastiCache)
    └── LambdaStack (Unit 5: Lambda function)
```

---

### 1.3 CloudFormation Stack Properties

**Stack Properties**:

```python
from aws_cdk import Stack, Environment

class NetworkStack(Stack):
    def __init__(self, scope, id: str, *, env: Environment, **kwargs):
        super().__init__(scope, id, env=env, **kwargs)
        
        # Stack properties
        self.stack_name = "Zero2ProdNetworkStack"
        self.description = "Network infrastructure for Zero2Prod application (VPC, subnets, security groups, VPC endpoints)"
        self.tags = {
            "Project": "zero2prod",
            "Environment": env.account,  # or pass explicitly
            "ManagedBy": "CDK",
            "Component": "network",
            "CostCenter": "network-infrastructure"
        }
```

**Environment Configuration**:

```python
# cdk/app.py
from aws_cdk import App, Environment
from network_stack import NetworkStack

app = App()

# Environment-specific configuration
env_us_east_1 = Environment(
    account="123456789012",  # AWS account ID (from context or env var)
    region="us-east-1"        # AWS region
)

# Instantiate NetworkStack
network_stack = NetworkStack(
    app,
    "NetworkStack",
    env=env_us_east_1,
    stack_name="Zero2ProdNetworkStack"
)

app.synth()
```

---

## 2. CDK Construct Hierarchy

### 2.1 Top-Level Construct Organization

**NetworkStack Construct Hierarchy**:

```
NetworkStack (Stack)
├── VPC (L2: aws_ec2.Vpc)
│   ├── Public Subnet 1a (L2: aws_ec2.PublicSubnet)
│   ├── Public Subnet 1b (L2: aws_ec2.PublicSubnet)
│   ├── Private Subnet 1a (L2: aws_ec2.PrivateSubnet)
│   ├── Private Subnet 1b (L2: aws_ec2.PrivateSubnet)
│   ├── Internet Gateway (L2: aws_ec2.CfnInternetGateway)
│   ├── Public Route Table (L2: aws_ec2.CfnRouteTable)
│   └── Private Route Table (L2: aws_ec2.CfnRouteTable)
├── Security Groups (L2: aws_ec2.SecurityGroup)
│   ├── ALB Security Group
│   ├── ECS Security Group
│   ├── Aurora Security Group
│   ├── ElastiCache Security Group
│   ├── Lambda Security Group
│   └── VPC Endpoint Security Group
└── VPC Endpoints
    ├── S3 Gateway Endpoint (L2: aws_ec2.GatewayVpcEndpoint)
    └── Interface Endpoints (L2: aws_ec2.InterfaceVpcEndpoint)
        ├── ECR API Endpoint
        ├── ECR DKR Endpoint
        ├── CloudWatch Logs Endpoint
        ├── Secrets Manager Endpoint
        ├── STS Endpoint
        ├── SES Endpoint
        └── SQS Endpoint
```

**Construct Levels Used**:
- **L2 (High-Level)**: Primary construct level (Vpc, SecurityGroup, InterfaceVpcEndpoint)
- **L1 (CfnXxx)**: Used sparingly for fine-grained control (route tables, route associations)

---

### 2.2 VPC Construct

**CDK Construct**: `aws_ec2.Vpc` (L2)

**Implementation**:

```python
from aws_cdk import aws_ec2 as ec2
from constructs import Construct

class NetworkStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # VPC
        self.vpc = ec2.Vpc(
            self, "Vpc",
            cidr="10.0.0.0/16",
            max_azs=2,  # Use 2 availability zones
            enable_dns_hostnames=True,
            enable_dns_support=True,
            
            # Subnet configuration
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,  # /24 subnets (256 addresses)
                    map_public_ip_on_launch=True
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,  # No NAT Gateway
                    cidr_mask=24  # /24 subnets (256 addresses)
                )
            ],
            
            # NAT Gateway: NONE (use VPC endpoints instead)
            nat_gateways=0,
            
            # Default behavior
            create_internet_gateway=True  # Internet gateway for public subnets
        )
        
        # Tag VPC
        self.vpc.node.apply_aspect(ec2.Tags.of(self.vpc).add("Name", "zero2prod-vpc"))
```

**Key Properties**:
- `cidr="10.0.0.0/16"`: VPC CIDR block (65,536 addresses)
- `max_azs=2`: Deploy across 2 availability zones
- `nat_gateways=0`: No NAT Gateway (use VPC endpoints)
- `subnet_configuration`: 2 public subnets + 2 private isolated subnets

**Subnet Type Explanation**:
- `SubnetType.PUBLIC`: Public subnet with Internet Gateway route
- `SubnetType.PRIVATE_ISOLATED`: Private subnet with NO NAT Gateway (VPC endpoints only)

---

### 2.3 Security Group Constructs

**CDK Construct**: `aws_ec2.SecurityGroup` (L2)

**Implementation Pattern** (example: ALB Security Group):

```python
# ALB Security Group
self.alb_sg = ec2.SecurityGroup(
    self, "AlbSecurityGroup",
    vpc=self.vpc,
    security_group_name="zero2prod-alb-sg",
    description="Security group for Application Load Balancer (public internet to ALB)",
    allow_all_outbound=False  # Explicit egress rules only
)

# Ingress: HTTPS from internet
self.alb_sg.add_ingress_rule(
    peer=ec2.Peer.any_ipv4(),
    connection=ec2.Port.tcp(443),
    description="HTTPS from internet"
)

# Ingress: HTTP from internet (redirect to HTTPS)
self.alb_sg.add_ingress_rule(
    peer=ec2.Peer.any_ipv4(),
    connection=ec2.Port.tcp(80),
    description="HTTP redirect to HTTPS"
)

# Egress: HTTP to ECS Security Group (added later after ECS SG is created)
# self.alb_sg.add_egress_rule(
#     peer=ec2.Peer.security_group_id(self.ecs_sg.security_group_id),
#     connection=ec2.Port.tcp(8000),
#     description="Forward traffic to ECS tasks"
# )
```

**Security Group Creation Order** (due to circular dependencies):

1. Create all security groups first (without cross-references)
2. Add security group rules with cross-references after all SGs are created

**Full Security Group List**:

```python
# 1. ALB Security Group
self.alb_sg = ec2.SecurityGroup(self, "AlbSecurityGroup", ...)

# 2. ECS Security Group
self.ecs_sg = ec2.SecurityGroup(self, "EcsSecurityGroup", ...)

# 3. Aurora Security Group
self.aurora_sg = ec2.SecurityGroup(self, "AuroraSecurityGroup", ...)

# 4. ElastiCache Security Group
self.elasticache_sg = ec2.SecurityGroup(self, "ElastiCacheSecurityGroup", ...)

# 5. Lambda Security Group
self.lambda_sg = ec2.SecurityGroup(self, "LambdaSecurityGroup", ...)

# 6. VPC Endpoint Security Group
self.vpc_endpoint_sg = ec2.SecurityGroup(self, "VpcEndpointSecurityGroup", ...)
```

**Security Group Rules** (added after all SGs are created):

See `resource-specifications.md` for complete ingress/egress rules.

---

### 2.4 VPC Endpoint Constructs

#### 2.4.1 S3 Gateway Endpoint

**CDK Construct**: `aws_ec2.GatewayVpcEndpoint` (L2)

**Implementation**:

```python
# S3 Gateway Endpoint
self.s3_gateway_endpoint = ec2.GatewayVpcEndpoint(
    self, "S3GatewayEndpoint",
    vpc=self.vpc,
    service=ec2.GatewayVpcEndpointAwsService.S3,
    
    # Attach to private route tables only
    subnets=[
        ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)
    ]
)

# Tag
ec2.Tags.of(self.s3_gateway_endpoint).add("Name", "zero2prod-s3-gateway-endpoint")
```

**Key Properties**:
- `service=GatewayVpcEndpointAwsService.S3`: S3 gateway endpoint
- `subnets`: Private subnets only (route table association)
- Cost: Free (no hourly charges)

---

#### 2.4.2 Interface Endpoints

**CDK Construct**: `aws_ec2.InterfaceVpcEndpoint` (L2)

**Implementation Pattern** (example: ECR API):

```python
# ECR API Interface Endpoint
self.ecr_api_endpoint = ec2.InterfaceVpcEndpoint(
    self, "EcrApiEndpoint",
    vpc=self.vpc,
    service=ec2.InterfaceVpcEndpointAwsService.ECR,
    
    # Deploy in BOTH private subnets (Multi-AZ)
    subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
    
    # Security group
    security_groups=[self.vpc_endpoint_sg],
    
    # Private DNS
    private_dns_enabled=True
)

# Tag
ec2.Tags.of(self.ecr_api_endpoint).add("Name", "zero2prod-ecr-api-endpoint")
```

**All Interface Endpoints**:

```python
# 1. ECR API
self.ecr_api_endpoint = ec2.InterfaceVpcEndpoint(
    self, "EcrApiEndpoint",
    vpc=self.vpc,
    service=ec2.InterfaceVpcEndpointAwsService.ECR,
    subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
    security_groups=[self.vpc_endpoint_sg],
    private_dns_enabled=True
)

# 2. ECR DKR
self.ecr_dkr_endpoint = ec2.InterfaceVpcEndpoint(
    self, "EcrDkrEndpoint",
    vpc=self.vpc,
    service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
    subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
    security_groups=[self.vpc_endpoint_sg],
    private_dns_enabled=True
)

# 3. CloudWatch Logs
self.logs_endpoint = ec2.InterfaceVpcEndpoint(
    self, "LogsEndpoint",
    vpc=self.vpc,
    service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
    subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
    security_groups=[self.vpc_endpoint_sg],
    private_dns_enabled=True
)

# 4. Secrets Manager
self.secretsmanager_endpoint = ec2.InterfaceVpcEndpoint(
    self, "SecretsManagerEndpoint",
    vpc=self.vpc,
    service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
    subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
    security_groups=[self.vpc_endpoint_sg],
    private_dns_enabled=True
)

# 5. STS
self.sts_endpoint = ec2.InterfaceVpcEndpoint(
    self, "StsEndpoint",
    vpc=self.vpc,
    service=ec2.InterfaceVpcEndpointAwsService.STS,
    subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
    security_groups=[self.vpc_endpoint_sg],
    private_dns_enabled=True
)

# 6. SES
self.ses_endpoint = ec2.InterfaceVpcEndpoint(
    self, "SesEndpoint",
    vpc=self.vpc,
    service=ec2.InterfaceVpcEndpointAwsService.SES,
    subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
    security_groups=[self.vpc_endpoint_sg],
    private_dns_enabled=True
)

# 7. SQS
self.sqs_endpoint = ec2.InterfaceVpcEndpoint(
    self, "SqsEndpoint",
    vpc=self.vpc,
    service=ec2.InterfaceVpcEndpointAwsService.SQS,
    subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
    security_groups=[self.vpc_endpoint_sg],
    private_dns_enabled=True
)
```

**Key Properties**:
- `subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)`: Deploy in BOTH private subnets (Multi-AZ)
- `security_groups=[self.vpc_endpoint_sg]`: VPC Endpoint Security Group
- `private_dns_enabled=True`: Enable private DNS resolution

---

## 3. Cross-Stack Exports

### 3.1 CloudFormation Exports

**Export Strategy**: Export network resource IDs using CloudFormation stack outputs for consumption by other stacks.

**Exported Resources**:

```python
from aws_cdk import CfnOutput

# VPC ID
CfnOutput(
    self, "VpcId",
    value=self.vpc.vpc_id,
    export_name="Zero2ProdVpcId",
    description="VPC ID for Zero2Prod application"
)

# Public Subnet IDs
CfnOutput(
    self, "PublicSubnetIds",
    value=",".join([subnet.subnet_id for subnet in self.vpc.public_subnets]),
    export_name="Zero2ProdPublicSubnetIds",
    description="Public subnet IDs (comma-separated)"
)

# Private Subnet IDs
CfnOutput(
    self, "PrivateSubnetIds",
    value=",".join([subnet.subnet_id for subnet in self.vpc.isolated_subnets]),
    export_name="Zero2ProdPrivateSubnetIds",
    description="Private subnet IDs (comma-separated)"
)

# ALB Security Group ID
CfnOutput(
    self, "AlbSecurityGroupId",
    value=self.alb_sg.security_group_id,
    export_name="Zero2ProdAlbSecurityGroupId",
    description="ALB security group ID"
)

# ECS Security Group ID
CfnOutput(
    self, "EcsSecurityGroupId",
    value=self.ecs_sg.security_group_id,
    export_name="Zero2ProdEcsSecurityGroupId",
    description="ECS security group ID"
)

# Aurora Security Group ID
CfnOutput(
    self, "AuroraSecurityGroupId",
    value=self.aurora_sg.security_group_id,
    export_name="Zero2ProdAuroraSecurityGroupId",
    description="Aurora security group ID"
)

# ElastiCache Security Group ID
CfnOutput(
    self, "ElastiCacheSecurityGroupId",
    value=self.elasticache_sg.security_group_id,
    export_name="Zero2ProdElastiCacheSecurityGroupId",
    description="ElastiCache security group ID"
)

# Lambda Security Group ID
CfnOutput(
    self, "LambdaSecurityGroupId",
    value=self.lambda_sg.security_group_id,
    export_name="Zero2ProdLambdaSecurityGroupId",
    description="Lambda security group ID"
)

# VPC Endpoint Security Group ID
CfnOutput(
    self, "VpcEndpointSecurityGroupId",
    value=self.vpc_endpoint_sg.security_group_id,
    export_name="Zero2ProdVpcEndpointSecurityGroupId",
    description="VPC Endpoint security group ID"
)
```

**Export Naming Convention**: `Zero2Prod<ResourceType><PropertyName>`

---

### 3.2 Consuming Exports in Other Stacks

**Example: DatabaseStack consumes NetworkStack exports**:

```python
from aws_cdk import Stack, Fn
from constructs import Construct

class DatabaseStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # Import VPC ID from NetworkStack
        vpc_id = Fn.import_value("Zero2ProdVpcId")
        
        # Import private subnet IDs
        private_subnet_ids = Fn.import_value("Zero2ProdPrivateSubnetIds").split(",")
        
        # Import Aurora security group ID
        aurora_sg_id = Fn.import_value("Zero2ProdAuroraSecurityGroupId")
        
        # Use imported values to create Aurora cluster
        # aurora_cluster = rds.DatabaseCluster(
        #     self, "AuroraCluster",
        #     vpc=ec2.Vpc.from_lookup(self, "Vpc", vpc_id=vpc_id),
        #     subnet_group=rds.SubnetGroup(self, "SubnetGroup", subnets=private_subnet_ids),
        #     security_groups=[ec2.SecurityGroup.from_security_group_id(self, "AuroraSg", aurora_sg_id)],
        #     ...
        # )
```

**Alternative: Direct Stack References** (if stacks are in same CDK app):

```python
from aws_cdk import App
from network_stack import NetworkStack
from database_stack import DatabaseStack

app = App()

# Create NetworkStack
network_stack = NetworkStack(app, "NetworkStack")

# Pass NetworkStack reference to DatabaseStack
database_stack = DatabaseStack(
    app, "DatabaseStack",
    vpc=network_stack.vpc,
    aurora_sg=network_stack.aurora_sg,
    private_subnets=network_stack.vpc.isolated_subnets
)

app.synth()
```

**Recommendation**: Use CloudFormation exports for maximum flexibility (allows stacks to be deployed independently).

---

## 4. CDK App Structure

### 4.1 Directory Structure

```
zero2prod/
├── cdk/
│   ├── app.py                       # CDK app entry point
│   ├── cdk.json                     # CDK configuration
│   ├── cdk.context.json             # CDK context (generated)
│   ├── requirements.txt             # Python dependencies
│   ├── stacks/
│   │   ├── __init__.py
│   │   ├── network_stack.py         # NetworkStack class
│   │   ├── database_stack.py        # DatabaseStack class (Unit 2)
│   │   ├── cache_stack.py           # CacheStack class (Unit 3)
│   │   ├── compute_stack.py         # ComputeStack class (Unit 4)
│   │   └── lambda_stack.py          # LambdaStack class (Unit 5)
│   ├── constructs/                  # Custom constructs (optional)
│   │   ├── __init__.py
│   │   └── secure_vpc_endpoint.py   # Custom VPC endpoint construct
│   └── tests/
│       ├── __init__.py
│       ├── unit/
│       │   ├── test_network_stack.py
│       │   └── test_security_groups.py
│       └── integration/
│           └── test_vpc_endpoints.py
└── aidlc-docs/
    └── construction/
        └── unit-1-network/
            └── infrastructure-design/
                └── cdk-stack-design.md (this file)
```

---

### 4.2 CDK App Entry Point

**File**: `cdk/app.py`

```python
#!/usr/bin/env python3
import os
from aws_cdk import App, Environment
from stacks.network_stack import NetworkStack

# Get environment configuration from context or environment variables
account = os.environ.get("CDK_DEFAULT_ACCOUNT", "123456789012")
region = os.environ.get("CDK_DEFAULT_REGION", "us-east-1")

app = App()

# Define AWS environment
env = Environment(account=account, region=region)

# Create NetworkStack
network_stack = NetworkStack(
    app,
    "NetworkStack",
    env=env,
    stack_name="Zero2ProdNetworkStack",
    description="Network infrastructure for Zero2Prod application"
)

# Add tags to all resources in the stack
app.node.apply_aspect(Tags.of(app).add("Project", "zero2prod"))
app.node.apply_aspect(Tags.of(app).add("ManagedBy", "CDK"))

app.synth()
```

---

### 4.3 CDK Configuration

**File**: `cdk/cdk.json`

```json
{
  "app": "python3 app.py",
  "watch": {
    "include": ["**"],
    "exclude": [
      "README.md",
      "cdk*.json",
      "requirements*.txt",
      "source.bat",
      "**/__init__.py",
      "**/__pycache__",
      "**/pytest_cache",
      "tests"
    ]
  },
  "context": {
    "@aws-cdk/aws-apigateway:usagePlanKeyOrderInsensitiveId": true,
    "@aws-cdk/core:stackRelativeExports": true,
    "@aws-cdk/aws-rds:lowercaseDbIdentifier": true,
    "@aws-cdk/aws-lambda:recognizeVersionProps": true,
    "@aws-cdk/aws-cloudfront:defaultSecurityPolicyTLSv1.2_2021": true,
    
    "availability-zones:account=123456789012:region=us-east-1": [
      "us-east-1a",
      "us-east-1b"
    ]
  }
}
```

**Key Configuration**:
- `app`: Python entry point
- `context`: CDK feature flags and environment-specific configuration
- `availability-zones`: Explicit AZ configuration (optional, CDK can auto-detect)

---

### 4.4 Python Dependencies

**File**: `cdk/requirements.txt`

```
aws-cdk-lib==2.100.0
constructs>=10.0.0,<11.0.0
boto3>=1.28.0
pytest>=7.4.0
pytest-cov>=4.1.0
```

**Installation**:

```bash
cd cdk
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 5. NetworkStack Implementation

### 5.1 Complete NetworkStack Class

**File**: `cdk/stacks/network_stack.py`

```python
from aws_cdk import (
    Stack,
    CfnOutput,
    Tags,
    aws_ec2 as ec2
)
from constructs import Construct


class NetworkStack(Stack):
    """
    Network infrastructure stack for Zero2Prod application.
    
    Creates:
    - VPC with 2 public and 2 private subnets across 2 AZs
    - 6 security groups (ALB, ECS, Aurora, ElastiCache, Lambda, VPC Endpoints)
    - 8 VPC endpoints (1 Gateway, 7 Interface)
    - Internet Gateway and route tables
    """
    
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # Create VPC
        self._create_vpc()
        
        # Create security groups
        self._create_security_groups()
        
        # Add security group rules (after all SGs are created)
        self._configure_security_group_rules()
        
        # Create VPC endpoints
        self._create_vpc_endpoints()
        
        # Create CloudFormation exports
        self._create_outputs()
    
    def _create_vpc(self) -> None:
        """Create VPC with public and private subnets."""
        self.vpc = ec2.Vpc(
            self, "Vpc",
            cidr="10.0.0.0/16",
            max_azs=2,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                    map_public_ip_on_launch=True
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ],
            nat_gateways=0
        )
        
        Tags.of(self.vpc).add("Name", "zero2prod-vpc")
    
    def _create_security_groups(self) -> None:
        """Create all security groups (without cross-references)."""
        
        # ALB Security Group
        self.alb_sg = ec2.SecurityGroup(
            self, "AlbSecurityGroup",
            vpc=self.vpc,
            security_group_name="zero2prod-alb-sg",
            description="Security group for Application Load Balancer",
            allow_all_outbound=False
        )
        
        # ECS Security Group
        self.ecs_sg = ec2.SecurityGroup(
            self, "EcsSecurityGroup",
            vpc=self.vpc,
            security_group_name="zero2prod-ecs-sg",
            description="Security group for ECS Fargate tasks",
            allow_all_outbound=False
        )
        
        # Aurora Security Group
        self.aurora_sg = ec2.SecurityGroup(
            self, "AuroraSecurityGroup",
            vpc=self.vpc,
            security_group_name="zero2prod-aurora-sg",
            description="Security group for Aurora PostgreSQL cluster",
            allow_all_outbound=False
        )
        
        # ElastiCache Security Group
        self.elasticache_sg = ec2.SecurityGroup(
            self, "ElastiCacheSecurityGroup",
            vpc=self.vpc,
            security_group_name="zero2prod-elasticache-sg",
            description="Security group for ElastiCache Serverless Redis",
            allow_all_outbound=False
        )
        
        # Lambda Security Group
        self.lambda_sg = ec2.SecurityGroup(
            self, "LambdaSecurityGroup",
            vpc=self.vpc,
            security_group_name="zero2prod-lambda-sg",
            description="Security group for Lambda email sender function",
            allow_all_outbound=False
        )
        
        # VPC Endpoint Security Group
        self.vpc_endpoint_sg = ec2.SecurityGroup(
            self, "VpcEndpointSecurityGroup",
            vpc=self.vpc,
            security_group_name="zero2prod-vpc-endpoints-sg",
            description="Security group for VPC interface endpoints",
            allow_all_outbound=False
        )
    
    def _configure_security_group_rules(self) -> None:
        """Add security group rules with cross-references."""
        
        # ALB Security Group Rules
        self.alb_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="HTTPS from internet"
        )
        self.alb_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="HTTP redirect to HTTPS"
        )
        self.alb_sg.add_egress_rule(
            peer=ec2.Peer.security_group_id(self.ecs_sg.security_group_id),
            connection=ec2.Port.tcp(8000),
            description="Forward traffic to ECS tasks"
        )
        
        # ECS Security Group Rules
        self.ecs_sg.add_ingress_rule(
            peer=ec2.Peer.security_group_id(self.alb_sg.security_group_id),
            connection=ec2.Port.tcp(8000),
            description="HTTP from ALB"
        )
        self.ecs_sg.add_egress_rule(
            peer=ec2.Peer.security_group_id(self.aurora_sg.security_group_id),
            connection=ec2.Port.tcp(5432),
            description="PostgreSQL to Aurora"
        )
        self.ecs_sg.add_egress_rule(
            peer=ec2.Peer.security_group_id(self.elasticache_sg.security_group_id),
            connection=ec2.Port.tcp(6379),
            description="Redis to ElastiCache"
        )
        self.ecs_sg.add_egress_rule(
            peer=ec2.Peer.security_group_id(self.vpc_endpoint_sg.security_group_id),
            connection=ec2.Port.tcp(443),
            description="HTTPS to VPC endpoints"
        )
        
        # Aurora Security Group Rules
        self.aurora_sg.add_ingress_rule(
            peer=ec2.Peer.security_group_id(self.ecs_sg.security_group_id),
            connection=ec2.Port.tcp(5432),
            description="PostgreSQL from ECS tasks"
        )
        self.aurora_sg.add_ingress_rule(
            peer=ec2.Peer.security_group_id(self.lambda_sg.security_group_id),
            connection=ec2.Port.tcp(5432),
            description="PostgreSQL from Lambda function"
        )
        
        # ElastiCache Security Group Rules
        self.elasticache_sg.add_ingress_rule(
            peer=ec2.Peer.security_group_id(self.ecs_sg.security_group_id),
            connection=ec2.Port.tcp(6379),
            description="Redis from ECS tasks"
        )
        
        # Lambda Security Group Rules
        self.lambda_sg.add_egress_rule(
            peer=ec2.Peer.security_group_id(self.aurora_sg.security_group_id),
            connection=ec2.Port.tcp(5432),
            description="PostgreSQL to Aurora"
        )
        self.lambda_sg.add_egress_rule(
            peer=ec2.Peer.security_group_id(self.vpc_endpoint_sg.security_group_id),
            connection=ec2.Port.tcp(443),
            description="HTTPS to VPC endpoints"
        )
        
        # VPC Endpoint Security Group Rules
        self.vpc_endpoint_sg.add_ingress_rule(
            peer=ec2.Peer.security_group_id(self.ecs_sg.security_group_id),
            connection=ec2.Port.tcp(443),
            description="HTTPS from ECS tasks"
        )
        self.vpc_endpoint_sg.add_ingress_rule(
            peer=ec2.Peer.security_group_id(self.lambda_sg.security_group_id),
            connection=ec2.Port.tcp(443),
            description="HTTPS from Lambda function"
        )
    
    def _create_vpc_endpoints(self) -> None:
        """Create VPC endpoints for AWS services."""
        
        # S3 Gateway Endpoint
        self.s3_gateway_endpoint = ec2.GatewayVpcEndpoint(
            self, "S3GatewayEndpoint",
            vpc=self.vpc,
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)]
        )
        Tags.of(self.s3_gateway_endpoint).add("Name", "zero2prod-s3-gateway-endpoint")
        
        # Interface Endpoints
        interface_endpoints = [
            ("EcrApiEndpoint", ec2.InterfaceVpcEndpointAwsService.ECR, "ecr-api"),
            ("EcrDkrEndpoint", ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER, "ecr-dkr"),
            ("LogsEndpoint", ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS, "logs"),
            ("SecretsManagerEndpoint", ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER, "secretsmanager"),
            ("StsEndpoint", ec2.InterfaceVpcEndpointAwsService.STS, "sts"),
            ("SesEndpoint", ec2.InterfaceVpcEndpointAwsService.SES, "ses"),
            ("SqsEndpoint", ec2.InterfaceVpcEndpointAwsService.SQS, "sqs")
        ]
        
        for endpoint_id, service, tag_name in interface_endpoints:
            endpoint = ec2.InterfaceVpcEndpoint(
                self, endpoint_id,
                vpc=self.vpc,
                service=service,
                subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
                security_groups=[self.vpc_endpoint_sg],
                private_dns_enabled=True
            )
            Tags.of(endpoint).add("Name", f"zero2prod-{tag_name}-endpoint")
    
    def _create_outputs(self) -> None:
        """Create CloudFormation stack outputs."""
        
        CfnOutput(self, "VpcId", value=self.vpc.vpc_id, export_name="Zero2ProdVpcId")
        
        CfnOutput(
            self, "PublicSubnetIds",
            value=",".join([subnet.subnet_id for subnet in self.vpc.public_subnets]),
            export_name="Zero2ProdPublicSubnetIds"
        )
        
        CfnOutput(
            self, "PrivateSubnetIds",
            value=",".join([subnet.subnet_id for subnet in self.vpc.isolated_subnets]),
            export_name="Zero2ProdPrivateSubnetIds"
        )
        
        CfnOutput(
            self, "AlbSecurityGroupId",
            value=self.alb_sg.security_group_id,
            export_name="Zero2ProdAlbSecurityGroupId"
        )
        
        CfnOutput(
            self, "EcsSecurityGroupId",
            value=self.ecs_sg.security_group_id,
            export_name="Zero2ProdEcsSecurityGroupId"
        )
        
        CfnOutput(
            self, "AuroraSecurityGroupId",
            value=self.aurora_sg.security_group_id,
            export_name="Zero2ProdAuroraSecurityGroupId"
        )
        
        CfnOutput(
            self, "ElastiCacheSecurityGroupId",
            value=self.elasticache_sg.security_group_id,
            export_name="Zero2ProdElastiCacheSecurityGroupId"
        )
        
        CfnOutput(
            self, "LambdaSecurityGroupId",
            value=self.lambda_sg.security_group_id,
            export_name="Zero2ProdLambdaSecurityGroupId"
        )
        
        CfnOutput(
            self, "VpcEndpointSecurityGroupId",
            value=self.vpc_endpoint_sg.security_group_id,
            export_name="Zero2ProdVpcEndpointSecurityGroupId"
        )
```

---

## 6. Deployment Commands

### 6.1 CDK Bootstrap

**Purpose**: One-time setup to prepare AWS environment for CDK deployments.

```bash
# Bootstrap AWS environment (one-time per account/region)
cdk bootstrap aws://123456789012/us-east-1

# Output: Creates CDKToolkit stack with S3 bucket and IAM roles
```

**When to Run**: Once per AWS account/region before first CDK deployment.

---

### 6.2 CDK Synthesis

**Purpose**: Generate CloudFormation template from CDK code.

```bash
# Synthesize CloudFormation template
cdk synth NetworkStack

# Output: cdk.out/NetworkStack.template.json
```

**Verification**: Review generated CloudFormation template for correctness.

---

### 6.3 CDK Diff

**Purpose**: Preview infrastructure changes before deployment.

```bash
# Show differences between deployed stack and code
cdk diff NetworkStack

# Output: Shows resources to be added, modified, or deleted
```

**Use Case**: Run before `cdk deploy` to verify changes.

---

### 6.4 CDK Deploy

**Purpose**: Deploy NetworkStack to AWS.

```bash
# Deploy NetworkStack
cdk deploy NetworkStack

# With approval prompt
cdk deploy NetworkStack --require-approval broadening

# Without approval (CI/CD)
cdk deploy NetworkStack --require-approval never
```

**Expected Output**: CloudFormation stack creation with resource IDs.

---

### 6.5 CDK Destroy

**Purpose**: Delete NetworkStack (use with caution).

```bash
# Destroy NetworkStack
cdk destroy NetworkStack

# Output: Deletes all resources in stack
```

**Warning**: Cannot destroy NetworkStack if other stacks depend on its exports.

---

## 7. Stack Deployment Order

### 7.1 Deployment Sequence

**Deployment Order**:

1. **NetworkStack** (Unit 1): Deploy first (no dependencies)
2. **DatabaseStack** (Unit 2): Deploy after NetworkStack (depends on VPC, subnets, Aurora SG)
3. **CacheStack** (Unit 3): Deploy after NetworkStack (depends on VPC, subnets, ElastiCache SG)
4. **LambdaStack** (Unit 5): Deploy after DatabaseStack (depends on Aurora cluster, VPC, Lambda SG)
5. **ComputeStack** (Unit 4): Deploy last (depends on DatabaseStack, CacheStack, ALB SG, ECS SG)

**Deployment Commands** (sequential):

```bash
# 1. Deploy NetworkStack
cdk deploy NetworkStack

# 2. Deploy DatabaseStack (after NetworkStack completes)
cdk deploy DatabaseStack

# 3. Deploy CacheStack (after NetworkStack completes)
cdk deploy CacheStack

# 4. Deploy LambdaStack (after DatabaseStack completes)
cdk deploy LambdaStack

# 5. Deploy ComputeStack (after DatabaseStack and CacheStack complete)
cdk deploy ComputeStack
```

**Parallel Deployment** (where possible):

```bash
# Deploy NetworkStack first
cdk deploy NetworkStack

# Deploy DatabaseStack and CacheStack in parallel (both depend on NetworkStack only)
cdk deploy DatabaseStack &
cdk deploy CacheStack &
wait

# Deploy LambdaStack (depends on DatabaseStack)
cdk deploy LambdaStack

# Deploy ComputeStack (depends on DatabaseStack and CacheStack)
cdk deploy ComputeStack
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Purpose**: Test CDK constructs generate correct CloudFormation resources.

**Example Unit Test** (`tests/unit/test_network_stack.py`):

```python
import aws_cdk as cdk
from aws_cdk.assertions import Template, Match
from stacks.network_stack import NetworkStack


def test_vpc_created():
    """Test VPC is created with correct CIDR."""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    # Assert VPC is created
    template.resource_count_is("AWS::EC2::VPC", 1)
    
    # Assert VPC CIDR is correct
    template.has_resource_properties("AWS::EC2::VPC", {
        "CidrBlock": "10.0.0.0/16",
        "EnableDnsHostnames": True,
        "EnableDnsSupport": True
    })


def test_subnets_created():
    """Test 4 subnets are created (2 public, 2 private)."""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    # Assert 4 subnets are created
    template.resource_count_is("AWS::EC2::Subnet", 4)


def test_security_groups_created():
    """Test 6 security groups are created."""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    # Assert 6 security groups are created
    template.resource_count_is("AWS::EC2::SecurityGroup", 6)


def test_vpc_endpoints_created():
    """Test 8 VPC endpoints are created (1 Gateway, 7 Interface)."""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    # Assert 1 Gateway endpoint (S3)
    template.resource_count_is("AWS::EC2::VPCEndpoint", 8)
    
    # Assert Gateway endpoint has correct service name
    template.has_resource_properties("AWS::EC2::VPCEndpoint", {
        "ServiceName": Match.string_like_regexp(r".*s3.*"),
        "VpcEndpointType": "Gateway"
    })
```

**Run Unit Tests**:

```bash
cd cdk
pytest tests/unit/
```

---

### 8.2 Snapshot Tests

**Purpose**: Detect unintended CloudFormation template changes.

**Example Snapshot Test**:

```python
import aws_cdk as cdk
from aws_cdk.assertions import Template
from stacks.network_stack import NetworkStack


def test_network_stack_snapshot():
    """Generate CloudFormation template snapshot."""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    # Save template as snapshot (run once to create baseline)
    # template.to_json() == expected_template.json
    
    # On subsequent runs, compare with snapshot
    assert template.to_json() == expected_snapshot
```

**Workflow**:
1. Generate baseline snapshot: Run test and save output
2. On subsequent runs: Compare generated template with baseline
3. If template changes unexpectedly: Test fails, requires explicit snapshot update

---

### 8.3 Integration Tests

**Purpose**: Verify deployed infrastructure is functional.

**Example Integration Test** (`tests/integration/test_vpc_endpoints.py`):

```python
import boto3
import pytest


@pytest.fixture(scope="module")
def ec2_client():
    """Create EC2 client."""
    return boto3.client('ec2', region_name='us-east-1')


def test_vpc_exists(ec2_client):
    """Test VPC is created with correct CIDR."""
    vpcs = ec2_client.describe_vpcs(
        Filters=[{'Name': 'tag:Name', 'Values': ['zero2prod-vpc']}]
    )
    
    assert len(vpcs['Vpcs']) == 1
    assert vpcs['Vpcs'][0]['CidrBlock'] == '10.0.0.0/16'


def test_vpc_endpoints_exist(ec2_client):
    """Test 8 VPC endpoints are created."""
    endpoints = ec2_client.describe_vpc_endpoints()
    
    # Filter endpoints for zero2prod VPC
    vpc_response = ec2_client.describe_vpcs(
        Filters=[{'Name': 'tag:Name', 'Values': ['zero2prod-vpc']}]
    )
    vpc_id = vpc_response['Vpcs'][0]['VpcId']
    
    zero2prod_endpoints = [
        e for e in endpoints['VpcEndpoints'] if e['VpcId'] == vpc_id
    ]
    
    assert len(zero2prod_endpoints) == 8


def test_private_dns_enabled(ec2_client):
    """Test interface endpoints have private DNS enabled."""
    endpoints = ec2_client.describe_vpc_endpoints()
    
    interface_endpoints = [
        e for e in endpoints['VpcEndpoints']
        if e['VpcEndpointType'] == 'Interface'
    ]
    
    for endpoint in interface_endpoints:
        assert endpoint['PrivateDnsEnabled'] == True
```

**Run Integration Tests** (after deployment):

```bash
cd cdk
pytest tests/integration/
```

---

## 9. Summary

**NetworkStack Overview**:
- **Purpose**: Foundation infrastructure for Zero2Prod application
- **Resources**: VPC, 4 subnets, 6 security groups, 8 VPC endpoints, internet gateway, route tables
- **Dependencies**: None (deployed first)
- **Exports**: VPC ID, subnet IDs, security group IDs (for other stacks)
- **Deployment Order**: 1 (before all other stacks)

**Key Implementation Details**:
- CDK L2 constructs for high-level abstraction
- Security groups created first, then rules added (avoid circular dependencies)
- Interface endpoints deployed in BOTH private subnets (Multi-AZ)
- CloudFormation exports for cross-stack references

**Testing Strategy**:
- Unit tests: Verify CloudFormation template correctness
- Snapshot tests: Detect unintended template changes
- Integration tests: Verify deployed infrastructure functionality

**Next Steps**: Proceed to Code Generation stage to implement NetworkStack.

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-12  
**Status**: Ready for Implementation
