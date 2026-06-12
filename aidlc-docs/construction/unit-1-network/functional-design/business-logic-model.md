# Business Logic Model - Unit 1: Network Infrastructure

## Overview

This document defines the functional business logic for the Network Infrastructure component. The network layer provides foundational connectivity, security, and isolation logic that enables all other components to communicate securely without internet egress.

**Scope**: WHAT the network does (functional logic), not HOW it's implemented (deferred to Infrastructure Design).

---

## 1. Network Topology Logic

### 1.1 VPC CIDR Calculation Logic

**Purpose**: Determine the IP address space for the entire VPC to ensure adequate addresses for all components.

**Inputs**:
- Number of Availability Zones (AZs): 2 (minimum for HA)
- Number of subnet types: 2 (public, private)
- Expected number of resources per subnet: ~250 per subnet
- Future growth factor: 2x (for scaling)

**Logic**:
1. **Calculate minimum addresses needed**:
   - Public subnets: 2 AZs × 250 addresses = 500 addresses
   - Private subnets: 2 AZs × 250 addresses = 500 addresses
   - Total minimum: 1,000 addresses
   - With 2x growth factor: 2,000 addresses

2. **Select VPC CIDR block**:
   - Required capacity: 2,000+ addresses
   - Selected CIDR: `10.0.0.0/16` (65,536 addresses)
   - Rationale: Provides 32x headroom for future expansion

3. **Validate CIDR block**:
   - Must be RFC 1918 private address space (10.0.0.0/8, 172.16.0.0/12, or 192.168.0.0/16)
   - Must not overlap with on-premises networks (if applicable)
   - Must support required number of subnets

**Outputs**:
- VPC CIDR Block: `10.0.0.0/16`
- Available address space: 65,536 addresses

**Business Rules Applied**:
- BR-1.1: VPC CIDR block must provide adequate IP space for all current and future resources

---

### 1.2 Subnet Sizing and Allocation Logic

**Purpose**: Divide VPC CIDR block into subnets optimized for specific resource types and availability zones.

**Inputs**:
- VPC CIDR: `10.0.0.0/16`
- Number of AZs: 2
- Subnet types: Public (ALB only), Private (ECS, Lambda, Aurora, ElastiCache)

**Logic**:

**Public Subnet Sizing**:
1. **Calculate ALB IP requirements**:
   - ALB nodes per AZ: 2-10 (AWS scales automatically)
   - Expected maximum ALB IPs per AZ: 20
   - Reserved AWS addresses per subnet: 5 (network, gateway, broadcast, DNS, future)
   - Total IPs needed per public subnet: 20 + 5 = 25 IPs
   - Selected subnet size: /24 (256 addresses) - 10x headroom

2. **Allocate public subnet CIDR blocks**:
   - Public Subnet 1 (AZ-A): `10.0.1.0/24` (256 addresses)
   - Public Subnet 2 (AZ-B): `10.0.2.0/24` (256 addresses)

**Private Subnet Sizing**:
1. **Calculate private resource IP requirements**:
   - ECS tasks: 10 max × 1 IP each = 10 IPs
   - Aurora instances: 2 (primary + standby) = 2 IPs
   - ElastiCache nodes: 2 (Multi-AZ) = 2 IPs
   - Lambda ENIs: 10 concurrent × 1 IP each = 10 IPs
   - VPC endpoint ENIs: 9 endpoints × 2 AZs × 1 IP = 18 IPs
   - Reserved AWS addresses: 5
   - Total IPs needed per private subnet: 10 + 2 + 2 + 10 + 18 + 5 = 47 IPs
   - Selected subnet size: /24 (256 addresses) - 5x headroom

2. **Allocate private subnet CIDR blocks**:
   - Private Subnet 1 (AZ-A): `10.0.10.0/24` (256 addresses)
   - Private Subnet 2 (AZ-B): `10.0.11.0/24` (256 addresses)

**Subnet Gap Logic**:
- Leave gaps between subnet ranges for future expansion
- Public subnets: `10.0.1.0/24` to `10.0.2.0/24`
- Private subnets: `10.0.10.0/24` to `10.0.11.0/24`
- Reserved for future: `10.0.3.0/24` to `10.0.9.0/24`, `10.0.12.0/24` to `10.0.255.0/24`

**Outputs**:
- 4 subnets created (2 public, 2 private)
- Each subnet has 256 usable IP addresses
- Future expansion capacity: 61,952 addresses available

