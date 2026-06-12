# Technology Stack - Unit 1: Network Infrastructure

## Overview

This document defines the technology stack and tooling decisions for Unit 1: Network Infrastructure. It specifies AWS services, infrastructure-as-code tools, versions, and justifications for technology choices.

**Unit Scope**: Network foundation including VPC, subnets, security groups, VPC endpoints, routing, and internet gateway.

**Document Date**: 2026-06-12  
**Unit Owner**: Network Infrastructure Team  
**Related Documents**:
- NFR Assessment: `/aidlc-docs/construction/unit-1-network/nfr-requirements/nfr-assessment.md`
- Functional Design: `/aidlc-docs/construction/unit-1-network/functional-design/`

---

## Technology Stack Summary

| Category | Technology | Version | Role | Justification |
|----------|-----------|---------|------|---------------|
| **Core Networking** | AWS VPC | N/A (managed service) | Network container | AWS native networking, highly available |
| **Core Networking** | AWS Subnets | N/A (managed service) | Network segmentation | Multi-AZ deployment for HA |
| **Core Networking** | AWS Security Groups | N/A (managed service) | Stateful firewall | Least-privilege access control |
| **Core Networking** | AWS Internet Gateway | N/A (managed service) | Public internet access | Enable ALB internet connectivity |
| **Core Networking** | AWS Route Tables | N/A (managed service) | Traffic routing | Control public/private routing |
| **Private Connectivity** | AWS VPC Endpoints (Gateway) | N/A (managed service) | S3 access without NAT | Free, high performance |
| **Private Connectivity** | AWS VPC Endpoints (Interface) | N/A (managed service) | AWS service access | Private connectivity, no NAT Gateway |
| **Infrastructure as Code** | AWS CDK | 2.x (latest stable) | Infrastructure provisioning | Type-safe, reusable constructs |
| **IaC Language** | Python | 3.11+ | CDK programming language | Team expertise, rich ecosystem |
| **Deployment Platform** | AWS CloudFormation | N/A (CDK backend) | Stack deployment | AWS-native, drift detection |
| **CI/CD Platform** | GitHub Actions | N/A (SaaS) | Deployment automation | Integrated with GitHub, OIDC auth |
| **Cost Tracking** | AWS Cost Explorer | N/A (managed service) | Cost monitoring | Track VPC endpoint costs |
| **Monitoring** | AWS CloudWatch | N/A (managed service) | Metrics and logging | Network metrics, alarms |

---

## 1. Core Networking Services

### 1.1 AWS VPC (Virtual Private Cloud)

**Version**: N/A (AWS-managed service)  
**Role**: Network isolation container for all AWS resources

**Key Features**:
- RFC 1918 private IP address space (`10.0.0.0/16`)
- DNS resolution and DNS hostnames support
- Multi-AZ subnet distribution
- Logically isolated from other VPCs

**Configuration**:
- CIDR Block: `10.0.0.0/16` (65,536 IP addresses)
- DNS Hostnames: Enabled (required for VPC endpoints)
- DNS Support: Enabled (required for DNS resolution)
- Tenancy: Default (shared hardware, cost-optimized)

**Why VPC?**
- **AWS Native**: First-class AWS service, deeply integrated with all AWS services
- **Well-Architected**: Supports security, reliability, and performance pillars
- **No Alternatives**: VPC is the only AWS networking foundation (no third-party alternatives)

**AWS SLA**: 99.99% (regional service)

**Cost**: Free (VPC itself has no charges, only VPC endpoints and data transfer)

---

### 1.2 AWS Subnets

**Version**: N/A (AWS-managed service)  
**Role**: Network segmentation within VPC, placed in specific Availability Zones

**Subnet Types**:

1. **Public Subnets** (2 subnets, 1 per AZ):
   - CIDR: `10.0.1.0/24` (AZ-A), `10.0.2.0/24` (AZ-B)
   - Purpose: Application Load Balancer (internet-facing)
   - Routing: Route table with default route to Internet Gateway
   - Auto-assign public IP: Enabled

