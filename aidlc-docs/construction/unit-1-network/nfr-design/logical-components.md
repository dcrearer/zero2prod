# Logical Components - Unit 1: Network Infrastructure

## Overview

This document defines the logical component architecture for the network infrastructure. Logical components represent cohesive groupings of domain entities that work together to implement NFR patterns.

**Purpose**: Bridge the gap between functional design (domain entities) and infrastructure design (AWS CDK constructs).

**Scope**: Network layer, routing layer, security layer, private connectivity layer, and observability layer.

---

## Component Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Internet (Public)                           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         NETWORK LAYER                               │
│  ┌────────────────────┐              ┌────────────────────┐         │
│  │  Public Subnet 1a  │              │  Public Subnet 1b  │         │
│  │  10.0.1.0/24       │              │  10.0.2.0/24       │         │
│  │  (us-east-1a)      │              │  (us-east-1b)      │         │
│  │  ALB ONLY          │              │  ALB ONLY          │         │
│  └────────────────────┘              └────────────────────┘         │
│                                                                       │
│  ┌────────────────────┐              ┌────────────────────┐         │
│  │  Private Subnet 1a │              │  Private Subnet 1b │         │
│  │  10.0.10.0/24      │              │  10.0.11.0/24      │         │
│  │  (us-east-1a)      │              │  (us-east-1b)      │         │
│  │  ECS, Aurora, etc. │              │  ECS, Aurora, etc. │         │
│  └────────────────────┘              └────────────────────┘         │
│                                                                       │
│  VPC: 10.0.0.0/16                                                    │
│  Internet Gateway: igw-xxxxxxxx                                      │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         ROUTING LAYER                               │
│  ┌────────────────────┐              ┌────────────────────┐         │
│  │  Public Route Table│              │ Private Route Table│         │
│  │  0.0.0.0/0 → IGW   │              │ 10.0.0.0/16 → local│         │
│  │  10.0.0.0/16 → local│             │ S3 → Gateway EP    │         │
│  └────────────────────┘              └────────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         SECURITY LAYER                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  ALB SG  │  │  ECS SG  │  │Aurora SG │  │ Cache SG │           │
│  │ (public) │  │ (private)│  │(private) │  │(private) │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│                                                                       │
│  ┌──────────┐  ┌──────────┐                                         │
│  │Lambda SG │  │ VPC EP SG│                                         │
│  │(private) │  │(private) │                                         │
│  └──────────┘  └──────────┘                                         │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   PRIVATE CONNECTIVITY LAYER                        │
│  ┌────────────────────┐              ┌────────────────────┐         │
│  │  S3 Gateway EP     │              │  Interface EPs     │         │
│  │  (route-based)     │              │  (ENI-based)       │         │
│  │  Free              │              │  7 endpoints       │         │
│  └────────────────────┘              │  - ECR API/DKR     │         │
│                                       │  - Logs, Secrets   │         │
│                                       │  - STS, SES, SQS   │         │
│                                       └────────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      OBSERVABILITY LAYER                            │
│  ┌────────────────────┐              ┌────────────────────┐         │
│  │  CloudWatch Metrics│              │  Resource Tags     │         │
│  │  - Available IPs   │              │  - Name, Project   │         │
│  │  - VPC EP data     │              │  - Environment     │         │
│  │  - ALB metrics     │              │  - ManagedBy       │         │
│  └────────────────────┘              └────────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. Network Layer

### 1.1 Component Overview

**Purpose**: Provide isolated network environment with Multi-AZ subnet architecture.

**Responsibilities**:
- Define VPC address space (10.0.0.0/16)
- Create public and private subnets across 2 Availability Zones
- Attach Internet Gateway for public subnet internet access
- Enable DNS hostnames and DNS support for VPC endpoints

**NFR Patterns Implemented**:
- Multi-AZ Pattern (NFR-1)
- Subnet Redundancy Pattern (NFR-1, NFR-11)
- IP Address Space Planning Pattern (NFR-11)

---

### 1.2 Sub-Components

#### 1.2.1 VPC Component

**Domain Entities**: VPC (1 instance)

**Attributes**:
- CIDR Block: `10.0.0.0/16` (65,536 addresses)
- DNS Hostnames: Enabled (required for VPC endpoint private DNS)
- DNS Support: Enabled (required for DNS resolution)

**Configuration**:
```yaml
VPC:
  cidr_block: "10.0.0.0/16"
  enable_dns_hostnames: true
  enable_dns_support: true
  tags:
    Name: "zero2prod-vpc"
    Project: "zero2prod"
    Environment: "production"
    ManagedBy: "CDK"
```

**Business Rules Enforced**:
- BR-1.1: VPC CIDR Block Rule (10.0.0.0/16)

---

#### 1.2.2 Public Subnet Component

**Domain Entities**: Subnet (2 instances - one per AZ)

**Purpose**: Host Application Load Balancer for public internet access.