**Business Rules Applied**:
- BR-1.2: Public subnets sized for ALB only
- BR-1.3: Private subnets sized for all application and data tier resources
- BR-1.4: Multi-AZ subnet distribution (1 subnet per type per AZ)

---

### 1.3 Availability Zone Distribution Logic

**Purpose**: Distribute subnets across multiple availability zones for high availability.

**Inputs**:
- Target availability: 99.9% (NFR-1)
- Minimum AZ count: 2 (for HA)
- Selected AWS region: us-east-1 (or configurable)

**Logic**:
1. **Determine AZ count**:
   - Minimum AZs for 99.9% availability: 2
   - Selected AZ count: 2 (cost-optimized for target availability)
   - AZs selected: `us-east-1a`, `us-east-1b`

2. **Distribute subnet types across AZs**:
   - Each subnet type deployed in each AZ
   - Public subnet in AZ-A and AZ-B
   - Private subnet in AZ-A and AZ-B

3. **AZ failure tolerance**:
   - If 1 AZ fails, remaining AZ can handle 100% of traffic
   - Resources in each AZ: ALB nodes, ECS tasks, Aurora instances, ElastiCache nodes

**Outputs**:
- 2 Availability Zones used
- Each AZ contains 1 public subnet and 1 private subnet
- AZ failure tolerance: 50% (1 of 2 AZs can fail)

**Business Rules Applied**:
- BR-1.5: Multi-AZ deployment required (minimum 2 AZs)

---

## 2. Routing Logic

### 2.1 Route Table Logic

**Purpose**: Control traffic flow between subnets, internet gateway, and VPC endpoints.

**Inputs**:
- Public subnets: `10.0.1.0/24`, `10.0.2.0/24`
- Private subnets: `10.0.10.0/24`, `10.0.11.0/24`
- Internet Gateway ID: (provisioned by infrastructure)
- VPC Endpoint IDs: (provisioned by infrastructure)

**Logic**:

**Public Route Table Logic**:
1. **Create public route table**:
   - Default route to Internet Gateway for outbound internet access
   - Local route to VPC CIDR (automatically added by AWS)

2. **Route entries**:
   - Destination: `0.0.0.0/0` → Target: Internet Gateway (IGW)
   - Destination: `10.0.0.0/16` → Target: local (VPC-internal traffic)

3. **Associate public subnets**:
   - Associate public subnet 1 (AZ-A) with public route table
   - Associate public subnet 2 (AZ-B) with public route table

**Private Route Table Logic**:
1. **Create private route table**:
   - NO route to Internet Gateway (private subnets have no internet egress)
   - NO NAT Gateway route (cost optimization, VPC endpoints used instead)
   - Local route to VPC CIDR (automatically added by AWS)

2. **Route entries**:
   - Destination: `10.0.0.0/16` → Target: local (VPC-internal traffic only)
   - Destination: `s3-prefix-list` → Target: S3 Gateway Endpoint (added automatically)

3. **Associate private subnets**:
   - Associate private subnet 1 (AZ-A) with private route table
   - Associate private subnet 2 (AZ-B) with private route table

**Outputs**:
- 2 route tables created (1 public, 1 private)
- Public subnets can reach internet via IGW
- Private subnets have NO internet access (VPC endpoints only)

**Business Rules Applied**:
- BR-2.1: Public subnets route traffic to Internet Gateway
- BR-2.2: Private subnets have NO internet egress (VPC endpoints only)
- BR-2.3: No NAT Gateway (cost optimization + security)

---

### 2.2 Internet Gateway Routing Logic

**Purpose**: Enable public subnets (ALB only) to receive inbound internet traffic and send outbound responses.

**Inputs**:
- VPC ID
- Public route table

**Logic**:
1. **Create Internet Gateway**:
   - Attach IGW to VPC
   - Enable inbound internet traffic to public subnets

2. **Configure default route**:
   - Add route `0.0.0.0/0` → IGW in public route table
   - This enables ALB in public subnets to receive HTTPS requests from internet

3. **Validate internet connectivity**:
   - Resources in public subnets can reach internet (ALB health checks)
   - Resources in private subnets CANNOT reach internet

**Outputs**:
- Internet Gateway attached to VPC
- Public subnets have internet access
- Private subnets have NO internet access

**Business Rules Applied**:
- BR-2.4: Only public subnets have internet gateway access

---

### 2.3 VPC Endpoint Routing Logic

**Purpose**: Enable private subnets to access AWS services (S3, ECR, SES, SQS, etc.) without internet egress.

