# Domain Entities - Unit 1: Network Infrastructure

## Overview

This document defines the domain entities (data structures) that represent the network infrastructure. Each entity is described with its attributes, relationships, constraints, and lifecycle.

**Scope**: Entities represent the logical WHAT (data model), not HOW they are implemented (deferred to Infrastructure Design using AWS CDK constructs).

---

## Entity Relationship Diagram

```
VPC (1)
 ├── owns (1:N) → Subnet
 ├── owns (1:N) → SecurityGroup
 ├── owns (1:N) → VPCEndpoint
 ├── owns (1) → InternetGateway
 └── owns (1:N) → RouteTable

Subnet (4)
 ├── associated_with (N:1) → RouteTable
 ├── placed_in (N:1) → AvailabilityZone
 └── type: Public | Private

SecurityGroup (6)
 ├── has (1:N) → IngressRule
 ├── has (1:N) → EgressRule
 └── assigned_to → Resource (ALB, ECS, Aurora, ElastiCache, Lambda, VPC Endpoints)

VPCEndpoint (8)
 ├── type: Gateway | Interface
 ├── placed_in (N:N) → Subnet (interface endpoints only)
 └── uses (N:1) → SecurityGroup (interface endpoints only)

RouteTable (2)
 ├── has (1:N) → Route
 └── associated_with (1:N) → Subnet

InternetGateway (1)
 └── attached_to (1:1) → VPC

AvailabilityZone (2)
 └── contains (1:N) → Subnet
```

---

## Core Entities

### 1. VPC Entity

**Definition**: The top-level network container that provides isolated network environment for all AWS resources.

**Attributes**:

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `vpc_id` | String | Yes | AWS-generated VPC identifier | Format: `vpc-xxxxxxxx` |
| `cidr_block` | String | Yes | IP address range for VPC | Must be RFC 1918 private address, `/16` minimum |
| `enable_dns_hostnames` | Boolean | Yes | Enable DNS hostnames for resources | Must be `true` |
| `enable_dns_support` | Boolean | Yes | Enable DNS resolution | Must be `true` |
| `tags` | Map<String, String> | Yes | Resource tags for identification | Must include `Name`, `Project`, `Environment` |

**Constraints**:
- `cidr_block` MUST be `10.0.0.0/16` (per BR-1.1)
- `enable_dns_hostnames` MUST be `true` (required for VPC endpoints private DNS)
- `enable_dns_support` MUST be `true` (required for DNS resolution)

**Lifecycle**:
1. Created first (no dependencies)
2. Destroyed last (all dependent resources must be deleted first)

**Relationships**:
- **Owns**: Subnets (4), SecurityGroups (6), VPCEndpoints (8), InternetGateway (1), RouteTables (2)

**Example**:
```yaml
VPC:
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  cidr_block: "10.0.0.0/16"
  enable_dns_hostnames: true
  enable_dns_support: true
  tags:
    Name: "zero2prod-vpc"
    Project: "zero2prod"
    Environment: "production"
```

**Mapped Business Rules**: BR-1.1 (VPC CIDR Block)

---

### 2. Subnet Entity

**Definition**: A subdivision of VPC IP address space, placed in a specific availability zone, with a specific routing configuration (public or private).

**Attributes**:

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `subnet_id` | String | Yes | AWS-generated subnet identifier | Format: `subnet-xxxxxxxx` |
| `vpc_id` | String | Yes | Parent VPC identifier | Must reference existing VPC |
| `cidr_block` | String | Yes | IP address range for subnet | Must be subset of VPC CIDR, `/24` minimum |
| `availability_zone` | String | Yes | AZ where subnet is placed | Format: `us-east-1a`, `us-east-1b` |
| `type` | Enum | Yes | Subnet type | Values: `Public`, `Private` |
| `map_public_ip_on_launch` | Boolean | Yes | Auto-assign public IPs | `true` for Public, `false` for Private |
| `tags` | Map<String, String> | Yes | Resource tags | Must include `Name`, `Type`, `AZ` |

**Constraints**:
- `cidr_block` MUST be `/24` (256 addresses per subnet) - per BR-1.2, BR-1.3
- `availability_zone` MUST be one of: `us-east-1a`, `us-east-1b` (or configured AZs)
- `type` determines routing and resource placement:
  - `Public`: Associated with public route table, allows ALB only
  - `Private`: Associated with private route table, allows ECS, Lambda, Aurora, ElastiCache, VPC endpoints

