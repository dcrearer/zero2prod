# Resource Specifications - Unit 1: Network Infrastructure

## Overview

This document provides detailed specifications for all AWS network resources, including CloudFormation resource types, CDK L2 constructs, naming conventions, tagging strategy, and complete configuration parameters.

**Scope**: Detailed specifications for VPC, subnets, security groups, VPC endpoints, route tables, and internet gateway.

**Related Documents**:
- CDK Stack Design: `cdk-stack-design.md` (sibling document)
- Functional Design: `/aidlc-docs/construction/unit-1-network/functional-design/domain-entities.md`
- NFR Design: `/aidlc-docs/construction/unit-1-network/nfr-design/`

---

## 1. VPC Resource

### 1.1 VPC Specification

**CloudFormation Resource Type**: `AWS::EC2::VPC`

**CDK L2 Construct**: `aws_cdk.aws_ec2.Vpc`

**Resource Configuration**:

```python
from aws_cdk import aws_ec2 as ec2

vpc = ec2.Vpc(
    self, "Vpc",
    cidr="10.0.0.0/16",
    max_azs=2,
    enable_dns_hostnames=True,
    enable_dns_support=True,
    subnet_configuration=[
        # Subnet configurations (see Subnet section)
    ],
    nat_gateways=0
)
```

**Property Specifications**:

| Property | Value | Required | Description | CloudFormation Property |
|----------|-------|----------|-------------|-------------------------|
| `cidr` | `10.0.0.0/16` | Yes | VPC CIDR block (65,536 IPs) | `CidrBlock` |
| `max_azs` | `2` | Yes | Deploy across 2 availability zones | N/A (CDK abstraction) |
| `enable_dns_hostnames` | `True` | Yes | Enable DNS hostnames (required for VPC endpoints) | `EnableDnsHostnames` |
| `enable_dns_support` | `True` | Yes | Enable DNS resolution | `EnableDnsSupport` |
| `nat_gateways` | `0` | Yes | No NAT Gateway (use VPC endpoints) | N/A (CDK abstraction) |

**Tags**:

| Key | Value | Purpose |
|-----|-------|---------|
| `Name` | `zero2prod-vpc` | Human-readable identifier |
| `Project` | `zero2prod` | Cost allocation |
| `Environment` | `production` | Environment identifier |
| `ManagedBy` | `CDK` | Infrastructure management |
| `Component` | `network` | Component category |

**CloudFormation Template (synthesized)**:

```yaml
VPC:
  Type: AWS::EC2::VPC
  Properties:
    CidrBlock: 10.0.0.0/16
    EnableDnsHostnames: true
    EnableDnsSupport: true
    Tags:
      - Key: Name
        Value: zero2prod-vpc
      - Key: Project
        Value: zero2prod
      - Key: Environment
        Value: production
      - Key: ManagedBy
        Value: CDK
      - Key: Component
        Value: network
```

---

## 2. Subnet Resources

### 2.1 Public Subnet 1 (AZ-A)

**CloudFormation Resource Type**: `AWS::EC2::Subnet`

**CDK L2 Construct**: `aws_cdk.aws_ec2.PublicSubnet` (created automatically by `Vpc` construct)

**Resource Configuration** (CDK automatically creates based on `subnet_configuration`):

```python
ec2.SubnetConfiguration(
    name="Public",
    subnet_type=ec2.SubnetType.PUBLIC,
    cidr_mask=24,
    map_public_ip_on_launch=True
)
```

**Property Specifications**:

| Property | Value | Required | Description | CloudFormation Property |
|----------|-------|----------|-------------|-------------------------|
| `cidr_block` | `10.0.1.0/24` | Yes | 256 IP addresses (251 usable) | `CidrBlock` |
| `availability_zone` | `us-east-1a` | Yes | Availability zone placement | `AvailabilityZone` |
| `map_public_ip_on_launch` | `True` | Yes | Auto-assign public IPs | `MapPublicIpOnLaunch` |
| `vpc_id` | `{VPC.VpcId}` | Yes | Parent VPC reference | `VpcId` |

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-public-1a` |
| `Type` | `Public` |
| `AZ` | `us-east-1a` |
| `aws-cdk:subnet-type` | `Public` |

---

### 2.2 Public Subnet 2 (AZ-B)

**Property Specifications**:

| Property | Value |
|----------|-------|
| `cidr_block` | `10.0.2.0/24` |
| `availability_zone` | `us-east-1b` |
| `map_public_ip_on_launch` | `True` |

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-public-1b` |
| `Type` | `Public` |
| `AZ` | `us-east-1b` |