**Inputs**:
- AWS services required: S3, ECR API, ECR DKR, CloudWatch Logs, Secrets Manager, STS, SES, SQS
- Private subnets: `10.0.10.0/24`, `10.0.11.0/24`
- Private route table

**Logic**:

**Gateway Endpoint Logic (S3)**:
1. **Create S3 Gateway Endpoint**:
   - Service: `com.amazonaws.us-east-1.s3`
   - Route Table: Private route table
   - Purpose: ECR image pulls from S3-backed registry

2. **Automatic route injection**:
   - AWS automatically adds S3 prefix list route to private route table
   - Destination: S3 prefix list → Target: S3 Gateway Endpoint
   - No additional routing logic needed

**Interface Endpoint Logic (ECR, Logs, Secrets Manager, STS, SES, SQS)**:
1. **Create interface endpoints for each service**:
   - Service: `com.amazonaws.us-east-1.ecr.api`
   - Service: `com.amazonaws.us-east-1.ecr.dkr`
   - Service: `com.amazonaws.us-east-1.logs`
   - Service: `com.amazonaws.us-east-1.secretsmanager`
   - Service: `com.amazonaws.us-east-1.sts`
   - Service: `com.amazonaws.us-east-1.ses`
   - Service: `com.amazonaws.us-east-1.sqs`

2. **Subnet placement**:
   - Each interface endpoint deployed in BOTH private subnets (AZ-A and AZ-B)
   - Total ENIs created: 7 services × 2 AZs = 14 ENIs

3. **DNS resolution logic**:
   - Enable private DNS for interface endpoints
   - AWS service DNS names resolve to private VPC endpoint IPs
   - Example: `secretsmanager.us-east-1.amazonaws.com` → `10.0.10.X` (private IP)

4. **Security group association**:
   - Attach VPC Endpoint Security Group to all interface endpoints
   - Allows inbound HTTPS (443) from ECS and Lambda security groups

**Endpoint Selection Logic**:
- **Why these endpoints?** Each service is used by application or infrastructure:
  - S3: ECR image layers stored in S3
  - ECR API: Fetch container image metadata
  - ECR DKR: Pull Docker images
  - CloudWatch Logs: Send application and Lambda logs
  - Secrets Manager: Retrieve database credentials, Redis URI, HMAC secret
  - STS: IAM role assumption for ECS tasks and Lambda
  - SES: Send transactional and newsletter emails
  - SQS: Queue newsletter delivery tasks

**Outputs**:
- 8 VPC endpoints created (1 Gateway, 7 Interface)
- Private subnets can access AWS services without internet
- DNS resolution for AWS services points to private VPC endpoint IPs

**Business Rules Applied**:
- BR-2.5: VPC endpoints required for all AWS services used by application
- BR-2.6: Interface endpoints deployed in all private subnets (Multi-AZ)
- BR-2.7: Private DNS enabled for interface endpoints

---

## 3. Security Group Rule Logic

### 3.1 ALB Security Group Logic

**Purpose**: Control inbound traffic to Application Load Balancer (public internet → ALB) and outbound traffic to ECS tasks.

**Inputs**:
- ALB placement: Public subnets
- Client IP range: `0.0.0.0/0` (public internet)
- ECS task security group ID

**Ingress Rules Logic**:
1. **HTTPS from internet**:
   - Protocol: TCP
   - Port: 443
   - Source: `0.0.0.0/0` (any public IP)
   - Rationale: Allow public users to access web application via HTTPS

2. **HTTP redirect (optional)**:
   - Protocol: TCP
   - Port: 80
   - Source: `0.0.0.0/0`
   - Rationale: Redirect HTTP to HTTPS (301 redirect)

**Egress Rules Logic**:
1. **Outbound to ECS tasks**:
   - Protocol: TCP
   - Port: 8000 (application container port)
   - Destination: ECS Security Group
   - Rationale: ALB forwards requests to ECS tasks

**Outputs**:
- ALB Security Group with 2 ingress rules (443, 80) and 1 egress rule (8000 → ECS)

**Business Rules Applied**:
- BR-3.1: ALB accepts HTTPS from internet (0.0.0.0/0)
- BR-3.2: ALB can only send traffic to ECS security group (least privilege)

---

### 3.2 ECS Security Group Logic

**Purpose**: Control inbound traffic to ECS tasks (from ALB only) and outbound traffic to Aurora, ElastiCache, and VPC endpoints.