**Lifecycle**:
1. Created after VPC
2. Destroyed before VPC
3. Cannot be deleted if resources (ECS tasks, ENIs) are attached

**Relationships**:
- **BelongsTo**: VPC (N:1)
- **PlacedIn**: AvailabilityZone (N:1)
- **AssociatedWith**: RouteTable (N:1)

**Subnet Instances** (4 total):

**Public Subnet 1 (AZ-A)**:
```yaml
Subnet:
  subnet_id: "subnet-public-1a"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  cidr_block: "10.0.1.0/24"
  availability_zone: "us-east-1a"
  type: Public
  map_public_ip_on_launch: true
  tags:
    Name: "zero2prod-public-1a"
    Type: "Public"
    AZ: "us-east-1a"
```

**Public Subnet 2 (AZ-B)**:
```yaml
Subnet:
  subnet_id: "subnet-public-1b"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  cidr_block: "10.0.2.0/24"
  availability_zone: "us-east-1b"
  type: Public
  map_public_ip_on_launch: true
  tags:
    Name: "zero2prod-public-1b"
    Type: "Public"
    AZ: "us-east-1b"
```

**Private Subnet 1 (AZ-A)**:
```yaml
Subnet:
  subnet_id: "subnet-private-1a"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  cidr_block: "10.0.10.0/24"
  availability_zone: "us-east-1a"
  type: Private
  map_public_ip_on_launch: false
  tags:
    Name: "zero2prod-private-1a"
    Type: "Private"
    AZ: "us-east-1a"
```

**Private Subnet 2 (AZ-B)**:
```yaml
Subnet:
  subnet_id: "subnet-private-1b"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  cidr_block: "10.0.11.0/24"
  availability_zone: "us-east-1b"
  type: Private
  map_public_ip_on_launch: false
  tags:
    Name: "zero2prod-private-1b"
    Type: "Private"
    AZ: "us-east-1b"
```

**Mapped Business Rules**: BR-1.2 (Public Subnet Sizing), BR-1.3 (Private Subnet Sizing), BR-1.4 (Multi-AZ Distribution)

---

### 3. Security Group Entity

**Definition**: A stateful firewall that controls inbound and outbound traffic for AWS resources based on protocol, port, and source/destination.

**Attributes**:

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `security_group_id` | String | Yes | AWS-generated security group identifier | Format: `sg-xxxxxxxx` |
| `vpc_id` | String | Yes | Parent VPC identifier | Must reference existing VPC |
| `name` | String | Yes | Security group name | Must be unique within VPC |
| `description` | String | Yes | Purpose and usage documentation | Must describe assigned resources |
| `ingress_rules` | List<IngressRule> | No | Inbound traffic rules | Can be empty list (no ingress) |
| `egress_rules` | List<EgressRule> | Yes | Outbound traffic rules | Must have at least 1 egress rule |
| `tags` | Map<String, String> | Yes | Resource tags | Must include `Name`, `Purpose` |

**Constraints**:
- `name` MUST follow naming convention: `zero2prod-<resource-type>-sg`
- `ingress_rules` can be empty (e.g., Lambda security group has no ingress)
- `egress_rules` MUST follow least-privilege principle (no `0.0.0.0/0` unless justified)

**Lifecycle**:
1. Created after VPC
2. Destroyed before VPC
3. Cannot be deleted if assigned to active resources

**Relationships**:
- **BelongsTo**: VPC (N:1)
- **AssignedTo**: Resources (ALB, ECS, Aurora, ElastiCache, Lambda, VPC Endpoints)
- **Has**: IngressRules (1:N), EgressRules (1:N)

**Security Group Instances** (6 total):

**ALB Security Group**:
```yaml
SecurityGroup:
  security_group_id: "sg-alb"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  name: "zero2prod-alb-sg"
  description: "Security group for Application Load Balancer (public internet to ALB)"
  ingress_rules:
    - protocol: TCP
      port: 443
      source: "0.0.0.0/0"
      description: "HTTPS from internet"
    - protocol: TCP
      port: 80
      source: "0.0.0.0/0"
      description: "HTTP redirect to HTTPS"
  egress_rules:
    - protocol: TCP
      port: 8000
      destination_sg: "sg-ecs"
      description: "Forward traffic to ECS tasks"
  tags:
    Name: "zero2prod-alb-sg"
    Purpose: "ALB internet-facing traffic"
```