---

### 2.3 Private Subnet 1 (AZ-A)

**CDK L2 Construct**: `aws_cdk.aws_ec2.PrivateSubnet`

**Resource Configuration**:

```python
ec2.SubnetConfiguration(
    name="Private",
    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,  # No NAT Gateway
    cidr_mask=24
)
```

**Property Specifications**:

| Property | Value | CloudFormation Property |
|----------|-------|-------------------------|
| `cidr_block` | `10.0.10.0/24` | `CidrBlock` |
| `availability_zone` | `us-east-1a` | `AvailabilityZone` |
| `map_public_ip_on_launch` | `False` | `MapPublicIpOnLaunch` |

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-private-1a` |
| `Type` | `Private` |
| `AZ` | `us-east-1a` |
| `aws-cdk:subnet-type` | `Isolated` |

---

### 2.4 Private Subnet 2 (AZ-B)

**Property Specifications**:

| Property | Value |
|----------|-------|
| `cidr_block` | `10.0.11.0/24` |
| `availability_zone` | `us-east-1b` |
| `map_public_ip_on_launch` | `False` |

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-private-1b` |
| `Type` | `Private` |
| `AZ` | `us-east-1b` |

---

### 2.5 Subnet CIDR Summary

| Subnet Name | CIDR Block | AZ | Type | Total IPs | Usable IPs | Resources |
|-------------|------------|----|----|-----------|------------|-----------|
| Public Subnet 1a | `10.0.1.0/24` | `us-east-1a` | Public | 256 | 251 | ALB nodes |
| Public Subnet 1b | `10.0.2.0/24` | `us-east-1b` | Public | 256 | 251 | ALB nodes |
| Private Subnet 1a | `10.0.10.0/24` | `us-east-1a` | Private | 256 | 251 | ECS, Lambda, Aurora, ElastiCache, VPC endpoints |
| Private Subnet 1b | `10.0.11.0/24` | `us-east-1b` | Private | 256 | 251 | ECS, Lambda, Aurora, ElastiCache, VPC endpoints |

**AWS Reserved IPs per Subnet** (5 per subnet):
- `x.x.x.0`: Network address
- `x.x.x.1`: VPC router
- `x.x.x.2`: DNS server
- `x.x.x.3`: Reserved for future use
- `x.x.x.255`: Network broadcast address

---

## 3. Security Group Resources

### 3.1 ALB Security Group

**CloudFormation Resource Type**: `AWS::EC2::SecurityGroup`

**CDK L2 Construct**: `aws_cdk.aws_ec2.SecurityGroup`

**Resource Configuration**:

```python
alb_sg = ec2.SecurityGroup(
    self, "AlbSecurityGroup",
    vpc=vpc,
    security_group_name="zero2prod-alb-sg",
    description="Security group for Application Load Balancer (public internet to ALB)",
    allow_all_outbound=False
)
```

**Property Specifications**:

| Property | Value | CloudFormation Property |
|----------|-------|-------------------------|
| `security_group_name` | `zero2prod-alb-sg` | `GroupName` |
| `description` | `Security group for Application Load Balancer` | `GroupDescription` |
| `vpc_id` | `{VPC.VpcId}` | `VpcId` |

**Ingress Rules**:

| Protocol | Port | Source | Description | CDK Code |
|----------|------|--------|-------------|----------|
| TCP | 443 | `0.0.0.0/0` | HTTPS from internet | `alb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "HTTPS from internet")` |
| TCP | 80 | `0.0.0.0/0` | HTTP redirect to HTTPS | `alb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP redirect to HTTPS")` |

**Egress Rules**:

| Protocol | Port | Destination | Description | CDK Code |
|----------|------|-------------|-------------|----------|
| TCP | 8000 | `{ECS-SG}` | Forward traffic to ECS tasks | `alb_sg.add_egress_rule(ec2.Peer.security_group_id(ecs_sg.security_group_id), ec2.Port.tcp(8000), "Forward traffic to ECS tasks")` |

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-alb-sg` |
| `Purpose` | `ALB internet-facing traffic` |

---

### 3.2 ECS Security Group

**Resource Configuration**:

```python
ecs_sg = ec2.SecurityGroup(
    self, "EcsSecurityGroup",
    vpc=vpc,
    security_group_name="zero2prod-ecs-sg",
    description="Security group for ECS Fargate tasks (web application)",
    allow_all_outbound=False
)
```

**Property Specifications**:

| Property | Value |
|----------|-------|
| `security_group_name` | `zero2prod-ecs-sg` |
| `description` | `Security group for ECS Fargate tasks` |

**Ingress Rules**:

| Protocol | Port | Source | Description |
|----------|------|--------|-------------|
| TCP | 8000 | `{ALB-SG}` | HTTP from ALB |

**Egress Rules**:

| Protocol | Port | Destination | Description |
|----------|------|-------------|-------------|
| TCP | 5432 | `{Aurora-SG}` | PostgreSQL to Aurora |
| TCP | 6379 | `{ElastiCache-SG}` | Redis to ElastiCache |
| TCP | 443 | `{VPC-Endpoint-SG}` | HTTPS to VPC endpoints |

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-ecs-sg` |
| `Purpose` | `ECS task traffic` |

---

### 3.3 Aurora Security Group

**Resource Configuration**:

```python
aurora_sg = ec2.SecurityGroup(
    self, "AuroraSecurityGroup",
    vpc=vpc,
    security_group_name="zero2prod-aurora-sg",
    description="Security group for Aurora PostgreSQL cluster",
    allow_all_outbound=False
)
```

**Property Specifications**:

| Property | Value |
|----------|-------|
| `security_group_name` | `zero2prod-aurora-sg` |
| `description` | `Security group for Aurora PostgreSQL cluster` |

**Ingress Rules**:

| Protocol | Port | Source | Description |
|----------|------|--------|-------------|
| TCP | 5432 | `{ECS-SG}` | PostgreSQL from ECS tasks |
| TCP | 5432 | `{Lambda-SG}` | PostgreSQL from Lambda function |

**Egress Rules**: NONE (no outbound connections)

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-aurora-sg` |
| `Purpose` | `Aurora database traffic` |

---

### 3.4 ElastiCache Security Group

**Resource Configuration**:

```python
elasticache_sg = ec2.SecurityGroup(
    self, "ElastiCacheSecurityGroup",
    vpc=vpc,
    security_group_name="zero2prod-elasticache-sg",
    description="Security group for ElastiCache Serverless Redis",
    allow_all_outbound=False
)
```

**Property Specifications**:

| Property | Value |
|----------|-------|
| `security_group_name` | `zero2prod-elasticache-sg` |
| `description` | `Security group for ElastiCache Serverless Redis` |

**Ingress Rules**:

| Protocol | Port | Source | Description |
|----------|------|--------|-------------|
| TCP | 6379 | `{ECS-SG}` | Redis from ECS tasks |

**Egress Rules**: NONE

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-elasticache-sg` |
| `Purpose` | `ElastiCache session cache traffic` |

---

### 3.5 Lambda Security Group

**Resource Configuration**:

```python
lambda_sg = ec2.SecurityGroup(
    self, "LambdaSecurityGroup",
    vpc=vpc,
    security_group_name="zero2prod-lambda-sg",
    description="Security group for Lambda email sender function",
    allow_all_outbound=False
)
```

**Property Specifications**:

| Property | Value |
|----------|-------|
| `security_group_name` | `zero2prod-lambda-sg` |
| `description` | `Security group for Lambda email sender function` |

**Ingress Rules**: NONE (event-driven, no network ingress)

**Egress Rules**:

| Protocol | Port | Destination | Description |
|----------|------|-------------|-------------|
| TCP | 5432 | `{Aurora-SG}` | PostgreSQL to Aurora |
| TCP | 443 | `{VPC-Endpoint-SG}` | HTTPS to VPC endpoints |

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-lambda-sg` |
| `Purpose` | `Lambda function traffic` |

---

### 3.6 VPC Endpoint Security Group

**Resource Configuration**:

```python
vpc_endpoint_sg = ec2.SecurityGroup(
    self, "VpcEndpointSecurityGroup",
    vpc=vpc,
    security_group_name="zero2prod-vpc-endpoints-sg",
    description="Security group for VPC interface endpoints",
    allow_all_outbound=False
)
```

**Property Specifications**:

| Property | Value |
|----------|-------|
| `security_group_name` | `zero2prod-vpc-endpoints-sg` |
| `description` | `Security group for VPC interface endpoints` |

**Ingress Rules**:

| Protocol | Port | Source | Description |
|----------|------|--------|-------------|
| TCP | 443 | `{ECS-SG}` | HTTPS from ECS tasks |
| TCP | 443 | `{Lambda-SG}` | HTTPS from Lambda function |

**Egress Rules**: NONE

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-vpc-endpoints-sg` |
| `Purpose` | `VPC endpoint traffic` |

---

### 3.7 Security Group Summary

| Security Group Name | Ingress Rules Count | Egress Rules Count | Assigned Resources |
|---------------------|---------------------|--------------------|--------------------|
| `zero2prod-alb-sg` | 2 | 1 | Application Load Balancer |
| `zero2prod-ecs-sg` | 1 | 3 | ECS Fargate tasks |
| `zero2prod-aurora-sg` | 2 | 0 | Aurora PostgreSQL cluster |
| `zero2prod-elasticache-sg` | 1 | 0 | ElastiCache Serverless Redis |
| `zero2prod-lambda-sg` | 0 | 2 | Lambda email sender function |
| `zero2prod-vpc-endpoints-sg` | 2 | 0 | VPC interface endpoints (7 ENIs × 2 AZs = 14 ENIs) |

---

## 4. VPC Endpoint Resources

### 4.1 S3 Gateway Endpoint

**CloudFormation Resource Type**: `AWS::EC2::VPCEndpoint`

**CDK L2 Construct**: `aws_cdk.aws_ec2.GatewayVpcEndpoint`

**Resource Configuration**:

```python
s3_gateway_endpoint = ec2.GatewayVpcEndpoint(
    self, "S3GatewayEndpoint",
    vpc=vpc,
    service=ec2.GatewayVpcEndpointAwsService.S3,
    subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)]
)
```

**Property Specifications**:

| Property | Value | CloudFormation Property |
|----------|-------|-------------------------|
| `service_name` | `com.amazonaws.us-east-1.s3` | `ServiceName` |
| `vpc_endpoint_type` | `Gateway` | `VpcEndpointType` |
| `vpc_id` | `{VPC.VpcId}` | `VpcId` |
| `route_table_ids` | `[{PrivateRouteTable.RouteTableId}]` | `RouteTableIds` |
| `policy_document` | `{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":"s3:*","Resource":"*"}]}` | `PolicyDocument` |

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-s3-gateway-endpoint` |
| `Service` | `s3` |

**Cost**: Free (no hourly charges, no per-GB charges)

---

### 4.2 ECR API Interface Endpoint

**CloudFormation Resource Type**: `AWS::EC2::VPCEndpoint`

**CDK L2 Construct**: `aws_cdk.aws_ec2.InterfaceVpcEndpoint`

**Resource Configuration**:

```python
ecr_api_endpoint = ec2.InterfaceVpcEndpoint(
    self, "EcrApiEndpoint",
    vpc=vpc,
    service=ec2.InterfaceVpcEndpointAwsService.ECR,
    subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
    security_groups=[vpc_endpoint_sg],
    private_dns_enabled=True
)
```

**Property Specifications**:

| Property | Value | CloudFormation Property |
|----------|-------|-------------------------|
| `service_name` | `com.amazonaws.us-east-1.ecr.api` | `ServiceName` |
| `vpc_endpoint_type` | `Interface` | `VpcEndpointType` |
| `vpc_id` | `{VPC.VpcId}` | `VpcId` |
| `subnet_ids` | `[{PrivateSubnet1a.SubnetId}, {PrivateSubnet1b.SubnetId}]` | `SubnetIds` |
| `security_group_ids` | `[{VpcEndpointSg.SecurityGroupId}]` | `SecurityGroupIds` |
| `private_dns_enabled` | `True` | `PrivateDnsEnabled` |

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-ecr-api-endpoint` |
| `Service` | `ecr-api` |