**Attributes**:
- Subnet 1a CIDR: `10.0.1.0/24` (256 addresses in us-east-1a)
- Subnet 1b CIDR: `10.0.2.0/24` (256 addresses in us-east-1b)
- Auto-assign public IPs: Enabled
- Type: Public

**Configuration**:
```yaml
PublicSubnet1a:
  cidr_block: "10.0.1.0/24"
  availability_zone: "us-east-1a"
  map_public_ip_on_launch: true
  tags:
    Name: "zero2prod-public-1a"
    Type: "Public"
    AZ: "us-east-1a"

PublicSubnet1b:
  cidr_block: "10.0.2.0/24"
  availability_zone: "us-east-1b"
  map_public_ip_on_launch: true
  tags:
    Name: "zero2prod-public-1b"
    Type: "Public"
    AZ: "us-east-1b"
```

**Resource Placement**:
- Allowed: Application Load Balancer ONLY
- Denied: ECS tasks, Lambda, Aurora, ElastiCache, VPC endpoints

**Business Rules Enforced**:
- BR-1.2: Public Subnet Sizing Rule (/24)
- BR-1.4: Multi-AZ Subnet Distribution Rule

**Capacity Analysis**:
- Total addresses: 256
- AWS reserved: 5 (first 4 + broadcast)
- Current usage: 2 ALB nodes per subnet
- Available capacity: 249 addresses (97% free)

---

#### 1.2.3 Private Subnet Component

**Domain Entities**: Subnet (2 instances - one per AZ)

**Purpose**: Host application tier (ECS, Lambda), data tier (Aurora, ElastiCache), and VPC endpoint ENIs.

**Attributes**:
- Subnet 1a CIDR: `10.0.10.0/24` (256 addresses in us-east-1a)
- Subnet 1b CIDR: `10.0.11.0/24` (256 addresses in us-east-1b)
- Auto-assign public IPs: Disabled
- Type: Private

**Configuration**:
```yaml
PrivateSubnet1a:
  cidr_block: "10.0.10.0/24"
  availability_zone: "us-east-1a"
  map_public_ip_on_launch: false
  tags:
    Name: "zero2prod-private-1a"
    Type: "Private"
    AZ: "us-east-1a"

PrivateSubnet1b:
  cidr_block: "10.0.11.0/24"
  availability_zone: "us-east-1b"
  map_public_ip_on_launch: false
  tags:
    Name: "zero2prod-private-1b"
    Type: "Private"
    AZ: "us-east-1b"
```

**Resource Placement**:
- Allowed: ECS tasks, Lambda ENIs, Aurora instances, ElastiCache nodes, VPC endpoint ENIs
- Denied: ALB (must be in public subnets)

**Business Rules Enforced**:
- BR-1.3: Private Subnet Sizing Rule (/24)
- BR-1.4: Multi-AZ Subnet Distribution Rule

**Capacity Analysis**:
- Total addresses: 256 per subnet
- AWS reserved: 5 per subnet
- Current usage per subnet: ~19 resources (ECS, Aurora, ElastiCache, VPC endpoint ENIs)
- Available capacity: ~232 addresses per subnet (91% free)
- Growth headroom: 10x scale (19 → 190 resources)

---

#### 1.2.4 Internet Gateway Component

**Domain Entities**: InternetGateway (1 instance)

**Purpose**: Enable internet access for resources in public subnets (ALB).

**Attributes**:
- Attachment: VPC
- High Availability: AWS-managed (99.99%+)

**Configuration**:
```yaml
InternetGateway:
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  tags:
    Name: "zero2prod-igw"
    Project: "zero2prod"
    ManagedBy: "CDK"
```

**Business Rules Enforced**:
- BR-2.1: Public Subnet Internet Routing Rule (used in public route table)
- BR-2.4: Public Subnet Internet Gateway Access Rule

**High Availability**:
- AWS-managed redundancy (horizontally scaled)
- No single point of failure
- Automatic failover within AWS infrastructure

---

### 1.3 Component Interactions

```
┌──────────────┐
│   Internet   │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Internet Gateway │
└──────┬───────────┘
       │
       ▼
┌────────────────────────────────┐
│      Public Subnets (2)        │
│  - 10.0.1.0/24 (us-east-1a)    │
│  - 10.0.2.0/24 (us-east-1b)    │
│                                 │
│  Resources: ALB ONLY           │
└────────────────────────────────┘

┌────────────────────────────────┐
│      Private Subnets (2)       │
│  - 10.0.10.0/24 (us-east-1a)   │
│  - 10.0.11.0/24 (us-east-1b)   │
│                                 │
│  Resources: ECS, Lambda,       │
│  Aurora, ElastiCache, VPC EPs  │
│                                 │
│  NO internet access            │
└────────────────────────────────┘
```

**Data Flow**:
1. Internet → Internet Gateway
2. Internet Gateway → Public Subnets (ALB)
3. ALB → Private Subnets (ECS tasks)
4. Private Subnets → VPC Endpoints → AWS Services
5. Private Subnets → Aurora, ElastiCache (within VPC)