**ECS Security Group**:
```yaml
SecurityGroup:
  security_group_id: "sg-ecs"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  name: "zero2prod-ecs-sg"
  description: "Security group for ECS Fargate tasks (web application)"
  ingress_rules:
    - protocol: TCP
      port: 8000
      source_sg: "sg-alb"
      description: "HTTP from ALB"
  egress_rules:
    - protocol: TCP
      port: 5432
      destination_sg: "sg-aurora"
      description: "PostgreSQL to Aurora"
    - protocol: TCP
      port: 6379
      destination_sg: "sg-elasticache"
      description: "Redis to ElastiCache"
    - protocol: TCP
      port: 443
      destination_sg: "sg-vpc-endpoints"
      description: "HTTPS to VPC endpoints"
  tags:
    Name: "zero2prod-ecs-sg"
    Purpose: "ECS task traffic"
```

**Aurora Security Group**:
```yaml
SecurityGroup:
  security_group_id: "sg-aurora"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  name: "zero2prod-aurora-sg"
  description: "Security group for Aurora PostgreSQL cluster"
  ingress_rules:
    - protocol: TCP
      port: 5432
      source_sg: "sg-ecs"
      description: "PostgreSQL from ECS tasks"
    - protocol: TCP
      port: 5432
      source_sg: "sg-lambda"
      description: "PostgreSQL from Lambda function"
  egress_rules: []
  tags:
    Name: "zero2prod-aurora-sg"
    Purpose: "Aurora database traffic"
```

**ElastiCache Security Group**:
```yaml
SecurityGroup:
  security_group_id: "sg-elasticache"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  name: "zero2prod-elasticache-sg"
  description: "Security group for ElastiCache Serverless Redis"
  ingress_rules:
    - protocol: TCP
      port: 6379
      source_sg: "sg-ecs"
      description: "Redis from ECS tasks"
  egress_rules: []
  tags:
    Name: "zero2prod-elasticache-sg"
    Purpose: "ElastiCache session cache traffic"
```

**Lambda Security Group**:
```yaml
SecurityGroup:
  security_group_id: "sg-lambda"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  name: "zero2prod-lambda-sg"
  description: "Security group for Lambda email sender function"
  ingress_rules: []
  egress_rules:
    - protocol: TCP
      port: 5432
      destination_sg: "sg-aurora"
      description: "PostgreSQL to Aurora"
    - protocol: TCP
      port: 443
      destination_sg: "sg-vpc-endpoints"
      description: "HTTPS to VPC endpoints"
  tags:
    Name: "zero2prod-lambda-sg"
    Purpose: "Lambda function traffic"
```

**VPC Endpoint Security Group**:
```yaml
SecurityGroup:
  security_group_id: "sg-vpc-endpoints"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  name: "zero2prod-vpc-endpoints-sg"
  description: "Security group for VPC interface endpoints"
  ingress_rules:
    - protocol: TCP
      port: 443
      source_sg: "sg-ecs"
      description: "HTTPS from ECS tasks"
    - protocol: TCP
      port: 443
      source_sg: "sg-lambda"
      description: "HTTPS from Lambda function"
  egress_rules: []
  tags:
    Name: "zero2prod-vpc-endpoints-sg"
    Purpose: "VPC endpoint traffic"
```

**Mapped Business Rules**: BR-3.1 to BR-3.9 (Security Group Rules), BR-8.1 (Security Group Documentation)

---

### 4. Ingress Rule Sub-Entity

**Definition**: A rule that controls inbound traffic to a security group.

**Attributes**:

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `protocol` | Enum | Yes | Network protocol | Values: `TCP`, `UDP`, `ICMP`, `ALL` |
| `port` | Integer | Conditional | Destination port number | Required for TCP/UDP, range: 0-65535 |
| `port_range` | String | Conditional | Port range (e.g., "80-443") | Mutually exclusive with `port` |
| `source` | String | Conditional | Source IP CIDR block | Format: `x.x.x.x/y`, example: `0.0.0.0/0` |
| `source_sg` | String | Conditional | Source security group ID | Mutually exclusive with `source` |
| `description` | String | Yes | Rule purpose and rationale | Must document why rule exists |