**Cost**: $7.20/month ($0.01/hour × 720 hours) + $0.01/GB data processed

---

### 4.3 ECR DKR Interface Endpoint

**Resource Configuration**:

```python
ecr_dkr_endpoint = ec2.InterfaceVpcEndpoint(
    self, "EcrDkrEndpoint",
    vpc=vpc,
    service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
    subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
    security_groups=[vpc_endpoint_sg],
    private_dns_enabled=True
)
```

**Property Specifications**:

| Property | Value |
|----------|-------|
| `service_name` | `com.amazonaws.us-east-1.ecr.dkr` |
| `vpc_endpoint_type` | `Interface` |
| `subnet_ids` | `[{PrivateSubnet1a}, {PrivateSubnet1b}]` |
| `private_dns_enabled` | `True` |

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-ecr-dkr-endpoint` |
| `Service` | `ecr-dkr` |

---

### 4.4 CloudWatch Logs Interface Endpoint

**Resource Configuration**:

```python
logs_endpoint = ec2.InterfaceVpcEndpoint(
    self, "LogsEndpoint",
    vpc=vpc,
    service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
    subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
    security_groups=[vpc_endpoint_sg],
    private_dns_enabled=True
)
```

**Property Specifications**:

| Property | Value |
|----------|-------|
| `service_name` | `com.amazonaws.us-east-1.logs` |
| `vpc_endpoint_type` | `Interface` |

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-logs-endpoint` |
| `Service` | `logs` |

---

### 4.5 Secrets Manager Interface Endpoint

**Resource Configuration**:

```python
secretsmanager_endpoint = ec2.InterfaceVpcEndpoint(
    self, "SecretsManagerEndpoint",
    vpc=vpc,
    service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
    subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
    security_groups=[vpc_endpoint_sg],
    private_dns_enabled=True
)
```

**Property Specifications**:

| Property | Value |
|----------|-------|
| `service_name` | `com.amazonaws.us-east-1.secretsmanager` |

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-secretsmanager-endpoint` |
| `Service` | `secretsmanager` |

---

### 4.6 STS Interface Endpoint

**Resource Configuration**:

```python
sts_endpoint = ec2.InterfaceVpcEndpoint(
    self, "StsEndpoint",
    vpc=vpc,
    service=ec2.InterfaceVpcEndpointAwsService.STS,
    subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
    security_groups=[vpc_endpoint_sg],
    private_dns_enabled=True
)
```

**Property Specifications**:

| Property | Value |
|----------|-------|
| `service_name` | `com.amazonaws.us-east-1.sts` |

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-sts-endpoint` |
| `Service` | `sts` |

---

### 4.7 SES Interface Endpoint

**Resource Configuration**:

```python
ses_endpoint = ec2.InterfaceVpcEndpoint(
    self, "SesEndpoint",
    vpc=vpc,
    service=ec2.InterfaceVpcEndpointAwsService.SES,
    subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
    security_groups=[vpc_endpoint_sg],
    private_dns_enabled=True
)
```

**Property Specifications**:

| Property | Value |
|----------|-------|
| `service_name` | `com.amazonaws.us-east-1.ses` |

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-ses-endpoint` |
| `Service` | `ses` |

---

### 4.8 SQS Interface Endpoint

**Resource Configuration**:

```python
sqs_endpoint = ec2.InterfaceVpcEndpoint(
    self, "SqsEndpoint",
    vpc=vpc,
    service=ec2.InterfaceVpcEndpointAwsService.SQS,
    subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
    security_groups=[vpc_endpoint_sg],
    private_dns_enabled=True
)
```

**Property Specifications**:

| Property | Value |
|----------|-------|
| `service_name` | `com.amazonaws.us-east-1.sqs` |

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-sqs-endpoint` |
| `Service` | `sqs` |

---

### 4.9 VPC Endpoint Summary