---

## 2. Routing Layer

### 2.1 Component Overview

**Purpose**: Control network traffic routing for public and private subnets.

**Responsibilities**:
- Route public subnet traffic to Internet Gateway
- Route private subnet traffic to local VPC only
- Route S3 traffic to S3 Gateway Endpoint
- Prevent internet egress from private subnets

**NFR Patterns Implemented**:
- Private Networking Pattern (NFR-3, SECURITY-04)
- VPC Endpoint Pattern (NFR-3, SECURITY-04)
- No NAT Gateway Pattern (NFR-12, NFR-3)

---

### 2.2 Sub-Components

#### 2.2.1 Public Route Table Component

**Domain Entities**: RouteTable (1 instance), Route (2 instances)

**Purpose**: Enable internet access for resources in public subnets.

**Configuration**:
```yaml
PublicRouteTable:
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  routes:
    - destination: "10.0.0.0/16"
      target: "local"
      description: "VPC-internal traffic"
    - destination: "0.0.0.0/0"
      target: "igw-xxxxxxxx"
      description: "Default route to Internet Gateway"
  associated_subnets:
    - "subnet-public-1a"
    - "subnet-public-1b"
  tags:
    Name: "zero2prod-public-rtb"
    Type: "Public"
```

**Routing Rules**:
1. Local VPC traffic: `10.0.0.0/16` → `local` (AWS automatic)
2. Default route: `0.0.0.0/0` → Internet Gateway (internet access)

**Business Rules Enforced**:
- BR-2.1: Public Subnet Internet Routing Rule (default route to IGW)

**Associated Subnets**:
- Public Subnet 1a (10.0.1.0/24)
- Public Subnet 1b (10.0.2.0/24)

---

#### 2.2.2 Private Route Table Component

**Domain Entities**: RouteTable (1 instance), Route (2 instances)

**Purpose**: Isolate private subnets from internet, enable VPC endpoint access.

**Configuration**:
```yaml
PrivateRouteTable:
  vpc_id: "vpc-0a1b2c3d4e5f6g7h8"
  routes:
    - destination: "10.0.0.0/16"
      target: "local"
      description: "VPC-internal traffic"
    - destination: "s3-prefix-list"
      target: "vpce-s3-gateway"
      description: "S3 traffic to Gateway Endpoint (AWS automatic)"
  associated_subnets:
    - "subnet-private-1a"
    - "subnet-private-1b"
  tags:
    Name: "zero2prod-private-rtb"
    Type: "Private"
```

**Routing Rules**:
1. Local VPC traffic: `10.0.0.0/16` → `local` (AWS automatic)
2. S3 traffic: S3 prefix list → S3 Gateway Endpoint (AWS automatic when endpoint created)

**Critical Security Rule**: NO default route to Internet Gateway or NAT Gateway (no internet egress)

**Business Rules Enforced**:
- BR-2.2: Private Subnet NO Internet Egress Rule (no default route)
- BR-2.3: No NAT Gateway Rule (no NAT Gateway route)
- BR-2.4: Public Subnet Internet Gateway Access Rule (IGW only in public route table)

**Associated Subnets**:
- Private Subnet 1a (10.0.10.0/24)
- Private Subnet 1b (10.0.11.0/24)

---

### 2.3 Component Interactions

```
Public Route Table:
  0.0.0.0/0 → Internet Gateway (internet access)
  10.0.0.0/16 → local (VPC-internal)
  ↓
  Associated with: Public Subnet 1a, Public Subnet 1b

Private Route Table:
  10.0.0.0/16 → local (VPC-internal ONLY)
  S3 Prefix List → S3 Gateway Endpoint (automatic)
  NO default route (no internet egress)
  ↓
  Associated with: Private Subnet 1a, Private Subnet 1b
```

**Validation**: Verify private route table has NO route to `0.0.0.0/0` (internet egress blocked)

---

## 3. Security Layer

### 3.1 Component Overview

**Purpose**: Enforce least-privilege network access control via security groups.

**Responsibilities**:
- Control inbound and outbound traffic for all resources
- Implement security group layering (ALB → ECS → Aurora/ElastiCache/VPC Endpoints)
- Document all security group rules
- Prevent overly permissive rules (no `0.0.0.0/0` egress except ALB)

**NFR Patterns Implemented**:
- Security Group Layering Pattern (SECURITY-04, SECURITY-05)
- Encryption in Transit Pattern (NFR-5, SECURITY-01)

---

### 3.2 Sub-Components

#### 3.2.1 ALB Security Group Component

**Domain Entities**: SecurityGroup (1 instance), IngressRule (2 instances), EgressRule (1 instance)

**Purpose**: Allow public HTTPS access to ALB, forward traffic to ECS tasks only.