**Constraints**:
- EITHER `source` OR `source_sg` MUST be provided (not both)
- `port` is required for `TCP` and `UDP` protocols
- `description` MUST clearly explain the rule's purpose

**Mapped Business Rules**: BR-3.1 to BR-3.9 (Security Group Rules)

---

### 5. Egress Rule Sub-Entity

**Definition**: A rule that controls outbound traffic from a security group.

**Attributes**:

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `protocol` | Enum | Yes | Network protocol | Values: `TCP`, `UDP`, `ICMP`, `ALL` |
| `port` | Integer | Conditional | Destination port number | Required for TCP/UDP, range: 0-65535 |
| `port_range` | String | Conditional | Port range (e.g., "80-443") | Mutually exclusive with `port` |
| `destination` | String | Conditional | Destination IP CIDR block | Format: `x.x.x.x/y`, example: `0.0.0.0/0` |
| `destination_sg` | String | Conditional | Destination security group ID | Mutually exclusive with `destination` |
| `description` | String | Yes | Rule purpose and rationale | Must document why rule exists |

**Constraints**:
- EITHER `destination` OR `destination_sg` MUST be provided (not both)
- `port` is required for `TCP` and `UDP` protocols
- `description` MUST clearly explain the rule's purpose
- Avoid `destination: "0.0.0.0/0"` unless explicitly justified (least privilege)

**Mapped Business Rules**: BR-3.2, BR-3.4, BR-3.8 (Least-Privilege Egress Rules)

---

### 6. VPC Endpoint Entity

**Definition**: A network interface that enables private connectivity to AWS services without internet gateway or NAT gateway.

**Attributes**:

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `endpoint_id` | String | Yes | AWS-generated VPC endpoint identifier | Format: `vpce-xxxxxxxx` |
| `vpc_id` | String | Yes | Parent VPC identifier | Must reference existing VPC |
| `service_name` | String | Yes | AWS service DNS name | Format: `com.amazonaws.region.service` |
| `endpoint_type` | Enum | Yes | Endpoint type | Values: `Gateway`, `Interface` |
| `subnet_ids` | List<String> | Conditional | Subnets for interface endpoints | Required for `Interface` type, both private subnets |
| `security_group_ids` | List<String> | Conditional | Security groups for interface endpoints | Required for `Interface` type |
| `route_table_ids` | List<String> | Conditional | Route tables for gateway endpoints | Required for `Gateway` type |
| `private_dns_enabled` | Boolean | Conditional | Enable private DNS resolution | Required `true` for `Interface` type |
| `tags` | Map<String, String> | Yes | Resource tags | Must include `Name`, `Service` |

**Constraints**:
- `endpoint_type` = `Gateway`: Requires `route_table_ids`, used for S3 only
- `endpoint_type` = `Interface`: Requires `subnet_ids`, `security_group_ids`, `private_dns_enabled`
- `private_dns_enabled` MUST be `true` for interface endpoints (per BR-2.7)
- `subnet_ids` MUST include BOTH private subnets for Multi-AZ (per BR-2.6)

**Lifecycle**:
1. Created after VPC, subnets, security groups, route tables
2. Destroyed before VPC
3. Cannot be deleted if actively used by resources

**Relationships**:
- **BelongsTo**: VPC (N:1)
- **PlacedIn**: Subnets (N:N, interface endpoints only)
- **Uses**: SecurityGroup (N:1, interface endpoints only)
- **AssociatedWith**: RouteTable (N:N, gateway endpoints only)

**VPC Endpoint Instances** (8 total):

**S3 Gateway Endpoint**:
```yaml
VPCEndpoint:
  endpoint_id: "vpce-s3-gateway"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  service_name: "com.amazonaws.us-east-1.s3"
  endpoint_type: Gateway
  route_table_ids:
    - "rtb-private"
  tags:
    Name: "zero2prod-s3-gateway-endpoint"
    Service: "s3"
```

**ECR API Interface Endpoint**:
```yaml
VPCEndpoint:
  endpoint_id: "vpce-ecr-api"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  service_name: "com.amazonaws.us-east-1.ecr.api"
  endpoint_type: Interface
  subnet_ids:
    - "subnet-private-1a"
    - "subnet-private-1b"
  security_group_ids:
    - "sg-vpc-endpoints"
  private_dns_enabled: true
  tags:
    Name: "zero2prod-ecr-api-endpoint"
    Service: "ecr-api"
```