2. **Private Subnets** (2 subnets, 1 per AZ):
   - CIDR: `10.0.10.0/24` (AZ-A), `10.0.11.0/24` (AZ-B)
   - Purpose: ECS tasks, Lambda functions, Aurora, ElastiCache, VPC endpoints
   - Routing: Route table with NO internet gateway (VPC endpoints only)
   - Auto-assign public IP: Disabled

**Subnet Sizing**:
- Size: `/24` (256 addresses per subnet)
- Usable IPs: 251 per subnet (AWS reserves 5 IPs: network, gateway, DNS, broadcast, future)
- Current utilization: ~10% (high headroom for growth)

**Multi-AZ Distribution**:
- Availability Zones: `us-east-1a`, `us-east-1b` (or configured region)
- Purpose: 99.9% availability (per NFR-1)
- Failure tolerance: Single AZ failure tolerated

**Why Multi-AZ?**
- **High Availability**: Resources remain available if 1 AZ fails
- **AWS Best Practice**: Multi-AZ is standard for production workloads
- **Cost-Effective**: Only 2 AZs needed for 99.9% availability (3 AZs for 99.99%)

---

### 1.3 AWS Security Groups

**Version**: N/A (AWS-managed service)  
**Role**: Stateful firewall controlling inbound and outbound traffic

**Security Group Architecture**:

| Security Group | Purpose | Ingress Rules | Egress Rules |
|----------------|---------|---------------|--------------|
| `zero2prod-alb-sg` | ALB traffic | HTTPS (443), HTTP (80) from internet | HTTP (8000) to ECS SG |
| `zero2prod-ecs-sg` | ECS task traffic | HTTP (8000) from ALB SG | PostgreSQL (5432) to Aurora SG, Redis (6379) to ElastiCache SG, HTTPS (443) to VPC Endpoint SG |
| `zero2prod-aurora-sg` | Aurora database | PostgreSQL (5432) from ECS SG, PostgreSQL (5432) from Lambda SG | None |
| `zero2prod-elasticache-sg` | ElastiCache Redis | Redis (6379) from ECS SG | None |
| `zero2prod-lambda-sg` | Lambda function | None (event-driven) | PostgreSQL (5432) to Aurora SG, HTTPS (443) to VPC Endpoint SG |
| `zero2prod-vpc-endpoints-sg` | VPC endpoints | HTTPS (443) from ECS SG, HTTPS (443) from Lambda SG | None |

**Key Features**:
- **Stateful**: Return traffic automatically allowed (no need for explicit return rules)
- **Least Privilege**: No `0.0.0.0/0` egress rules (except ALB, which is internet-facing)
- **Security Group Chaining**: Reference other security groups (not CIDR blocks) for tighter security
- **Rule Documentation**: Every rule has a `description` field (per SECURITY-05)

**Why Security Groups over Network ACLs?**
- **Simpler**: Stateful (automatic return traffic), easier to manage
- **More Secure**: Security groups are instance-level, Network ACLs are subnet-level
- **Sufficient**: Security groups provide adequate protection for this use case
- **AWS Best Practice**: Use security groups as primary security mechanism, Network ACLs optional

**No Network ACLs**:
- Decision: Use default Network ACL (allow all inbound/outbound)
- Rationale: Security groups provide sufficient protection, Network ACLs add unnecessary complexity

---

### 1.4 AWS Internet Gateway

**Version**: N/A (AWS-managed service)  
**Role**: Enable public subnets to send/receive internet traffic

**Key Features**:
- Horizontally scaled, redundant, highly available (AWS-managed)
- Supports inbound and outbound IPv4 traffic
- Attached to VPC (1 IGW per VPC)

**Configuration**:
- Attached to: VPC (`zero2prod-vpc`)
- Used by: Public route table only (private subnets have NO internet access)
- Purpose: ALB receives HTTPS requests from internet

**Why Internet Gateway?**
- **Required for ALB**: ALB is internet-facing, needs IGW for public traffic
- **AWS Native**: First-class AWS service, no alternatives
- **Free**: Internet Gateway has no hourly charges (only data transfer costs)

**Security Consideration**:
- Internet Gateway is ONLY in public route table (private subnets have NO route to IGW)
- This enforces private subnet isolation (per NFR-3)

---

### 1.5 AWS Route Tables

**Version**: N/A (AWS-managed service)  
**Role**: Control traffic routing between subnets, internet gateway, and VPC endpoints