**Inputs**:
- ECS task placement: Private subnets
- ALB security group ID
- Aurora security group ID
- ElastiCache security group ID
- VPC Endpoint security group ID

**Ingress Rules Logic**:
1. **HTTP from ALB**:
   - Protocol: TCP
   - Port: 8000 (application container port)
   - Source: ALB Security Group
   - Rationale: Only ALB can send traffic to ECS tasks (no direct internet access)

**Egress Rules Logic**:
1. **PostgreSQL to Aurora**:
   - Protocol: TCP
   - Port: 5432
   - Destination: Aurora Security Group
   - Rationale: ECS tasks query database

2. **Redis to ElastiCache**:
   - Protocol: TCP
   - Port: 6379
   - Destination: ElastiCache Security Group
   - Rationale: ECS tasks access session cache

3. **HTTPS to VPC endpoints**:
   - Protocol: TCP
   - Port: 443
   - Destination: VPC Endpoint Security Group
   - Rationale: ECS tasks access AWS services (Secrets Manager, SES, SQS)

**Outputs**:
- ECS Security Group with 1 ingress rule (8000 from ALB) and 3 egress rules (5432, 6379, 443)

**Business Rules Applied**:
- BR-3.3: ECS tasks accept traffic ONLY from ALB (no direct access)
- BR-3.4: ECS tasks can access Aurora, ElastiCache, and VPC endpoints (least privilege)

---

### 3.3 Aurora Security Group Logic

**Purpose**: Control inbound traffic to Aurora PostgreSQL (from ECS and Lambda only).

**Inputs**:
- Aurora placement: Private subnets
- ECS security group ID
- Lambda security group ID

**Ingress Rules Logic**:
1. **PostgreSQL from ECS**:
   - Protocol: TCP
   - Port: 5432
   - Source: ECS Security Group
   - Rationale: ECS tasks query database for application logic

2. **PostgreSQL from Lambda**:
   - Protocol: TCP
   - Port: 5432
   - Source: Lambda Security Group
   - Rationale: Lambda function queries database for newsletter content

**Egress Rules Logic**:
- NO egress rules needed (Aurora does not initiate outbound connections)

**Outputs**:
- Aurora Security Group with 2 ingress rules (5432 from ECS, 5432 from Lambda) and 0 egress rules

**Business Rules Applied**:
- BR-3.5: Aurora accepts connections ONLY from ECS and Lambda (no direct access)

---

### 3.4 ElastiCache Security Group Logic

**Purpose**: Control inbound traffic to ElastiCache Redis (from ECS only).

**Inputs**:
- ElastiCache placement: Private subnets
- ECS security group ID

**Ingress Rules Logic**:
1. **Redis from ECS**:
   - Protocol: TCP
   - Port: 6379
   - Source: ECS Security Group
   - Rationale: ECS tasks access session cache

**Egress Rules Logic**:
- NO egress rules needed (ElastiCache does not initiate outbound connections)

**Outputs**:
- ElastiCache Security Group with 1 ingress rule (6379 from ECS) and 0 egress rules

**Business Rules Applied**:
- BR-3.6: ElastiCache accepts connections ONLY from ECS (no Lambda access needed)

---

### 3.5 Lambda Security Group Logic

**Purpose**: Control outbound traffic from Lambda function (to Aurora, VPC endpoints) and prevent inbound connections.

**Inputs**:
- Lambda placement: Private subnets
- Aurora security group ID
- VPC Endpoint security group ID

**Ingress Rules Logic**:
- NO ingress rules (Lambda invoked by SQS trigger, not by network traffic)

**Egress Rules Logic**:
1. **PostgreSQL to Aurora**:
   - Protocol: TCP
   - Port: 5432
   - Destination: Aurora Security Group
   - Rationale: Lambda function queries database for newsletter content

2. **HTTPS to VPC endpoints**:
   - Protocol: TCP
   - Port: 443
   - Destination: VPC Endpoint Security Group
   - Rationale: Lambda accesses SES, Secrets Manager, CloudWatch Logs

**Outputs**:
- Lambda Security Group with 0 ingress rules and 2 egress rules (5432, 443)

**Business Rules Applied**:
- BR-3.7: Lambda has NO ingress rules (event-driven, not network-triggered)
- BR-3.8: Lambda can access Aurora and VPC endpoints (least privilege)

---

### 3.6 VPC Endpoint Security Group Logic

**Purpose**: Control inbound traffic to VPC endpoints (from ECS and Lambda only).

**Inputs**:
- VPC endpoint placement: Private subnets
- ECS security group ID
- Lambda security group ID