**ECR DKR Interface Endpoint**:
```yaml
VPCEndpoint:
  endpoint_id: "vpce-ecr-dkr"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  service_name: "com.amazonaws.us-east-1.ecr.dkr"
  endpoint_type: Interface
  subnet_ids:
    - "subnet-private-1a"
    - "subnet-private-1b"
  security_group_ids:
    - "sg-vpc-endpoints"
  private_dns_enabled: true
  tags:
    Name: "zero2prod-ecr-dkr-endpoint"
    Service: "ecr-dkr"
```

**CloudWatch Logs Interface Endpoint**:
```yaml
VPCEndpoint:
  endpoint_id: "vpce-logs"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  service_name: "com.amazonaws.us-east-1.logs"
  endpoint_type: Interface
  subnet_ids:
    - "subnet-private-1a"
    - "subnet-private-1b"
  security_group_ids:
    - "sg-vpc-endpoints"
  private_dns_enabled: true
  tags:
    Name: "zero2prod-logs-endpoint"
    Service: "logs"
```

**Secrets Manager Interface Endpoint**:
```yaml
VPCEndpoint:
  endpoint_id: "vpce-secretsmanager"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  service_name: "com.amazonaws.us-east-1.secretsmanager"
  endpoint_type: Interface
  subnet_ids:
    - "subnet-private-1a"
    - "subnet-private-1b"
  security_group_ids:
    - "sg-vpc-endpoints"
  private_dns_enabled: true
  tags:
    Name: "zero2prod-secretsmanager-endpoint"
    Service: "secretsmanager"
```

**STS Interface Endpoint**:
```yaml
VPCEndpoint:
  endpoint_id: "vpce-sts"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  service_name: "com.amazonaws.us-east-1.sts"
  endpoint_type: Interface
  subnet_ids:
    - "subnet-private-1a"
    - "subnet-private-1b"
  security_group_ids:
    - "sg-vpc-endpoints"
  private_dns_enabled: true
  tags:
    Name: "zero2prod-sts-endpoint"
    Service: "sts"
```

**SES Interface Endpoint**:
```yaml
VPCEndpoint:
  endpoint_id: "vpce-ses"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  service_name: "com.amazonaws.us-east-1.ses"
  endpoint_type: Interface
  subnet_ids:
    - "subnet-private-1a"
    - "subnet-private-1b"
  security_group_ids:
    - "sg-vpc-endpoints"
  private_dns_enabled: true
  tags:
    Name: "zero2prod-ses-endpoint"
    Service: "ses"
```

**SQS Interface Endpoint**:
```yaml
VPCEndpoint:
  endpoint_id: "vpce-sqs"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  service_name: "com.amazonaws.us-east-1.sqs"
  endpoint_type: Interface
  subnet_ids:
    - "subnet-private-1a"
    - "subnet-private-1b"
  security_group_ids:
    - "sg-vpc-endpoints"
  private_dns_enabled: true
  tags:
    Name: "zero2prod-sqs-endpoint"
    Service: "sqs"
```

**Mapped Business Rules**: BR-2.5 (VPC Endpoint Requirements), BR-2.6 (Multi-AZ Interface Endpoints), BR-2.7 (Private DNS), BR-6.1 (S3 Gateway Endpoint), BR-6.2 (Interface Endpoints)

---

### 7. Route Table Entity

**Definition**: A set of routing rules that determine where network traffic from subnets is directed.

**Attributes**:

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `route_table_id` | String | Yes | AWS-generated route table identifier | Format: `rtb-xxxxxxxx` |
| `vpc_id` | String | Yes | Parent VPC identifier | Must reference existing VPC |
| `name` | String | Yes | Route table name | Values: `Public`, `Private` |
| `routes` | List<Route> | Yes | Routing rules | Must have at least local route |
| `associated_subnet_ids` | List<String> | Yes | Subnets using this route table | Must have at least 1 subnet |
| `tags` | Map<String, String> | Yes | Resource tags | Must include `Name`, `Type` |