| Endpoint Name | Service | Type | Subnets | ENI Count | Cost/Month |
|---------------|---------|------|---------|-----------|------------|
| S3 Gateway | S3 | Gateway | Private route table | 0 | $0.00 |
| ECR API | ECR | Interface | Both private subnets | 2 | $7.20 |
| ECR DKR | ECR Docker | Interface | Both private subnets | 2 | $7.20 |
| CloudWatch Logs | Logs | Interface | Both private subnets | 2 | $7.20 |
| Secrets Manager | Secrets Manager | Interface | Both private subnets | 2 | $7.20 |
| STS | STS | Interface | Both private subnets | 2 | $7.20 |
| SES | SES | Interface | Both private subnets | 2 | $7.20 |
| SQS | SQS | Interface | Both private subnets | 2 | $7.20 |

**Total Interface Endpoint Cost**: $50.40/month (7 × $7.20)
**Total Data Processing Cost**: ~$0.50/month (estimated 50 GB × $0.01/GB)
**Total VPC Endpoint Cost**: ~$51/month

---

## 5. Route Table Resources

### 5.1 Public Route Table

**CloudFormation Resource Type**: `AWS::EC2::RouteTable`

**CDK L2 Construct**: `aws_cdk.aws_ec2.CfnRouteTable` (automatically created by Vpc construct)

**Resource Configuration** (CDK automatically creates):

```python
# Public route table created automatically by Vpc construct
# Manual creation would look like:
public_route_table = ec2.CfnRouteTable(
    self, "PublicRouteTable",
    vpc_id=vpc.vpc_id
)
```

**Property Specifications**:

| Property | Value | CloudFormation Property |
|----------|-------|-------------------------|
| `vpc_id` | `{VPC.VpcId}` | `VpcId` |

**Routes**:

| Destination | Target | Description | CloudFormation Resource |
|-------------|--------|-------------|-------------------------|
| `10.0.0.0/16` | `local` | VPC-internal traffic (AWS automatic) | N/A (automatic) |
| `0.0.0.0/0` | `{InternetGateway.InternetGatewayId}` | Default route to internet | `AWS::EC2::Route` |

**Associated Subnets**:
- Public Subnet 1a (`10.0.1.0/24`)
- Public Subnet 1b (`10.0.2.0/24`)

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-public-rtb` |
| `Type` | `Public` |

---

### 5.2 Private Route Table

**CloudFormation Resource Type**: `AWS::EC2::RouteTable`

**Resource Configuration** (CDK automatically creates):

```python
# Private route table created automatically by Vpc construct
```

**Property Specifications**:

| Property | Value |
|----------|-------|
| `vpc_id` | `{VPC.VpcId}` |

**Routes**:

| Destination | Target | Description |
|-------------|--------|-------------|
| `10.0.0.0/16` | `local` | VPC-internal traffic (AWS automatic) |
| S3 prefix list | `{S3GatewayEndpoint.VpcEndpointId}` | S3 traffic to gateway endpoint (AWS automatic when endpoint is created) |

**Important**: No default route (`0.0.0.0/0`) to Internet Gateway or NAT Gateway.

**Associated Subnets**:
- Private Subnet 1a (`10.0.10.0/24`)
- Private Subnet 1b (`10.0.11.0/24`)

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-private-rtb` |
| `Type` | `Private` |

---

## 6. Internet Gateway Resource

### 6.1 Internet Gateway

**CloudFormation Resource Type**: `AWS::EC2::InternetGateway`

**CDK L2 Construct**: `aws_cdk.aws_ec2.CfnInternetGateway` (automatically created by Vpc construct with `create_internet_gateway=True`)

**Resource Configuration** (CDK automatically creates):

```python
# Internet Gateway created automatically by Vpc construct
# Manual creation would look like:
igw = ec2.CfnInternetGateway(self, "InternetGateway")

# Attach to VPC
ec2.CfnVPCGatewayAttachment(
    self, "VpcGatewayAttachment",
    vpc_id=vpc.vpc_id,
    internet_gateway_id=igw.ref
)
```

**Property Specifications**:

| Property | Value | CloudFormation Property |
|----------|-------|-------------------------|
| `vpc_id` | `{VPC.VpcId}` | N/A (attachment property) |

**Tags**:

| Key | Value |
|-----|-------|
| `Name` | `zero2prod-igw` |

**Attachment**: Attached to VPC via `AWS::EC2::VPCGatewayAttachment`

**Used By**: Public route table (default route `0.0.0.0/0` → IGW)

---

## 7. Resource Naming Conventions

### 7.1 Naming Standards