**Ingress Rules Logic**:
1. **HTTPS from ECS**:
   - Protocol: TCP
   - Port: 443
   - Source: ECS Security Group
   - Rationale: ECS tasks access VPC endpoints

2. **HTTPS from Lambda**:
   - Protocol: TCP
   - Port: 443
   - Source: Lambda Security Group
   - Rationale: Lambda function accesses VPC endpoints

**Egress Rules Logic**:
- NO egress rules needed (VPC endpoints do not initiate outbound connections)

**Outputs**:
- VPC Endpoint Security Group with 2 ingress rules (443 from ECS, 443 from Lambda) and 0 egress rules

**Business Rules Applied**:
- BR-3.9: VPC endpoints accept connections ONLY from ECS and Lambda

---

## 4. IP Address Allocation Strategy

### 4.1 Static vs Dynamic IP Allocation Logic

**Purpose**: Determine which resources require static IPs vs dynamic IPs.

**Logic**:

**Static IP Allocation**:
- NONE - All resources use dynamic IPs assigned by AWS
- Rationale: AWS services (ALB, ECS, Aurora, ElastiCache, Lambda) use DNS-based service discovery

**Dynamic IP Allocation**:
- ALB nodes: Dynamic IPs (AWS manages)
- ECS tasks: Dynamic IPs (assigned from private subnet pool)
- Aurora instances: Dynamic IPs (DNS endpoint resolves to current primary)
- ElastiCache nodes: Dynamic IPs (DNS endpoint resolves to current nodes)
- Lambda ENIs: Dynamic IPs (AWS manages)
- VPC Endpoint ENIs: Dynamic IPs (private DNS resolves to endpoint IPs)

**DNS-Based Service Discovery**:
- All inter-service communication uses DNS names, not IP addresses
- Example: ECS task connects to Aurora via `cluster-endpoint.region.rds.amazonaws.com`
- Example: ECS task connects to ElastiCache via `cache-endpoint.region.cache.amazonaws.com`
- Example: ECS task accesses Secrets Manager via `secretsmanager.region.amazonaws.com` (resolves to VPC endpoint IP)

**Outputs**:
- 0 static IPs allocated
- All IPs dynamically assigned by AWS
- DNS-based service discovery used for all connections

**Business Rules Applied**:
- BR-4.1: No static IPs required (DNS-based service discovery)

---

### 4.2 IP Address Exhaustion Prevention Logic

**Purpose**: Monitor and prevent IP address exhaustion in subnets.

**Logic**:
1. **Calculate IP usage per subnet**:
   - Public subnets: 10 IPs used (ALB nodes) / 256 available = 4% utilization
   - Private subnets: 47 IPs used (ECS, Aurora, ElastiCache, Lambda, VPC endpoints) / 256 available = 18% utilization

2. **IP exhaustion threshold**:
   - Warning threshold: 70% utilization
   - Critical threshold: 85% utilization
   - Action: Expand subnet CIDR or add new subnets

3. **IP allocation monitoring**:
   - CloudWatch metric: Available IPs per subnet
   - Alarm: Trigger if available IPs < 50

**Outputs**:
- Current IP utilization: 4% (public), 18% (private)
- IP exhaustion risk: LOW
- Monitoring: CloudWatch alarm on available IPs

**Business Rules Applied**:
- BR-4.2: Monitor IP usage to prevent exhaustion

---

## 5. Network ACL Logic (Optional)

### 5.1 Network ACL vs Security Group Decision Logic

**Purpose**: Determine if Network ACLs (stateless) are needed in addition to Security Groups (stateful).

**Logic**:
1. **Evaluate security requirements**:
   - Current security posture: Security Groups (stateful) provide sufficient protection
   - Network ACLs (stateless): Add complexity, require managing inbound and outbound rules separately
   - Decision: Use Security Groups ONLY (simpler, sufficient for requirements)

2. **Network ACL default behavior**:
   - Default Network ACL: Allow all inbound and outbound traffic (AWS default)
   - Custom Network ACLs: NOT created (unnecessary complexity)

**Outputs**:
- Network ACLs: Default ACL used (allow all)
- Security Groups: Primary security enforcement mechanism

**Business Rules Applied**:
- BR-5.1: Security Groups are primary security mechanism (Network ACLs optional)

---

## 6. VPC Endpoint Selection Logic

### 6.1 Endpoint Type Decision Logic (Gateway vs Interface)

**Purpose**: Determine which VPC endpoint type to use for each AWS service.