**Constraints**:
- `routes` MUST include local route (`10.0.0.0/16` → `local`) - AWS automatic
- Public route table MUST have default route to IGW
- Private route table MUST NOT have default route to IGW or NAT Gateway

**Lifecycle**:
1. Created after VPC
2. Destroyed before VPC
3. Cannot be deleted if associated with subnets

**Relationships**:
- **BelongsTo**: VPC (N:1)
- **Has**: Routes (1:N)
- **AssociatedWith**: Subnets (1:N)

**Route Table Instances** (2 total):

**Public Route Table**:
```yaml
RouteTable:
  route_table_id: "rtb-public"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  name: "Public"
  routes:
    - destination: "10.0.0.0/16"
      target: "local"
      description: "VPC-internal traffic"
    - destination: "0.0.0.0/0"
      target: "igw-xxxxxxxx"
      description: "Default route to internet gateway"
  associated_subnet_ids:
    - "subnet-public-1a"
    - "subnet-public-1b"
  tags:
    Name: "zero2prod-public-rtb"
    Type: "Public"
```

**Private Route Table**:
```yaml
RouteTable:
  route_table_id: "rtb-private"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  name: "Private"
  routes:
    - destination: "10.0.0.0/16"
      target: "local"
      description: "VPC-internal traffic"
    - destination: "s3-prefix-list"
      target: "vpce-s3-gateway"
      description: "S3 traffic to gateway endpoint (AWS automatic)"
  associated_subnet_ids:
    - "subnet-private-1a"
    - "subnet-private-1b"
  tags:
    Name: "zero2prod-private-rtb"
    Type: "Private"
```

**Mapped Business Rules**: BR-2.1 (Public Routing), BR-2.2 (Private No Internet), BR-2.3 (No NAT Gateway)

---

### 8. Route Sub-Entity

**Definition**: A routing rule that specifies destination CIDR and target (gateway, endpoint, local).

**Attributes**:

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `destination` | String | Yes | Destination IP CIDR block | Format: `x.x.x.x/y`, example: `0.0.0.0/0` |
| `target` | String | Yes | Route target | Values: `local`, `igw-xxx`, `vpce-xxx`, `nat-xxx` |
| `description` | String | Yes | Route purpose | Must document why route exists |

**Constraints**:
- `destination` = `10.0.0.0/16` → `target` MUST be `local` (AWS automatic)
- `destination` = `0.0.0.0/0` → `target` MUST be `igw-xxx` (public route table only)
- Private route table MUST NOT have `destination` = `0.0.0.0/0` (per BR-2.2)

**Mapped Business Rules**: BR-2.1 (Public Routing), BR-2.2 (Private No Internet)

---

### 9. Internet Gateway Entity

**Definition**: A horizontally scaled, redundant, highly available VPC component that enables internet communication for public subnets.

**Attributes**:

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `internet_gateway_id` | String | Yes | AWS-generated IGW identifier | Format: `igw-xxxxxxxx` |
| `vpc_id` | String | Yes | Attached VPC identifier | Must reference existing VPC |
| `tags` | Map<String, String> | Yes | Resource tags | Must include `Name` |

**Constraints**:
- Only 1 Internet Gateway per VPC
- Must be attached to VPC
- Used ONLY in public route table

**Lifecycle**:
1. Created after VPC
2. Attached to VPC
3. Destroyed before VPC

**Relationships**:
- **AttachedTo**: VPC (1:1)
- **UsedBy**: Public Route Table

**Example**:
```yaml
InternetGateway:
  internet_gateway_id: "igw-xxxxxxxx"
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  tags:
    Name: "zero2prod-igw"
```

**Mapped Business Rules**: BR-2.1 (Public Routing), BR-2.4 (Public Internet Gateway Access)

---

### 10. Availability Zone Entity

**Definition**: A physically separate, isolated data center within an AWS region, used for high availability deployments.

**Attributes**:

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `az_id` | String | Yes | AWS availability zone identifier | Format: `us-east-1a`, `us-east-1b` |
| `az_name` | String | Yes | Human-readable AZ name | Example: `US East (N. Virginia) - AZ A` |
| `region` | String | Yes | AWS region | Example: `us-east-1` |

**Constraints**:
- Minimum 2 AZs required for Multi-AZ deployment (per BR-1.4)
- Each AZ contains 1 public subnet and 1 private subnet

**Relationships**:
- **Contains**: Subnets (1:N)