**Route Table Architecture**:

**Public Route Table**:
- Routes:
  - `10.0.0.0/16` → `local` (VPC-internal traffic)
  - `0.0.0.0/0` → `igw-xxxxxxxx` (default route to internet)
- Associated Subnets: Public Subnet 1 (AZ-A), Public Subnet 2 (AZ-B)
- Purpose: Enable ALB to receive internet traffic

**Private Route Table**:
- Routes:
  - `10.0.0.0/16` → `local` (VPC-internal traffic only)
  - S3 prefix list → `vpce-s3-gateway` (AWS-managed route, added automatically)
- Associated Subnets: Private Subnet 1 (AZ-A), Private Subnet 2 (AZ-B)
- Purpose: Enforce private subnet isolation (NO internet egress)

**Why No NAT Gateway?**
- **Cost Optimization**: NAT Gateway costs $32/month per AZ ($64/month for 2 AZs)
- **Security**: Private subnets have NO internet egress (VPC endpoints only)
- **VPC Endpoints**: Provide AWS service access without NAT Gateway
- **Decision**: User selected "operations-first" approach, but VPC endpoints are cheaper than NAT Gateway

---

## 2. Private Connectivity

### 2.1 AWS VPC Endpoints (Gateway)

**Service**: Amazon S3  
**Endpoint Type**: Gateway Endpoint  
**Version**: N/A (AWS-managed service)

**Key Features**:
- Free (no hourly charges or per-GB charges)
- Highly available (AWS-managed, no single point of failure)
- Automatically adds route to private route table

**Configuration**:
- Service Name: `com.amazonaws.us-east-1.s3`
- Route Table: Private route table
- Purpose: ECR Docker image layers stored in S3 (image pulls without internet)

**Why Gateway Endpoint for S3?**
- **Cost-Effective**: Gateway endpoints are free (interface endpoints cost $7/month)
- **Performance**: Direct access to S3 via AWS backbone network
- **Sufficient**: S3 is the only AWS service that supports gateway endpoints in this project

**Use Case**:
- ECS Fargate pulls Docker images from ECR
- ECR stores image layers in S3
- Gateway endpoint enables private S3 access without NAT Gateway

---

### 2.2 AWS VPC Endpoints (Interface / PrivateLink)

**Service Count**: 7 interface endpoints  
**Endpoint Type**: Interface Endpoint (PrivateLink)  
**Version**: N/A (AWS-managed service)

**Interface Endpoints Required**:

| Endpoint | Service Name | Purpose | Consumers |
|----------|--------------|---------|-----------|
| ECR API | `com.amazonaws.us-east-1.ecr.api` | Fetch Docker image metadata | ECS Fargate |
| ECR DKR | `com.amazonaws.us-east-1.ecr.dkr` | Pull Docker images | ECS Fargate |
| CloudWatch Logs | `com.amazonaws.us-east-1.logs` | Send application logs | ECS, Lambda |
| Secrets Manager | `com.amazonaws.us-east-1.secretsmanager` | Retrieve credentials | ECS, Lambda |
| STS | `com.amazonaws.us-east-1.sts` | IAM role assumption | ECS, Lambda |
| SES | `com.amazonaws.us-east-1.ses` | Send emails | ECS, Lambda |
| SQS | `com.amazonaws.us-east-1.sqs` | Queue newsletter tasks | ECS (Lambda triggered by SQS) |

**Key Features**:
- **Private DNS**: Enabled (AWS service DNS names resolve to private VPC IPs)
- **Multi-AZ**: Each endpoint deployed in BOTH private subnets (HA)
- **Security Group**: Attached to VPC Endpoint Security Group (HTTPS from ECS and Lambda only)
- **ENIs**: 2 ENIs per endpoint (1 per AZ) = 14 ENIs total

**Configuration**:
- Subnets: Both private subnets (`10.0.10.0/24`, `10.0.11.0/24`)
- Security Group: `zero2prod-vpc-endpoints-sg` (HTTPS from ECS and Lambda)
- Private DNS: Enabled (required for AWS SDK compatibility)