**Inputs**:
- AWS service: S3, ECR, CloudWatch Logs, Secrets Manager, STS, SES, SQS

**Logic**:

**Gateway Endpoint Decision**:
1. **S3 Gateway Endpoint**:
   - Service: S3
   - Type: Gateway endpoint (free, no hourly charges)
   - Rationale: S3 supports gateway endpoints, cost-effective
   - Use case: ECR image layers stored in S3

**Interface Endpoint Decision**:
1. **Services requiring interface endpoints**:
   - ECR API, ECR DKR, CloudWatch Logs, Secrets Manager, STS, SES, SQS
   - Type: Interface endpoint (PrivateLink, hourly charge per endpoint)
   - Rationale: These services do NOT support gateway endpoints
   - Cost: ~$7/month per endpoint × 7 endpoints = ~$49/month

2. **Cost vs benefit analysis**:
   - Alternative: NAT Gateway ($32/month + data transfer)
   - Interface endpoints: $49/month (no data transfer charges to AWS services)
   - Decision: Interface endpoints (higher upfront cost, better security, no NAT Gateway needed)

**Outputs**:
- 1 Gateway endpoint (S3)
- 7 Interface endpoints (ECR API, ECR DKR, Logs, Secrets Manager, STS, SES, SQS)

**Business Rules Applied**:
- BR-6.1: Use gateway endpoints for S3 (cost-effective)
- BR-6.2: Use interface endpoints for services without gateway support
- BR-6.3: No NAT Gateway (VPC endpoints provide AWS service access)

---

### 6.2 VPC Endpoint Dependency Logic

**Purpose**: Identify which VPC endpoints are required for each application component.

**Inputs**:
- Application components: ECS tasks, Lambda function

**Logic**:

**ECS Task Endpoint Dependencies**:
1. **Container image pull**:
   - ECR API endpoint: Fetch image metadata
   - ECR DKR endpoint: Pull Docker image layers
   - S3 endpoint: Retrieve image layers from S3-backed registry

2. **Application runtime**:
   - Secrets Manager endpoint: Retrieve database credentials, Redis URI, HMAC secret
   - STS endpoint: Assume IAM task role
   - Logs endpoint: Send application logs to CloudWatch Logs
   - SES endpoint: Send confirmation emails
   - SQS endpoint: Enqueue newsletter delivery tasks

**Lambda Function Endpoint Dependencies**:
1. **Lambda runtime**:
   - Secrets Manager endpoint: Retrieve database credentials
   - STS endpoint: Assume IAM execution role
   - Logs endpoint: Send Lambda logs to CloudWatch Logs
   - SES endpoint: Send newsletter emails

**Dependency Matrix**:
| VPC Endpoint | ECS Tasks | Lambda Function |
|--------------|-----------|-----------------|
| S3 (Gateway) | Required (ECR) | Not needed |
| ECR API | Required | Not needed |
| ECR DKR | Required | Not needed |
| CloudWatch Logs | Required | Required |
| Secrets Manager | Required | Required |
| STS | Required | Required |
| SES | Required | Required |
| SQS | Required | Not needed (triggered by SQS, not accessing SQS API) |

**Outputs**:
- 8 VPC endpoints required
- ECS dependencies: 8 endpoints
- Lambda dependencies: 4 endpoints

**Business Rules Applied**:
- BR-6.4: VPC endpoints required for all AWS services used by application

---

## Summary

This business logic model defines the functional WHAT of the network infrastructure:

1. **Network Topology Logic**: VPC CIDR calculation, subnet sizing, AZ distribution
2. **Routing Logic**: Route tables, internet gateway routing, VPC endpoint routing
3. **Security Group Rule Logic**: 6 security groups with least-privilege rules
4. **IP Address Allocation Strategy**: Dynamic IPs, DNS-based service discovery, exhaustion prevention
5. **Network ACL Logic**: Security Groups only (Network ACLs optional)
6. **VPC Endpoint Selection Logic**: Gateway vs interface endpoints, endpoint dependencies

**Key Functional Capabilities**:
- Private subnet architecture with NO internet egress (VPC endpoints only)
- Multi-AZ high availability (2 AZs)
- Least-privilege security groups (restrict traffic to known sources)
- DNS-based service discovery (no static IPs)
- Cost-optimized (VPC endpoints instead of NAT Gateway)

**Next Steps**: Infrastructure Design will define HOW these functional requirements are implemented using AWS CDK Python.

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-12  
**Status**: Ready for Review