**Configuration**:
```yaml
ALBSecurityGroup:
  name: "zero2prod-alb-sg"
  description: "Security group for Application Load Balancer (public internet to ALB)"
  ingress_rules:
    - protocol: TCP
      port: 443
      source: "0.0.0.0/0"
      description: "HTTPS from internet for public access"
    - protocol: TCP
      port: 80
      source: "0.0.0.0/0"
      description: "HTTP from internet (redirects to HTTPS)"
  egress_rules:
    - protocol: TCP
      port: 8000
      destination_sg: "zero2prod-ecs-sg"
      description: "Forward traffic to ECS tasks on port 8000"
  tags:
    Name: "zero2prod-alb-sg"
    Purpose: "ALB internet-facing traffic"
```

**Business Rules Enforced**:
- BR-3.1: ALB Internet Access Rule (allow HTTPS from 0.0.0.0/0)
- BR-3.2: ALB to ECS Only Rule (egress to ECS SG only)

**Justification for 0.0.0.0/0 Ingress**: ALB is public-facing, must accept HTTPS from any internet source.

---

#### 3.2.2 ECS Security Group Component

**Domain Entities**: SecurityGroup (1 instance), IngressRule (1 instance), EgressRule (3 instances)

**Purpose**: Accept traffic from ALB, allow outbound to Aurora, ElastiCache, VPC Endpoints.

**Configuration**:
```yaml
ECSSecurityGroup:
  name: "zero2prod-ecs-sg"
  description: "Security group for ECS Fargate tasks (web application)"
  ingress_rules:
    - protocol: TCP
      port: 8000
      source_sg: "zero2prod-alb-sg"
      description: "HTTP from ALB on port 8000"
  egress_rules:
    - protocol: TCP
      port: 5432
      destination_sg: "zero2prod-aurora-sg"
      description: "PostgreSQL to Aurora database"
    - protocol: TCP
      port: 6379
      destination_sg: "zero2prod-elasticache-sg"
      description: "Redis to ElastiCache session cache"
    - protocol: TCP
      port: 443
      destination_sg: "zero2prod-vpc-endpoints-sg"
      description: "HTTPS to VPC endpoints for AWS API access"
  tags:
    Name: "zero2prod-ecs-sg"
    Purpose: "ECS task traffic"
```

**Business Rules Enforced**:
- BR-3.3: ECS Accepts Traffic ONLY from ALB Rule (ingress from ALB SG only)
- BR-3.4: ECS Outbound Least-Privilege Rule (egress to specific SGs only)

---

#### 3.2.3 Aurora Security Group Component

**Domain Entities**: SecurityGroup (1 instance), IngressRule (2 instances), EgressRule (0 instances)

**Purpose**: Accept PostgreSQL connections from ECS and Lambda only.

**Configuration**:
```yaml
AuroraSecurityGroup:
  name: "zero2prod-aurora-sg"
  description: "Security group for Aurora PostgreSQL cluster"
  ingress_rules:
    - protocol: TCP
      port: 5432
      source_sg: "zero2prod-ecs-sg"
      description: "PostgreSQL from ECS tasks for web app database queries"
    - protocol: TCP
      port: 5432
      source_sg: "zero2prod-lambda-sg"
      description: "PostgreSQL from Lambda function for newsletter content retrieval"
  egress_rules: []
  tags:
    Name: "zero2prod-aurora-sg"
    Purpose: "Aurora database traffic"
```

**Business Rules Enforced**:
- BR-3.5: Aurora Accepts Traffic ONLY from ECS and Lambda Rule (ingress from ECS and Lambda SGs only)

**No Egress Rules**: Database does not initiate outbound connections (stateful security group allows return traffic automatically).

---

#### 3.2.4 ElastiCache Security Group Component

**Domain Entities**: SecurityGroup (1 instance), IngressRule (1 instance), EgressRule (0 instances)

**Purpose**: Accept Redis connections from ECS only.

**Configuration**:
```yaml
ElastiCacheSecurityGroup:
  name: "zero2prod-elasticache-sg"
  description: "Security group for ElastiCache Serverless Redis"
  ingress_rules:
    - protocol: TCP
      port: 6379
      source_sg: "zero2prod-ecs-sg"
      description: "Redis from ECS tasks for session cache access"
  egress_rules: []
  tags:
    Name: "zero2prod-elasticache-sg"
    Purpose: "ElastiCache session cache traffic"
```

**Business Rules Enforced**:
- BR-3.6: ElastiCache Accepts Traffic ONLY from ECS Rule (ingress from ECS SG only)

**No Egress Rules**: Cache does not initiate outbound connections.

---

#### 3.2.5 Lambda Security Group Component

**Domain Entities**: SecurityGroup (1 instance), IngressRule (0 instances), EgressRule (2 instances)

**Purpose**: Allow Lambda to access Aurora and VPC Endpoints (no ingress, event-driven).