**Cost Analysis**:
- Hourly charge: $0.01 per endpoint-hour = $7.20 per endpoint per month
- Total hourly cost: 7 endpoints × $7.20 = $50.40/month
- Data processing: $0.01 per GB (estimated 50 GB/month = $0.50/month)
- Total interface endpoint cost: ~$51/month

**Why Interface Endpoints?**
- **No Internet Egress**: Private subnets have NO NAT Gateway (per NFR-3)
- **Better Security**: All AWS API traffic stays within VPC (no public internet)
- **Cost Comparison**: Interface endpoints ($51/month) vs NAT Gateway ($64/month for 2 AZs) = Save $13/month
- **AWS Best Practice**: VPC endpoints are recommended for production workloads

**Alternative Considered: NAT Gateway**
- Cost: $32/month per AZ × 2 AZs = $64/month
- Data transfer: $0.045 per GB × 50 GB = $2.25/month
- Total: $66.25/month (more expensive than interface endpoints)
- Security: NAT Gateway provides internet egress (less secure than VPC endpoints)
- Decision: VPC endpoints preferred (cheaper, more secure)

---

## 3. Infrastructure as Code

### 3.1 AWS CDK (Cloud Development Kit)

**Version**: 2.x (latest stable)  
**Language**: Python 3.11+  
**Role**: Infrastructure-as-code framework for defining AWS resources

**Key Features**:
- **Type-Safe**: Python type hints enable IDE autocomplete and compile-time checks
- **Reusable Constructs**: L2 constructs provide high-level abstractions (e.g., `Vpc`, `SecurityGroup`)
- **Synthesizes to CloudFormation**: CDK generates CloudFormation templates (AWS-native deployment)
- **Cross-Stack References**: Export VPC ID, subnet IDs, security group IDs for other stacks

**CDK Construct Levels Used**:

| Construct Level | Description | Usage in Network Stack |
|-----------------|-------------|------------------------|
| L1 (CfnXxx) | Low-level CloudFormation resources | Rarely used (only for unsupported L2 features) |
| L2 (High-level) | Simplified abstractions with defaults | Primary level (Vpc, SecurityGroup, InterfaceVpcEndpoint) |
| L3 (Patterns) | Opinionated multi-resource patterns | Not used in network stack (too opinionated) |

**CDK Stack Structure**:
```python
# cdk/app.py
from aws_cdk import App
from network_stack import NetworkStack

app = App()
NetworkStack(app, "NetworkStack", env={...})
app.synth()
```

```python
# cdk/network_stack.py
from aws_cdk import Stack, aws_ec2 as ec2
from constructs import Construct

class NetworkStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        # VPC
        self.vpc = ec2.Vpc(self, "Vpc", cidr="10.0.0.0/16", ...)
        
        # Security Groups
        self.alb_sg = ec2.SecurityGroup(self, "AlbSg", vpc=self.vpc, ...)
        
        # VPC Endpoints
        self.secrets_manager_endpoint = ec2.InterfaceVpcEndpoint(
            self, "SecretsManagerEndpoint",
            vpc=self.vpc,
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            ...
        )
```

**Why AWS CDK over Alternatives?**

| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| **Terraform** | Multi-cloud, large ecosystem | Not AWS-native, state management complexity | Rejected (AWS-only project) |
| **CloudFormation (YAML)** | AWS-native, no tooling needed | Verbose, no type safety, no reusability | Rejected (CDK is better DX) |
| **Pulumi** | Multi-language, type-safe | Smaller ecosystem, commercial licensing | Rejected (CDK is AWS-official) |
| **AWS SAM** | Serverless-focused, simple | Limited to Lambda/API Gateway | Rejected (need full VPC control) |
| **AWS CDK (Python)** | Type-safe, reusable, AWS-official, team expertise | Learning curve | **SELECTED** |

**CDK Version Selection**:
- **CDK v1**: Deprecated (EOL June 2023)
- **CDK v2**: Stable, recommended (single package, faster iteration)
- **Decision**: CDK v2.x (latest stable)

**Python Version**:
- **Python 3.11+**: Modern syntax, improved type hints, better performance
- **Why Python?**: Team has Python expertise (over TypeScript)

---

### 3.2 AWS CloudFormation