**Pattern**: `zero2prod-<resource-type>-<identifier>`

**Examples**:

| Resource Type | Naming Pattern | Example |
|---------------|----------------|---------|
| VPC | `zero2prod-vpc` | `zero2prod-vpc` |
| Public Subnet | `zero2prod-public-<az>` | `zero2prod-public-1a` |
| Private Subnet | `zero2prod-private-<az>` | `zero2prod-private-1a` |
| Security Group | `zero2prod-<resource>-sg` | `zero2prod-alb-sg` |
| VPC Endpoint | `zero2prod-<service>-endpoint` | `zero2prod-s3-gateway-endpoint` |
| Route Table | `zero2prod-<type>-rtb` | `zero2prod-public-rtb` |
| Internet Gateway | `zero2prod-igw` | `zero2prod-igw` |

**Naming Rules**:
- Lowercase only (except tags)
- Hyphen-separated words
- Consistent prefix: `zero2prod-`
- Resource type suffix where appropriate (e.g., `-sg`, `-rtb`, `-endpoint`)

---

### 7.2 Tagging Strategy

**Required Tags** (all resources):

| Tag Key | Tag Value | Purpose |
|---------|-----------|---------|
| `Name` | Resource-specific name | Human-readable identifier |
| `Project` | `zero2prod` | Cost allocation |
| `Environment` | `production` or `staging` or `development` | Environment identifier |
| `ManagedBy` | `CDK` | Infrastructure management tool |
| `Component` | `network` | Component category |

**Optional Tags**:

| Tag Key | Example Value | Use Case |
|---------|---------------|----------|
| `CostCenter` | `network-infrastructure` | Detailed cost allocation |
| `Owner` | `network-team` | Ownership tracking |
| `Purpose` | `ALB internet-facing traffic` | Resource purpose (security groups) |
| `Type` | `Public` or `Private` | Subnet type |
| `AZ` | `us-east-1a` | Availability zone (subnets) |
| `Service` | `s3` or `ecr-api` | AWS service (VPC endpoints) |

**CDK Tagging** (apply tags to all resources in stack):

```python
from aws_cdk import Tags

# Apply tags to all resources in the stack
Tags.of(self).add("Project", "zero2prod")
Tags.of(self).add("Environment", "production")
Tags.of(self).add("ManagedBy", "CDK")
Tags.of(self).add("Component", "network")
```

---

## 8. CloudFormation Resource Count

### 8.1 Expected Resource Count

**Total CloudFormation Resources**: ~35 resources (varies based on CDK synthesis)

| Resource Type | Count | CloudFormation Resource Type |
|---------------|-------|------------------------------|
| VPC | 1 | `AWS::EC2::VPC` |
| Subnets | 4 | `AWS::EC2::Subnet` |
| Security Groups | 6 | `AWS::EC2::SecurityGroup` |
| Security Group Ingress | 8 | `AWS::EC2::SecurityGroupIngress` |
| Security Group Egress | 8 | `AWS::EC2::SecurityGroupEgress` |
| VPC Endpoints | 8 | `AWS::EC2::VPCEndpoint` |
| Route Tables | 2 | `AWS::EC2::RouteTable` |
| Routes | 2 | `AWS::EC2::Route` |
| Subnet Route Table Associations | 4 | `AWS::EC2::SubnetRouteTableAssociation` |
| Internet Gateway | 1 | `AWS::EC2::InternetGateway` |
| VPC Gateway Attachment | 1 | `AWS::EC2::VPCGatewayAttachment` |

**Note**: Actual count may vary based on CDK synthesis and implicit resources created by L2 constructs.

---

### 8.2 Resource Dependencies

**Dependency Order** (CloudFormation stack creation):

1. VPC
2. Internet Gateway, Subnets, Route Tables
3. VPC Gateway Attachment (attach IGW to VPC)
4. Routes (add routes to route tables)
5. Subnet Route Table Associations
6. Security Groups (without cross-references)
7. Security Group Rules (with cross-references)
8. VPC Endpoints (depend on VPC, subnets, security groups)

**CloudFormation DependsOn** (implicit, handled by CDK):