**Availability Zone Instances** (2 total):

**AZ-A**:
```yaml
AvailabilityZone:
  az_id: "us-east-1a"
  az_name: "US East (N. Virginia) - AZ A"
  region: "us-east-1"
```

**AZ-B**:
```yaml
AvailabilityZone:
  az_id: "us-east-1b"
  az_name: "US East (N. Virginia) - AZ B"
  region: "us-east-1"
```

**Mapped Business Rules**: BR-1.4 (Multi-AZ Distribution), BR-1.5 (Multi-AZ Deployment)

---

## Entity Instance Summary

| Entity Type | Instance Count | Names |
|-------------|----------------|-------|
| VPC | 1 | `zero2prod-vpc` |
| Subnet | 4 | `zero2prod-public-1a`, `zero2prod-public-1b`, `zero2prod-private-1a`, `zero2prod-private-1b` |
| Security Group | 6 | `zero2prod-alb-sg`, `zero2prod-ecs-sg`, `zero2prod-aurora-sg`, `zero2prod-elasticache-sg`, `zero2prod-lambda-sg`, `zero2prod-vpc-endpoints-sg` |
| VPC Endpoint | 8 | S3 (Gateway), ECR API, ECR DKR, CloudWatch Logs, Secrets Manager, STS, SES, SQS (all Interface) |
| Route Table | 2 | `zero2prod-public-rtb`, `zero2prod-private-rtb` |
| Internet Gateway | 1 | `zero2prod-igw` |
| Availability Zone | 2 | `us-east-1a`, `us-east-1b` |

**Total Entities**: 24 instances across 7 entity types

---

## Entity Validation Rules

### Validation Checklist

**VPC Validation**:
- [ ] VPC CIDR is `10.0.0.0/16`
- [ ] DNS hostnames enabled
- [ ] DNS support enabled

**Subnet Validation**:
- [ ] 4 subnets created (2 public, 2 private)
- [ ] Each subnet is `/24` (256 addresses)
- [ ] Public subnets in both AZs
- [ ] Private subnets in both AZs
- [ ] Public subnets: `map_public_ip_on_launch = true`
- [ ] Private subnets: `map_public_ip_on_launch = false`

**Security Group Validation**:
- [ ] 6 security groups created
- [ ] All ingress/egress rules documented
- [ ] No `0.0.0.0/0` egress except ALB (justified)
- [ ] Lambda security group has 0 ingress rules
- [ ] Aurora/ElastiCache security groups have 0 egress rules

**VPC Endpoint Validation**:
- [ ] 8 VPC endpoints created (1 Gateway, 7 Interface)
- [ ] Interface endpoints in BOTH private subnets
- [ ] Private DNS enabled for all interface endpoints
- [ ] Gateway endpoint associated with private route table

**Route Table Validation**:
- [ ] 2 route tables created (1 public, 1 private)
- [ ] Public route table has default route to IGW
- [ ] Private route table has NO default route
- [ ] Public subnets associated with public route table
- [ ] Private subnets associated with private route table

**Internet Gateway Validation**:
- [ ] 1 Internet Gateway attached to VPC
- [ ] Used in public route table ONLY

**Availability Zone Validation**:
- [ ] 2 Availability Zones used
- [ ] Each AZ contains 1 public subnet and 1 private subnet

---

## Summary

This document defines 10 domain entities for the network infrastructure:

1. **VPC**: Top-level network container (1 instance)
2. **Subnet**: Network subdivisions (4 instances: 2 public, 2 private)
3. **Security Group**: Stateful firewalls (6 instances)
4. **Ingress Rule**: Inbound traffic rules (sub-entity)
5. **Egress Rule**: Outbound traffic rules (sub-entity)
6. **VPC Endpoint**: Private AWS service access (8 instances)
7. **Route Table**: Routing rules (2 instances: 1 public, 1 private)
8. **Route**: Individual routing rules (sub-entity)
9. **Internet Gateway**: Public internet access (1 instance)
10. **Availability Zone**: Physical data centers (2 instances)

**Total Entity Instances**: 24 across 7 top-level entity types

**Next Steps**: Infrastructure Design will implement these entities using AWS CDK Python constructs (L2 constructs for higher-level abstractions, L1 constructs for fine-grained control).

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-12  
**Status**: Ready for Review