**Version**: N/A (AWS-managed service, backend for CDK)  
**Role**: Stack deployment engine (generated by CDK)

**Key Features**:
- **Declarative**: Define desired state, CloudFormation handles provisioning
- **Rollback on Failure**: Automatic rollback if deployment fails
- **Change Sets**: Preview changes before deployment
- **Drift Detection**: Detect manual changes made outside CloudFormation

**CloudFormation Usage**:
- CDK synthesizes Python code to CloudFormation templates (JSON/YAML)
- `cdk deploy` deploys CloudFormation stacks
- `cdk diff` compares deployed stack with code (preview changes)

**Why CloudFormation (via CDK)?**
- **AWS Native**: First-class AWS service, deeply integrated
- **Idempotent**: Deploying same template multiple times has no effect
- **State Management**: CloudFormation tracks resource state (no separate state file like Terraform)
- **Rollback**: Automatic rollback on failure (safety net)

---

## 4. Deployment Automation

### 4.1 GitHub Actions

**Version**: N/A (GitHub-hosted SaaS)  
**Role**: CI/CD pipeline for automated infrastructure deployment

**Key Features**:
- **OIDC Authentication**: No long-lived AWS access keys (temporary credentials via OIDC)
- **Integrated with GitHub**: Trigger on push, PR, manual workflow dispatch
- **Matrix Builds**: Deploy to multiple environments (dev, staging, production)
- **Manual Approval**: Require approval for production deployments

**GitHub Actions Workflow (Network Stack)**:
```yaml
name: Deploy Network Stack

on:
  push:
    branches: [main]
    paths: ['cdk/network-stack/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsCDKRole
          aws-region: us-east-1
      - name: Install CDK
        run: npm install -g aws-cdk
      - name: Install Python dependencies
        run: pip install -r requirements.txt
      - name: CDK synth
        run: cdk synth NetworkStack
      - name: CDK diff
        run: cdk diff NetworkStack
      - name: Manual approval (production only)
        if: github.ref == 'refs/heads/main'
        uses: trstringer/manual-approval@v1
      - name: CDK deploy
        run: cdk deploy NetworkStack --require-approval never
```

**Why GitHub Actions over Alternatives?**

| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| **AWS CodePipeline** | AWS-native, integrated with CloudFormation | Complex setup, higher cost | Rejected (GitHub Actions simpler) |
| **Jenkins** | Flexible, self-hosted | Requires infrastructure, maintenance overhead | Rejected (prefer SaaS) |
| **GitLab CI** | Integrated with GitLab | Not using GitLab for source control | Rejected (using GitHub) |
| **GitHub Actions** | Integrated with GitHub, OIDC auth, free for public repos | GitHub-specific | **SELECTED** |

**OIDC Authentication**:
- **Why OIDC?**: No long-lived AWS access keys stored in GitHub secrets
- **How it works**: GitHub Actions requests temporary credentials from AWS STS via OIDC provider
- **IAM Role**: `GitHubActionsCDKRole` (trust relationship with GitHub OIDC provider)
- **Security**: Temporary credentials expire after 1 hour (reduced risk)

---

## 5. Monitoring and Observability

### 5.1 AWS CloudWatch

**Version**: N/A (AWS-managed service)  
**Role**: Metrics, logs, and alarms for network infrastructure

**Network Metrics**:

| Metric | Source | Purpose | Threshold |
|--------|--------|---------|-----------|
| Available IPs per subnet | VPC | Monitor IP exhaustion | < 100 (warning) |
| VPC endpoint data processed | VPC Endpoints | Cost tracking | > 100 GB/month (review) |
| ALB active connection count | ALB | Monitor traffic | N/A (informational) |
| ALB target response time | ALB | Monitor latency | > 200ms p95 (alert) |

**CloudWatch Logs**:
- ALB Access Logs: Sent to S3 bucket (not CloudWatch Logs, due to cost)
- VPC Flow Logs: Optional (not enabled in initial deployment, can add later)

**CloudWatch Alarms**:

| Alarm | Metric | Threshold | Action |
|-------|--------|-----------|--------|
| Subnet IP exhaustion | Available IPs | < 100 | Email network team |
| ALB unhealthy targets | Unhealthy target count | > 0 for 5 minutes | Page on-call |
| VPC endpoint cost spike | Data processed | > 100 GB/month | Email ops team |