**Configuration**:
```yaml
LambdaSecurityGroup:
  name: "zero2prod-lambda-sg"
  description: "Security group for Lambda email sender function"
  ingress_rules: []
  egress_rules:
    - protocol: TCP
      port: 5432
      destination_sg: "zero2prod-aurora-sg"
      description: "PostgreSQL to Aurora for newsletter content retrieval"
    - protocol: TCP
      port: 443
      destination_sg: "zero2prod-vpc-endpoints-sg"
      description: "HTTPS to VPC endpoints for SES email sending"
  tags:
    Name: "zero2prod-lambda-sg"
    Purpose: "Lambda function traffic"
```

**Business Rules Enforced**:
- BR-3.7: Lambda No Ingress Rule (0 ingress rules, event-driven)
- BR-3.8: Lambda Outbound Least-Privilege Rule (egress to Aurora and VPC Endpoint SGs only)

---

#### 3.2.6 VPC Endpoint Security Group Component

**Domain Entities**: SecurityGroup (1 instance), IngressRule (2 instances), EgressRule (0 instances)

**Purpose**: Accept HTTPS connections from ECS and Lambda for AWS service access.

**Configuration**:
```yaml
VPCEndpointSecurityGroup:
  name: "zero2prod-vpc-endpoints-sg"
  description: "Security group for VPC interface endpoints"
  ingress_rules:
    - protocol: TCP
      port: 443
      source_sg: "zero2prod-ecs-sg"
      description: "HTTPS from ECS tasks for AWS API calls (Secrets Manager, SES, SQS, etc.)"
    - protocol: TCP
      port: 443
      source_sg: "zero2prod-lambda-sg"
      description: "HTTPS from Lambda function for AWS API calls (SES, Secrets Manager)"
  egress_rules: []
  tags:
    Name: "zero2prod-vpc-endpoints-sg"
    Purpose: "VPC endpoint traffic"
```

**Business Rules Enforced**:
- BR-3.9: VPC Endpoint Accepts Traffic ONLY from ECS and Lambda Rule (ingress from ECS and Lambda SGs only)

**No Egress Rules**: VPC endpoints do not initiate outbound connections (AWS service responses allowed automatically via stateful tracking).

---

### 3.3 Component Interactions (Security Group Chain)

```
┌───────────────────────────────────────────────────────────────────┐
│                      Security Group Flow                          │
└───────────────────────────────────────────────────────────────────┘

Internet (0.0.0.0/0)
       │
       ▼ (HTTPS: 443, HTTP: 80)
┌─────────────────┐
│  ALB SG         │ Ingress: 443, 80 from 0.0.0.0/0
│                 │ Egress: 8000 to ECS SG
└────────┬────────┘
         │
         ▼ (HTTP: 8000)
┌─────────────────┐
│  ECS SG         │ Ingress: 8000 from ALB SG
│                 │ Egress: 5432 to Aurora SG
│                 │         6379 to ElastiCache SG
│                 │         443 to VPC Endpoint SG
└────┬────┬───┬───┘
     │    │   │
     │    │   ▼ (HTTPS: 443)
     │    │   ┌─────────────────┐
     │    │   │ VPC Endpoint SG │ Ingress: 443 from ECS SG, Lambda SG
     │    │   │                 │ Egress: None
     │    │   └─────────────────┘
     │    │           ↓
     │    │   AWS Services (ECR, Logs, Secrets, SES, SQS, etc.)
     │    │
     │    ▼ (Redis: 6379)
     │    ┌─────────────────┐
     │    │ ElastiCache SG  │ Ingress: 6379 from ECS SG
     │    │                 │ Egress: None
     │    └─────────────────┘
     │
     ▼ (PostgreSQL: 5432)
┌─────────────────┐
│  Aurora SG      │ Ingress: 5432 from ECS SG, Lambda SG
│                 │ Egress: None
└─────────────────┘
         ▲
         │ (PostgreSQL: 5432)
┌─────────────────┐
│  Lambda SG      │ Ingress: None (event-driven)
│                 │ Egress: 5432 to Aurora SG
│                 │         443 to VPC Endpoint SG
└─────────────────┘
         │
         ▼ (HTTPS: 443)
┌─────────────────┐
│ VPC Endpoint SG │ (same as above)
└─────────────────┘
```

**Defense in Depth Layers**:
1. Internet Layer: ALB SG (public ingress, controlled egress)
2. Application Layer: ECS SG, Lambda SG (controlled access to data and services)
3. Data Layer: Aurora SG, ElastiCache SG (no egress, ingress from app layer only)
4. Service Layer: VPC Endpoint SG (HTTPS from app layer only)

---

## 4. Private Connectivity Layer

### 4.1 Component Overview

**Purpose**: Enable private connectivity to AWS services without internet egress.

**Responsibilities**:
- Deploy VPC endpoints for all required AWS services
- Configure Multi-AZ deployment for high availability
- Enable private DNS for interface endpoints
- Optimize cost (use gateway endpoint for S3)