```yaml
# Example: VPC Endpoint depends on VPC, subnets, and security groups
VpcEndpoint:
  Type: AWS::EC2::VPCEndpoint
  DependsOn:
    - VPC
    - PrivateSubnet1a
    - PrivateSubnet1b
    - VpcEndpointSecurityGroup
```

---

## 9. Resource Limits and Quotas

### 9.1 AWS Service Limits

**VPC Limits** (per region):

| Resource | Default Limit | Current Usage | Headroom |
|----------|---------------|---------------|----------|
| VPCs per region | 5 | 1 | 4 |
| Subnets per VPC | 200 | 4 | 196 |
| Security groups per VPC | 500 | 6 | 494 |
| Rules per security group | 60 | 8 (max per SG) | 52 |
| VPC endpoints per VPC | 255 | 8 | 247 |
| Internet gateways per region | 5 | 1 | 4 |

**No Service Limit Increases Required**: All usage is well within default limits.

---

### 9.2 IP Address Limits

**VPC CIDR Limits**:

| Property | Value | Notes |
|----------|-------|-------|
| VPC CIDR block | `10.0.0.0/16` | 65,536 addresses |
| Minimum VPC CIDR | `/16` | AWS enforced minimum |
| Maximum VPC CIDR | `/28` | AWS enforced maximum (discouraged) |
| Secondary CIDR blocks | 4 (additional) | Can add more CIDR blocks if needed |

**Subnet CIDR Limits**:

| Property | Value |
|----------|-------|
| Minimum subnet CIDR | `/28` (16 addresses) |
| Current subnet CIDR | `/24` (256 addresses) |
| Usable IPs per subnet | 251 (AWS reserves 5) |

---

## 10. Cost Breakdown

### 10.1 Network Infrastructure Cost (Monthly)

**Fixed Costs**:

| Resource | Quantity | Unit Cost | Monthly Cost | Notes |
|----------|----------|-----------|--------------|-------|
| VPC | 1 | Free | $0.00 | No charge for VPC |
| Subnets | 4 | Free | $0.00 | No charge for subnets |
| Internet Gateway | 1 | Free | $0.00 | No hourly charge (data transfer charged separately) |
| Security Groups | 6 | Free | $0.00 | No charge for security groups |
| Route Tables | 2 | Free | $0.00 | No charge for route tables |
| S3 Gateway Endpoint | 1 | Free | $0.00 | No charge for gateway endpoints |
| Interface Endpoints (hourly) | 7 | $0.01/hour | $50.40 | 7 × $7.20/month |

**Variable Costs** (estimated):

| Resource | Volume | Unit Cost | Monthly Cost | Notes |
|----------|--------|-----------|--------------|-------|
| Interface Endpoints (data) | 50 GB | $0.01/GB | $0.50 | Estimated data transfer |
| Cross-AZ Data Transfer | 10 GB | $0.01/GB | $0.10 | Estimated cross-AZ traffic |
| Internet Data Transfer (Outbound) | 100 GB | $0.09/GB (first 10 TB) | $9.00 | ALB responses to internet |

**Total Network Cost**: ~$60/month

**Cost Optimization Opportunities**:
- Using S3 Gateway Endpoint (free) instead of S3 Interface Endpoint ($7.20/month): **Save $7.20/month**
- Using VPC endpoints ($51/month) instead of NAT Gateway ($66/month): **Save $15/month**

---

## 11. Summary

**Resource Overview**:
- **VPC**: 1 VPC with CIDR `10.0.0.0/16`
- **Subnets**: 4 subnets (2 public, 2 private) across 2 AZs
- **Security Groups**: 6 security groups with 16 total rules
- **VPC Endpoints**: 8 endpoints (1 Gateway, 7 Interface)
- **Route Tables**: 2 route tables (1 public, 1 private)
- **Internet Gateway**: 1 internet gateway

**Total CloudFormation Resources**: ~35 resources

**Total Monthly Cost**: ~$60 (primarily VPC endpoints and data transfer)

**Key Configuration Details**:
- No NAT Gateway (use VPC endpoints)
- Multi-AZ deployment (2 AZs)
- Private DNS enabled for interface endpoints
- Least-privilege security groups
- TLS 1.2+ encryption in transit

**Next Steps**: Proceed to Deployment Configuration document for CDK deployment instructions.

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-12  
**Status**: Ready for Implementation