**Why CloudWatch?**
- **AWS Native**: First-class integration with all AWS services
- **No Agent Needed**: VPC metrics automatically published
- **Built-in Dashboards**: Pre-built dashboards for VPC, ALB
- **No Alternatives**: CloudWatch is the only AWS-native monitoring service for VPC

---

### 5.2 AWS Cost Explorer

**Version**: N/A (AWS-managed service)  
**Role**: Cost monitoring and analysis for VPC endpoints

**Cost Tracking**:
- VPC endpoint hourly charges: $0.01 per endpoint-hour × 7 endpoints = $50.40/month
- VPC endpoint data processing: $0.01 per GB (estimated $0.50/month)
- Cross-AZ data transfer: $0.01 per GB (estimated $0.10/month)
- Total network cost: ~$51/month

**Cost Allocation Tags**:
- `Environment`: `production` (or `dev`, `staging`)
- `Project`: `zero2prod`
- `Component`: `network`
- `ManagedBy`: `CDK`

**Cost Optimization**:
- S3 Gateway Endpoint: Free (no per-GB charges)
- Interface endpoints cheaper than NAT Gateway ($51/month vs $66/month)
- No VPC Flow Logs (save $50+/month)

**Budget Alert**:
- Budget: $100/month (network infrastructure)
- Alert: Email if actual cost exceeds $100/month (forecast or actual)

---

## 6. Version Control and Documentation

### 6.1 Git (GitHub)

**Version**: 2.x (latest stable)  
**Role**: Version control for CDK code and documentation

**Repository Structure**:
```
zero2prod/
├── cdk/
│   ├── app.py (CDK app entry point)
│   ├── network_stack.py (Network infrastructure)
│   ├── cdk.json (CDK configuration)
│   └── requirements.txt (Python dependencies)
├── aidlc-docs/
│   └── construction/
│       └── unit-1-network/
│           ├── functional-design/
│           ├── nfr-requirements/
│           └── infrastructure-design/ (future)
└── .github/
    └── workflows/
        └── deploy-network.yml (GitHub Actions workflow)
```

**Branch Strategy**:
- `main`: Production-ready code (protected branch)
- `feature/*`: Feature development branches
- `hotfix/*`: Urgent fixes for production

**Pull Request Process**:
1. Create feature branch from `main`
2. Develop CDK code and documentation
3. Open pull request (requires 1 approval)
4. CI pipeline runs: CDK synth, CDK diff, unit tests
5. Merge to `main` after approval
6. GitHub Actions deploys to production (with manual approval)

---

## 7. Testing and Quality Assurance

### 7.1 CDK Unit Tests

**Framework**: pytest (Python testing framework)  
**Purpose**: Test CDK constructs generate correct CloudFormation templates

**Example Unit Test**:
```python
import aws_cdk as cdk
from aws_cdk.assertions import Template
from network_stack import NetworkStack

def test_vpc_created():
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    # Assert VPC is created
    template.resource_count_is("AWS::EC2::VPC", 1)
    
    # Assert VPC CIDR is correct
    template.has_resource_properties("AWS::EC2::VPC", {
        "CidrBlock": "10.0.0.0/16"
    })

def test_security_groups_created():
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    # Assert 6 security groups are created
    template.resource_count_is("AWS::EC2::SecurityGroup", 6)
```

**Test Coverage Target**: > 80% of custom CDK constructs

---

### 7.2 CDK Snapshot Tests

**Framework**: pytest + CDK assertions  
**Purpose**: Detect unintended CloudFormation template changes

**Snapshot Test Workflow**:
1. Generate CloudFormation template: `cdk synth`
2. Save template as snapshot: `template.snapshot.json`
3. On subsequent runs, compare generated template with snapshot
4. Fail if template changes unexpectedly (requires explicit snapshot update)

**Why Snapshot Tests?**
- **Detect Unintended Changes**: Catch accidental infrastructure modifications
- **Code Review**: Pull requests show CloudFormation template diffs
- **Safety Net**: Prevent breaking changes from being deployed

---

### 7.3 Integration Tests (Smoke Tests)