**NFR Patterns Implemented**:
- VPC Endpoint Pattern (NFR-3, SECURITY-04)
- VPC Endpoint Selection Pattern (NFR-12)
- Multi-AZ Pattern (NFR-1)

---

### 4.2 Sub-Components

#### 4.2.1 S3 Gateway Endpoint Component

**Domain Entities**: VPCEndpoint (1 instance, Gateway type)

**Purpose**: Enable private S3 access for ECR image pulls (ECS Fargate) without internet egress.

**Configuration**:
```yaml
S3GatewayEndpoint:
  service_name: "com.amazonaws.us-east-1.s3"
  endpoint_type: Gateway
  route_table_ids:
    - "rtb-private"  # Private route table only
  tags:
    Name: "zero2prod-s3-gateway-endpoint"
    Service: "s3"
    Cost: "Free"
```

**Use Cases**:
- ECR image pulls: ECS Fargate pulls container images from ECR (stored in S3)
- Future S3 access: Application can access S3 buckets without internet egress

**Cost**: Free (no hourly charge for gateway endpoints)

**Business Rules Enforced**:
- BR-6.1: S3 Gateway Endpoint Rule (use gateway, not interface)

---

#### 4.2.2 Interface Endpoints Component

**Domain Entities**: VPCEndpoint (7 instances, Interface type)

**Purpose**: Enable private access to AWS services that do not support gateway endpoints.

**Endpoints Required**:

1. **ECR API Endpoint**:
   ```yaml
   ECRAPIEndpoint:
     service_name: "com.amazonaws.us-east-1.ecr.api"
     endpoint_type: Interface
     subnet_ids: ["subnet-private-1a", "subnet-private-1b"]
     security_group_ids: ["sg-vpc-endpoints"]
     private_dns_enabled: true
     tags:
       Name: "zero2prod-ecr-api-endpoint"
       Service: "ecr-api"
   ```
   Use case: ECS Fargate retrieves container image metadata

2. **ECR DKR Endpoint**:
   ```yaml
   ECRDKREndpoint:
     service_name: "com.amazonaws.us-east-1.ecr.dkr"
     endpoint_type: Interface
     subnet_ids: ["subnet-private-1a", "subnet-private-1b"]
     security_group_ids: ["sg-vpc-endpoints"]
     private_dns_enabled: true
     tags:
       Name: "zero2prod-ecr-dkr-endpoint"
       Service: "ecr-dkr"
   ```
   Use case: ECS Fargate Docker registry access

3. **CloudWatch Logs Endpoint**:
   ```yaml
   LogsEndpoint:
     service_name: "com.amazonaws.us-east-1.logs"
     endpoint_type: Interface
     subnet_ids: ["subnet-private-1a", "subnet-private-1b"]
     security_group_ids: ["sg-vpc-endpoints"]
     private_dns_enabled: true
     tags:
       Name: "zero2prod-logs-endpoint"
       Service: "logs"
   ```
   Use case: ECS and Lambda send application logs to CloudWatch

4. **Secrets Manager Endpoint**:
   ```yaml
   SecretsManagerEndpoint:
     service_name: "com.amazonaws.us-east-1.secretsmanager"
     endpoint_type: Interface
     subnet_ids: ["subnet-private-1a", "subnet-private-1b"]
     security_group_ids: ["sg-vpc-endpoints"]
     private_dns_enabled: true
     tags:
       Name: "zero2prod-secretsmanager-endpoint"
       Service: "secretsmanager"
   ```
   Use case: ECS and Lambda retrieve database credentials and API keys

5. **STS Endpoint**:
   ```yaml
   STSEndpoint:
     service_name: "com.amazonaws.us-east-1.sts"
     endpoint_type: Interface
     subnet_ids: ["subnet-private-1a", "subnet-private-1b"]
     security_group_ids: ["sg-vpc-endpoints"]
     private_dns_enabled: true
     tags:
       Name: "zero2prod-sts-endpoint"
       Service: "sts"
   ```
   Use case: ECS and Lambda assume IAM roles (AWS SDK credential provider)

6. **SES Endpoint**:
   ```yaml
   SESEndpoint:
     service_name: "com.amazonaws.us-east-1.ses"
     endpoint_type: Interface
     subnet_ids: ["subnet-private-1a", "subnet-private-1b"]
     security_group_ids: ["sg-vpc-endpoints"]
     private_dns_enabled: true
     tags:
       Name: "zero2prod-ses-endpoint"
       Service: "ses"
   ```
   Use case: Lambda sends newsletter emails via Amazon SES

7. **SQS Endpoint**:
   ```yaml
   SQSEndpoint:
     service_name: "com.amazonaws.us-east-1.sqs"
     endpoint_type: Interface
     subnet_ids: ["subnet-private-1a", "subnet-private-1b"]
     security_group_ids: ["sg-vpc-endpoints"]
     private_dns_enabled: true
     tags:
       Name: "zero2prod-sqs-endpoint"
       Service: "sqs"
   ```
   Use case: ECS enqueues newsletter delivery tasks to SQS queue