**Framework**: Python + boto3 (AWS SDK)  
**Purpose**: Verify deployed network infrastructure is functional

**Integration Test Cases**:

| Test Case | Verification Method | Expected Result |
|-----------|---------------------|-----------------|
| VPC created | `describe_vpcs()` | VPC ID exists, CIDR is `10.0.0.0/16` |
| Subnets created | `describe_subnets()` | 4 subnets exist (2 public, 2 private) |
| Security groups created | `describe_security_groups()` | 6 security groups exist |
| VPC endpoints created | `describe_vpc_endpoints()` | 8 endpoints exist (1 Gateway, 7 Interface) |
| Private DNS enabled | `describe_vpc_endpoints()` | Interface endpoints have `private_dns_enabled=true` |
| Route tables configured | `describe_route_tables()` | Public route has IGW, private route has no IGW |

**Example Integration Test**:
```python
import boto3

def test_vpc_endpoints_exist():
    ec2 = boto3.client('ec2', region_name='us-east-1')
    response = ec2.describe_vpc_endpoints()
    
    endpoints = response['VpcEndpoints']
    assert len(endpoints) == 8, f"Expected 8 endpoints, found {len(endpoints)}"
    
    # Verify S3 gateway endpoint exists
    s3_endpoints = [e for e in endpoints if 's3' in e['ServiceName'] and e['VpcEndpointType'] == 'Gateway']
    assert len(s3_endpoints) == 1, "S3 gateway endpoint not found"
    
    # Verify 7 interface endpoints exist
    interface_endpoints = [e for e in endpoints if e['VpcEndpointType'] == 'Interface']
    assert len(interface_endpoints) == 7, f"Expected 7 interface endpoints, found {len(interface_endpoints)}"
```

**When to Run**:
- After `cdk deploy` in CI/CD pipeline
- Manually after infrastructure changes
- Scheduled daily (verify no drift)

---

## 8. Alternative Technologies Considered

### 8.1 Networking Alternatives

| Alternative | Rationale for Rejection |
|-------------|-------------------------|
| **Transit Gateway** | Overkill for single VPC (used for multi-VPC connectivity) |
| **AWS PrivateLink (for custom services)** | Not needed (only AWS services, not custom services) |
| **AWS Network Firewall** | Overkill for this use case (security groups sufficient) |
| **AWS Direct Connect** | Not needed (no on-premises connectivity) |
| **AWS VPN** | Not needed (no on-premises connectivity) |

### 8.2 Infrastructure-as-Code Alternatives

| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| **Terraform** | Multi-cloud, large community | State management complexity, not AWS-native | Rejected |
| **Pulumi** | Type-safe, multi-language | Smaller ecosystem, commercial licensing | Rejected |
| **CloudFormation (YAML)** | AWS-native | Verbose, no type safety | Rejected (CDK is better) |
| **AWS SAM** | Serverless-focused | Limited to Lambda/API Gateway | Rejected |

### 8.3 CI/CD Alternatives

| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| **AWS CodePipeline** | AWS-native | Complex setup, higher cost | Rejected |
| **Jenkins** | Flexible | Requires infrastructure | Rejected (prefer SaaS) |
| **GitLab CI** | Integrated with GitLab | Not using GitLab | Rejected |

---

## 9. Version Matrix

| Technology | Version | EOL Date | Upgrade Path |
|------------|---------|----------|--------------|
| AWS CDK | 2.x (latest) | N/A (rolling releases) | `npm update -g aws-cdk` |
| Python | 3.11+ | Oct 2027 (Python 3.11) | Upgrade to Python 3.12+ when available |
| boto3 (AWS SDK) | Latest stable | N/A (rolling releases) | `pip install --upgrade boto3` |
| GitHub Actions | N/A (SaaS) | N/A | Automatic updates by GitHub |
| pytest | 7.x | N/A | `pip install --upgrade pytest` |

**Dependency Management**:
- CDK: `package.json` or global install via npm
- Python dependencies: `requirements.txt` (pinned versions)
- GitHub Actions: `actions/checkout@v3` (pinned to major version)