**Cost per Interface Endpoint**: $7.20/month + data transfer ($0.01 per GB)

**Business Rules Enforced**:
- BR-2.5: VPC Endpoint Requirement Rule (deploy all 8 endpoints)
- BR-2.6: Interface Endpoint Multi-AZ Rule (deploy in both private subnets)
- BR-2.7: Private DNS for Interface Endpoints Rule (enabled for all)
- BR-6.2: Interface Endpoints for Services Without Gateway Support Rule

---

### 4.3 Component Interactions

```
┌───────────────────────────────────────────────────────────────────┐
│                    VPC Endpoint Architecture                      │
└───────────────────────────────────────────────────────────────────┘

ECS Task (Private Subnet 1a)
       │
       ▼ (Docker pull from ECR)
┌─────────────────┐
│  S3 Gateway EP  │ Route table-based, no ENI
│  (Free)         │ Routes: S3 Prefix List → Gateway EP
└─────────────────┘
       │
       ▼
AWS S3 (ECR image storage)


ECS Task (Private Subnet 1a)
       │
       ▼ (AWS SDK calls: Secrets Manager, SES, SQS, etc.)
┌─────────────────┐
│ Interface EP 1a │ ENI in Private Subnet 1a
│ (ECR, Logs,     │ Private DNS: Resolves AWS service DNS to private IP
│  Secrets, etc.) │ Security Group: Allow 443 from ECS SG, Lambda SG
└─────────────────┘
       │
       ▼
AWS PrivateLink → AWS Services


Lambda Function (Private Subnet 1b)
       │
       ▼ (AWS SDK calls: SES, Secrets Manager)
┌─────────────────┐
│ Interface EP 1b │ ENI in Private Subnet 1b
│ (SES, Secrets)  │ Private DNS: Resolves AWS service DNS to private IP
└─────────────────┘
       │
       ▼
AWS PrivateLink → AWS Services
```

**Private DNS Resolution Example**:
```
Application code: secrets_client.get_secret_value(SecretId="database/password")
DNS resolution: secretsmanager.us-east-1.amazonaws.com → 10.0.10.X (VPC endpoint private IP)
Connection: HTTPS to 10.0.10.X (within VPC, no internet egress)
AWS PrivateLink: Routes to Secrets Manager service
```

---

## 5. Observability Layer

### 5.1 Component Overview

**Purpose**: Provide visibility into network infrastructure health, performance, and cost.

**Responsibilities**:
- Monitor available IP addresses per subnet
- Track VPC endpoint data transfer costs
- Monitor ALB metrics (request count, latency, error rates)
- Tag all resources for cost allocation and management

**NFR Patterns Implemented**:
- CloudWatch Metrics for VPC Pattern (NFR-7, NFR-8)
- Tagging Strategy Pattern (NFR-12, NFR-15)

---

### 5.2 Sub-Components

#### 5.2.1 CloudWatch Metrics Component

**Purpose**: Monitor network infrastructure metrics.

**Metrics Collected**:

1. **Subnet Available IPs**:
   - Metric: `AvailableIPAddressCount` per subnet (AWS-provided)
   - Dashboard: Line chart showing available IPs over time
   - Alarm: Alert if available IPs < 50 (critical threshold)

2. **VPC Endpoint Data Processed**:
   - Metric: `DataProcessed` per interface endpoint (AWS-provided)
   - Dashboard: Bar chart showing monthly data per endpoint
   - Use case: Cost tracking and anomaly detection

3. **ALB Metrics** (application-level, included for completeness):
   - Metrics: `RequestCount`, `TargetResponseTime`, `HealthyHostCount`, `HTTPCode_Target_5XX_Count`
   - Dashboard: Operational dashboard includes ALB metrics
   - Alarms: Critical alerts for unhealthy targets and high error rates

**CloudWatch Dashboard**:
```yaml
NetworkDashboard:
  widgets:
    - metric: AvailableIPAddressCount
      subnets: ["subnet-public-1a", "subnet-public-1b", "subnet-private-1a", "subnet-private-1b"]
      visualization: Line chart
    - metric: DataProcessed
      endpoints: ["vpce-ecr-api", "vpce-logs", "vpce-secretsmanager", "vpce-ses", "vpce-sqs"]
      visualization: Bar chart
    - metric: HealthyHostCount
      alb: "zero2prod-alb"
      visualization: Gauge
```

---

#### 5.2.2 CloudWatch Alarms Component

**Purpose**: Alert on network infrastructure issues.

**Alarms Configured**:

1. **IP Exhaustion Alarm** (per subnet):
   ```yaml
   IPExhaustionAlarm:
     metric: AvailableIPAddressCount
     threshold: 50
     comparison: LessThanThreshold
     evaluation_periods: 2
     period: 300  # 5 minutes
     statistic: Average
     alarm_actions: ["sns-topic-arn"]
     alarm_description: "Alert if subnet available IPs < 50 (80% utilization)"
   ```

2. **VPC Endpoint Data Anomaly Alarm**:
   ```yaml
   VPCEndpointDataAnomalyAlarm:
     metric: DataProcessed
     threshold: 100  # GB per month
     comparison: GreaterThanThreshold
     evaluation_periods: 1
     period: 2592000  # 30 days
     statistic: Sum
     alarm_actions: ["sns-topic-arn"]
     alarm_description: "Alert if VPC endpoint data > 100 GB/month (cost warning)"
   ```

3. **ALB Unhealthy Targets Alarm** (application-level):
   ```yaml
   ALBUnhealthyTargetsAlarm:
     metric: UnHealthyHostCount
     threshold: 0
     comparison: GreaterThanThreshold
     evaluation_periods: 2
     period: 300  # 5 minutes
     statistic: Average
     alarm_actions: ["sns-topic-arn"]
     alarm_description: "Alert if ALB has unhealthy targets (service degradation)"
   ```

---

#### 5.2.3 Resource Tagging Component

**Purpose**: Tag all network resources for cost allocation and management.

**Tagging Strategy**:

**Required Tags** (all resources):
```yaml
tags:
  Name: "zero2prod-<resource-type>"
  Project: "zero2prod"
  Environment: "production"
  ManagedBy: "CDK"
  CostCenter: "network-infrastructure"
```

**Resource-Specific Tags**:

- **Subnets**: Add `Type: Public/Private` and `AZ: us-east-1a/us-east-1b`
- **Security Groups**: Add `Purpose: <resource-type> traffic`
- **VPC Endpoints**: Add `Service: <aws-service>` and `Cost: Free` (for gateway) or `Cost: $7.20/month` (for interface)

**Cost Allocation**:
- AWS Cost Explorer: Filter by `CostCenter=network-infrastructure`
- Monthly cost breakdown: VPC endpoints, data transfer, etc.
- Tag-based budgets: Alert if network costs exceed $60/month

**Business Rules Enforced**:
- BR-8.1: Security Group Rules Documentation Rule (tags document purpose)

---

### 5.3 Component Interactions

```
┌───────────────────────────────────────────────────────────────────┐
│                   Observability Flow                              │
└───────────────────────────────────────────────────────────────────┘

Network Resources (VPC, Subnets, Security Groups, VPC Endpoints)
       │
       ▼ (Metrics)
┌─────────────────┐
│ CloudWatch      │ Metrics: Available IPs, VPC EP data, ALB metrics
│ Metrics         │ Retention: 15 months (default)
└────────┬────────┘
         │
         ▼ (Evaluate)
┌─────────────────┐
│ CloudWatch      │ Alarms: IP exhaustion, data anomaly, unhealthy targets
│ Alarms          │ Actions: SNS notification
└────────┬────────┘
         │
         ▼ (Notify)
┌─────────────────┐
│ SNS Topic       │ Subscribers: Email, PagerDuty
│                 │ Critical: Page on-call
└─────────────────┘

┌─────────────────┐
│ Resource Tags   │ Cost allocation, resource management
│                 │ Filter: CostCenter=network-infrastructure
└─────────────────┘
       │
       ▼
┌─────────────────┐
│ AWS Cost        │ Monthly cost breakdown
│ Explorer        │ Budget alerts
└─────────────────┘
```

---

## Summary

This document defines 5 logical component layers with 17 sub-components:

1. **Network Layer** (4 components):
   - VPC Component
   - Public Subnet Component (2 subnets)
   - Private Subnet Component (2 subnets)
   - Internet Gateway Component

2. **Routing Layer** (2 components):
   - Public Route Table Component (default route to IGW)
   - Private Route Table Component (no default route, S3 gateway route)

3. **Security Layer** (6 components):
   - ALB Security Group Component
   - ECS Security Group Component
   - Aurora Security Group Component
   - ElastiCache Security Group Component
   - Lambda Security Group Component
   - VPC Endpoint Security Group Component

4. **Private Connectivity Layer** (2 components):
   - S3 Gateway Endpoint Component (free)
   - Interface Endpoints Component (7 endpoints: ECR API, ECR DKR, Logs, Secrets Manager, STS, SES, SQS)

5. **Observability Layer** (3 components):
   - CloudWatch Metrics Component (available IPs, VPC endpoint data, ALB metrics)
   - CloudWatch Alarms Component (IP exhaustion, data anomaly, unhealthy targets)
   - Resource Tagging Component (cost allocation, resource management)

**Key Architectural Decisions**:
- Private networking: No NAT Gateway, VPC endpoints only
- Multi-AZ deployment: All components redundant across 2 AZs
- Security group layering: Defense in depth with least-privilege rules
- Cost optimization: S3 Gateway Endpoint (free) instead of Interface Endpoint ($7.20/month)

**Next Steps**: Proceed to Security Hardening document to define security controls and compliance verification.

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-12  
**Status**: Ready for Review