**Upgrade Strategy**:
- CDK: Upgrade to latest stable version quarterly (review release notes)
- Python: Upgrade to latest stable version annually (test in dev first)
- boto3: Upgrade monthly (AWS SDK has frequent updates)

---

## 10. Security Considerations

### 10.1 Network Security Technologies

| Technology | Purpose | Implementation |
|------------|---------|----------------|
| **TLS 1.2+** | Encrypt traffic in transit | ALB, Aurora, ElastiCache, VPC endpoints |
| **Security Groups** | Stateful firewall | Least-privilege rules (no `0.0.0.0/0` egress) |
| **VPC Endpoints** | Private AWS service access | No internet egress from private subnets |
| **Private Subnets** | Network isolation | No IGW/NAT Gateway route |
| **IAM Roles** | Authenticate ECS/Lambda to AWS services | No hardcoded credentials |

### 10.2 Secrets Management

| Secret Type | Storage | Access Method |
|-------------|---------|---------------|
| Database password | AWS Secrets Manager | VPC endpoint (Secrets Manager interface endpoint) |
| Redis URI | AWS Secrets Manager | VPC endpoint |
| HMAC secret | AWS Secrets Manager | VPC endpoint |
| IAM credentials | IAM Roles | STS (via VPC endpoint) |

**No Hardcoded Secrets**:
- CDK code references Secrets Manager ARNs, not secret values
- Secret values injected at runtime via ECS task environment variables

---

## 11. Cost Breakdown

### 11.1 Monthly Cost Estimate

| Component | Quantity | Unit Cost | Monthly Cost | Notes |
|-----------|----------|-----------|--------------|-------|
| VPC | 1 | Free | $0.00 | No charge for VPC itself |
| Subnets | 4 | Free | $0.00 | No charge for subnets |
| Internet Gateway | 1 | Free | $0.00 | No hourly charge (data transfer charged separately) |
| Security Groups | 6 | Free | $0.00 | No charge for security groups |
| Route Tables | 2 | Free | $0.00 | No charge for route tables |
| S3 Gateway Endpoint | 1 | Free | $0.00 | No charge for gateway endpoints |
| Interface Endpoints (hourly) | 7 | $0.01/hour | $50.40 | 7 endpoints × $7.20/month |
| Interface Endpoints (data) | 50 GB | $0.01/GB | $0.50 | Estimated data transfer |
| Cross-AZ Data Transfer | 10 GB | $0.01/GB | $0.10 | Estimated cross-AZ traffic |
| **Total** | - | - | **$51.00** | **Approximate monthly cost** |

### 11.2 Cost Optimization Opportunities

| Optimization | Savings | Trade-off |
|--------------|---------|-----------|
| Use S3 Gateway Endpoint (not Interface) | $7/month | None (gateway is better) |
| Use VPC endpoints (not NAT Gateway) | $15/month | None (endpoints are more secure) |
| No VPC Flow Logs | $50+/month | Reduced troubleshooting visibility (can enable later) |
| Single-AZ deployment | $25/month | Loss of high availability (not acceptable) |

---

## Summary

**Technology Stack**:
- **Networking**: AWS VPC, Subnets, Security Groups, Internet Gateway, Route Tables
- **Private Connectivity**: VPC Endpoints (1 Gateway, 7 Interface)
- **Infrastructure as Code**: AWS CDK 2.x (Python 3.11+)
- **Deployment**: GitHub Actions + AWS CloudFormation
- **Monitoring**: AWS CloudWatch + Cost Explorer

**Key Decisions**:
1. **AWS CDK over Terraform**: Type-safe, AWS-native, team expertise in Python
2. **VPC Endpoints over NAT Gateway**: Cheaper ($51/month vs $66/month), more secure
3. **Security Groups over Network ACLs**: Simpler, sufficient for requirements
4. **GitHub Actions over AWS CodePipeline**: Integrated with GitHub, OIDC auth
5. **Multi-AZ (2 AZs)**: Balance cost and availability (99.9% target)

**Cost**: ~$51/month (VPC endpoints only)

**Next Steps**:
- Proceed to NFR Design stage to define NFR implementation patterns
- Proceed to Infrastructure Design stage to implement CDK Python code
- Set up GitHub Actions CI/CD pipeline for automated deployment

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-12  
**Status**: Ready for Review
