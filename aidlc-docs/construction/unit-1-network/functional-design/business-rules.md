# Business Rules - Unit 1: Network Infrastructure

## Overview

This document defines the business rules that govern the network infrastructure design and implementation. These rules enforce security, availability, cost optimization, and operational requirements.

**Rule Enforcement**: All rules are MANDATORY constraints that must be validated during Infrastructure Design and Code Generation.

---

## 1. VPC Configuration Rules

### BR-1.1: VPC CIDR Block Rule

**Rule**: VPC CIDR block MUST provide adequate IP address space for all current and future resources with minimum 2x growth capacity.

**Rationale**: Prevents IP address exhaustion as application scales.

**Specific Requirements**:
- Minimum CIDR block: `/16` (65,536 addresses)
- Recommended CIDR: `10.0.0.0/16` (AWS best practice for private VPCs)
- Must not overlap with on-premises networks (if applicable)

**Validation**:
- Calculate total IP requirements: (Number of AZs × Resources per AZ × 2x growth factor)
- Verify CIDR block provides sufficient addresses
- Confirm CIDR is RFC 1918 private address space

**Consequences of Violation**:
- IP address exhaustion
- Cannot add new resources (ECS tasks, Lambda functions)
- Requires VPC migration (high-risk, high-effort)

**Mapped Requirements**: NFR-11 (Scalability), NFR-3 (Network Isolation)

---

### BR-1.2: Public Subnet Sizing Rule

**Rule**: Public subnets MUST be sized ONLY for Application Load Balancer (ALB) nodes with minimum `/24` CIDR per subnet.

**Rationale**: Public subnets have internet access, minimize attack surface by restricting to ALB only.

**Specific Requirements**:
- Public subnet size: `/24` (256 addresses per subnet)
- Public subnet count: 2 (one per AZ for Multi-AZ ALB)
- Resources allowed in public subnets: ALB ONLY (no EC2, ECS, Lambda, databases)

**Validation**:
- Verify public subnet CIDR is `/24` or larger
- Confirm no resources other than ALB deployed in public subnets

**Consequences of Violation**:
- Increased attack surface (resources with direct internet access)
- Security audit failure
- Violates least-privilege security principle

**Mapped Requirements**: NFR-3 (Network Isolation), SECURITY-04 (Private Networking)

---

### BR-1.3: Private Subnet Sizing Rule

**Rule**: Private subnets MUST be sized to accommodate ECS tasks, Lambda ENIs, Aurora instances, ElastiCache nodes, and VPC endpoint ENIs with minimum `/24` CIDR per subnet.

**Rationale**: Private subnets host all application and data tier resources, require sufficient IP space.

**Specific Requirements**:
- Private subnet size: `/24` (256 addresses per subnet)
- Private subnet count: 2 (one per AZ for Multi-AZ deployment)
- Resources in private subnets: ECS, Lambda, Aurora, ElastiCache, VPC endpoints

**Validation**:
- Calculate IP requirements: ECS tasks + Lambda ENIs + Aurora instances + ElastiCache nodes + VPC endpoint ENIs + 5 AWS reserved
- Verify private subnet CIDR provides sufficient addresses

**Consequences of Violation**:
- IP address exhaustion in private subnets
- Cannot scale ECS tasks or Lambda concurrency
- Cannot add new VPC endpoints

**Mapped Requirements**: NFR-11 (Scalability), NFR-3 (Network Isolation)

---

### BR-1.4: Multi-AZ Subnet Distribution Rule

**Rule**: Each subnet type (public, private) MUST be deployed in ALL availability zones (minimum 2 AZs) for high availability.

**Rationale**: Enables application to survive single AZ failure.

**Specific Requirements**:
- Minimum AZ count: 2
- Public subnets: 1 per AZ (2 total)
- Private subnets: 1 per AZ (2 total)
- Total subnets: 4 (2 public + 2 private)

**Validation**:
- Verify each AZ has 1 public subnet and 1 private subnet
- Confirm resources distributed across all AZs

**Consequences of Violation**:
- Single point of failure (1 AZ failure causes total outage)
- Does not meet 99.9% availability target (NFR-1)

**Mapped Requirements**: NFR-1 (High Availability)

---

### BR-1.5: Multi-AZ Deployment Rule

**Rule**: All infrastructure components (ALB, ECS, Aurora, ElastiCache, VPC endpoints) MUST be deployed across multiple availability zones (minimum 2 AZs).

**Rationale**: Provides fault tolerance and high availability.

**Specific Requirements**:
- ALB: Nodes in multiple AZs (AWS automatic)
- ECS: Tasks spread across multiple AZs
- Aurora: Multi-AZ with automatic failover
- ElastiCache: Multi-AZ replication
- VPC Interface Endpoints: ENIs in all AZs

**Validation**:
- Verify each component has presence in at least 2 AZs
- Test AZ failure scenario (simulate AZ failure, verify service continuity)

**Consequences of Violation**:
- Single AZ failure causes service outage
- Does not meet 99.9% availability SLA

**Mapped Requirements**: NFR-1 (High Availability)

---

## 2. Routing Rules

### BR-2.1: Public Subnet Internet Routing Rule

**Rule**: Public subnets MUST have a default route (`0.0.0.0/0`) to Internet Gateway to enable inbound internet traffic to ALB.

**Rationale**: ALB in public subnets must receive HTTPS requests from public internet.

**Specific Requirements**:
- Public route table: Route `0.0.0.0/0` → Internet Gateway
- Public route table: Route `10.0.0.0/16` → local (VPC-internal traffic)
- Public subnets: Associated with public route table

**Validation**:
- Verify public route table has default route to IGW
- Test inbound internet connectivity to ALB

**Consequences of Violation**:
- ALB cannot receive internet traffic
- Application inaccessible to public users

**Mapped Requirements**: FR-7 (Public API Endpoints)

---

### BR-2.2: Private Subnet NO Internet Egress Rule

**Rule**: Private subnets MUST NOT have any route to Internet Gateway or NAT Gateway (no internet egress).

**Rationale**: Highest security posture, prevents data exfiltration, reduces attack surface.

**Specific Requirements**:
- Private route table: NO route to Internet Gateway
- Private route table: NO route to NAT Gateway
- Private route table: Route `10.0.0.0/16` → local (VPC-internal traffic only)
- Private route table: S3 prefix list → S3 Gateway Endpoint (automatic)

**Validation**:
- Verify private route table has NO default route
- Test that resources in private subnets CANNOT reach internet

**Consequences of Violation**:
- Security audit failure
- Violates NFR-3 (Network Isolation) highest security tier
- Increased risk of data exfiltration

**Mapped Requirements**: NFR-3 (Network Isolation), SECURITY-04 (Private Networking)

---

### BR-2.3: No NAT Gateway Rule

**Rule**: VPC MUST NOT deploy NAT Gateway (cost optimization and security).

**Rationale**: VPC endpoints provide AWS service access without internet egress, saving $32/month + data transfer costs.

**Specific Requirements**:
- NAT Gateway: NOT deployed
- AWS service access: Via VPC endpoints ONLY
- Internet access: Public subnets via Internet Gateway ONLY

**Validation**:
- Verify no NAT Gateway exists in VPC
- Confirm private subnets can access AWS services via VPC endpoints

**Consequences of Violation**:
- Increased monthly cost ($32/month per NAT Gateway + data transfer)
- Lower security (NAT Gateway provides internet egress)

**Mapped Requirements**: NFR-3 (Network Isolation), NFR-12 (Cost Optimization)

---

### BR-2.4: Public Subnet Internet Gateway Access Rule

**Rule**: ONLY public subnets MAY have Internet Gateway access, all other subnets MUST use VPC endpoints for AWS service access.

**Rationale**: Minimize attack surface by limiting internet access to ALB only.

**Specific Requirements**:
- Internet Gateway: Attached to VPC
- Internet Gateway routes: ONLY in public route table
- Private subnets: NO routes to Internet Gateway

**Validation**:
- Verify only public route table has IGW route
- Verify private route table has NO IGW route

**Consequences of Violation**:
- Security audit failure
- Increased attack surface

**Mapped Requirements**: NFR-3 (Network Isolation), SECURITY-04 (Private Networking)

---

### BR-2.5: VPC Endpoint Requirement Rule

**Rule**: VPC MUST deploy VPC endpoints for ALL AWS services used by application (S3, ECR, CloudWatch Logs, Secrets Manager, STS, SES, SQS).

**Rationale**: Enable private subnet resources to access AWS services without internet egress.

**Specific Requirements**:
- Required VPC endpoints (8 total):
  1. `com.amazonaws.region.s3` (Gateway endpoint)
  2. `com.amazonaws.region.ecr.api` (Interface endpoint)
  3. `com.amazonaws.region.ecr.dkr` (Interface endpoint)
  4. `com.amazonaws.region.logs` (Interface endpoint)
  5. `com.amazonaws.region.secretsmanager` (Interface endpoint)
  6. `com.amazonaws.region.sts` (Interface endpoint)
  7. `com.amazonaws.region.ses` (Interface endpoint)
  8. `com.amazonaws.region.sqs` (Interface endpoint)

**Validation**:
- Verify all 8 VPC endpoints deployed
- Test connectivity from private subnets to each AWS service

**Consequences of Violation**:
- Resources in private subnets cannot access AWS services
- Application cannot retrieve secrets, send emails, enqueue messages
- ECS tasks cannot pull container images

**Mapped Requirements**: NFR-3 (Network Isolation), SECURITY-04 (Private Networking)

---

### BR-2.6: Interface Endpoint Multi-AZ Rule

**Rule**: ALL interface VPC endpoints MUST be deployed in ALL private subnets (one ENI per AZ) for high availability.

**Rationale**: Endpoint failure in one AZ should not affect resources in other AZs.

**Specific Requirements**:
- Interface endpoints: 7 (ECR API, ECR DKR, Logs, Secrets Manager, STS, SES, SQS)
- ENIs per endpoint: 2 (one per private subnet in each AZ)
- Total ENIs: 7 endpoints × 2 AZs = 14 ENIs

**Validation**:
- Verify each interface endpoint has ENIs in both private subnets
- Test endpoint connectivity from both AZs

**Consequences of Violation**:
- Single AZ endpoint failure causes service disruption
- Cross-AZ data transfer charges (if endpoint not in same AZ as resource)

**Mapped Requirements**: NFR-1 (High Availability)

---

### BR-2.7: Private DNS for Interface Endpoints Rule

**Rule**: Private DNS MUST be enabled for all interface VPC endpoints to resolve AWS service DNS names to private VPC endpoint IPs.

**Rationale**: Application code uses standard AWS service DNS names (e.g., `secretsmanager.us-east-1.amazonaws.com`), private DNS resolves to private IPs.

**Specific Requirements**:
- Private DNS: Enabled for all interface endpoints
- DNS resolution: AWS service DNS names resolve to private VPC endpoint IPs (10.0.10.X)
- No code changes: Application uses standard AWS SDK DNS names

**Validation**:
- Verify private DNS enabled for each interface endpoint
- Test DNS resolution from private subnet (should resolve to private IP)

**Consequences of Violation**:
- AWS SDK attempts to reach public AWS service endpoints
- Traffic routed to internet (fails due to no NAT Gateway)
- Application cannot access AWS services

**Mapped Requirements**: NFR-3 (Network Isolation)

---

## 3. Security Group Rules

### BR-3.1: ALB Internet Access Rule

**Rule**: ALB Security Group MUST allow inbound HTTPS (port 443) from internet (`0.0.0.0/0`) for public access.

**Rationale**: Public users must be able to access web application via HTTPS.

**Specific Requirements**:
- Ingress: Protocol TCP, Port 443, Source `0.0.0.0/0`
- Ingress (optional): Protocol TCP, Port 80, Source `0.0.0.0/0` (HTTP redirect to HTTPS)
- Egress: Protocol TCP, Port 8000, Destination ECS Security Group

**Validation**:
- Verify ALB security group allows inbound 443 from 0.0.0.0/0
- Test HTTPS connectivity to ALB from internet

**Consequences of Violation**:
- Users cannot access application via HTTPS
- Application inaccessible to public

**Mapped Requirements**: FR-7 (Public API Endpoints)

---

### BR-3.2: ALB to ECS Only Rule

**Rule**: ALB Security Group MUST allow outbound traffic ONLY to ECS Security Group (least privilege).

**Rationale**: ALB should only forward traffic to ECS tasks, not other resources.

**Specific Requirements**:
- Egress: Protocol TCP, Port 8000, Destination ECS Security Group (NO `0.0.0.0/0`)

**Validation**:
- Verify ALB security group egress rules target ECS security group only

**Consequences of Violation**:
- Overly permissive security group
- Security audit failure

**Mapped Requirements**: SECURITY-04 (Least-Privilege)

---

### BR-3.3: ECS Accepts Traffic ONLY from ALB Rule

**Rule**: ECS Security Group MUST allow inbound traffic ONLY from ALB Security Group (no direct access from internet or other sources).

**Rationale**: ECS tasks in private subnets should only receive traffic via ALB (defense in depth).

**Specific Requirements**:
- Ingress: Protocol TCP, Port 8000, Source ALB Security Group (NO `0.0.0.0/0`)

**Validation**:
- Verify ECS security group ingress rules allow ONLY ALB security group

**Consequences of Violation**:
- Direct access to ECS tasks from internet (if public IP assigned)
- Security audit failure

**Mapped Requirements**: SECURITY-04 (Least-Privilege)

---

### BR-3.4: ECS Outbound Least-Privilege Rule

**Rule**: ECS Security Group MUST allow outbound traffic ONLY to Aurora, ElastiCache, and VPC Endpoint Security Groups (least privilege).

**Rationale**: ECS tasks should only access required resources, not arbitrary destinations.

**Specific Requirements**:
- Egress: Protocol TCP, Port 5432, Destination Aurora Security Group
- Egress: Protocol TCP, Port 6379, Destination ElastiCache Security Group
- Egress: Protocol TCP, Port 443, Destination VPC Endpoint Security Group
- NO egress rule for `0.0.0.0/0`

**Validation**:
- Verify ECS security group egress rules target specific security groups only
- Verify NO `0.0.0.0/0` egress rule

**Consequences of Violation**:
- Overly permissive security group
- Security audit failure
- Potential data exfiltration risk

**Mapped Requirements**: SECURITY-04 (Least-Privilege)

---

### BR-3.5: Aurora Accepts Traffic ONLY from ECS and Lambda Rule

**Rule**: Aurora Security Group MUST allow inbound PostgreSQL (port 5432) ONLY from ECS and Lambda Security Groups.

**Rationale**: Only application tier (ECS) and worker tier (Lambda) should access database.

**Specific Requirements**:
- Ingress: Protocol TCP, Port 5432, Source ECS Security Group
- Ingress: Protocol TCP, Port 5432, Source Lambda Security Group
- NO ingress rule for `0.0.0.0/0` or public access

**Validation**:
- Verify Aurora security group allows ONLY ECS and Lambda security groups

**Consequences of Violation**:
- Database exposed to unauthorized resources
- Security audit failure

**Mapped Requirements**: SECURITY-04 (Least-Privilege)

---

### BR-3.6: ElastiCache Accepts Traffic ONLY from ECS Rule

**Rule**: ElastiCache Security Group MUST allow inbound Redis (port 6379) ONLY from ECS Security Group (Lambda does not need cache access).

**Rationale**: Only web application (ECS) requires session cache access.

**Specific Requirements**:
- Ingress: Protocol TCP, Port 6379, Source ECS Security Group
- NO ingress from Lambda or other sources

**Validation**:
- Verify ElastiCache security group allows ONLY ECS security group

**Consequences of Violation**:
- Overly permissive security group
- Security audit failure

**Mapped Requirements**: SECURITY-04 (Least-Privilege)

---

### BR-3.7: Lambda No Ingress Rule

**Rule**: Lambda Security Group MUST have NO ingress rules (Lambda is event-driven, not network-triggered).

**Rationale**: Lambda function is triggered by SQS events, not by network connections.

**Specific Requirements**:
- Ingress rules: NONE (0 ingress rules)
- Egress rules: ONLY to Aurora and VPC Endpoint Security Groups

**Validation**:
- Verify Lambda security group has 0 ingress rules

**Consequences of Violation**:
- Unnecessary ingress rules
- Security audit failure

**Mapped Requirements**: SECURITY-04 (Least-Privilege)

---

### BR-3.8: Lambda Outbound Least-Privilege Rule

**Rule**: Lambda Security Group MUST allow outbound traffic ONLY to Aurora and VPC Endpoint Security Groups (least privilege).

**Rationale**: Lambda function only needs to access database and AWS services via VPC endpoints.

**Specific Requirements**:
- Egress: Protocol TCP, Port 5432, Destination Aurora Security Group
- Egress: Protocol TCP, Port 443, Destination VPC Endpoint Security Group
- NO egress rule for `0.0.0.0/0`

**Validation**:
- Verify Lambda security group egress rules target specific security groups only

**Consequences of Violation**:
- Overly permissive security group
- Security audit failure

**Mapped Requirements**: SECURITY-04 (Least-Privilege)

---

### BR-3.9: VPC Endpoint Accepts Traffic ONLY from ECS and Lambda Rule

**Rule**: VPC Endpoint Security Group MUST allow inbound HTTPS (port 443) ONLY from ECS and Lambda Security Groups.

**Rationale**: Only application tier (ECS) and worker tier (Lambda) should access VPC endpoints.

**Specific Requirements**:
- Ingress: Protocol TCP, Port 443, Source ECS Security Group
- Ingress: Protocol TCP, Port 443, Source Lambda Security Group
- NO ingress rule for `0.0.0.0/0`

**Validation**:
- Verify VPC Endpoint security group allows ONLY ECS and Lambda security groups

**Consequences of Violation**:
- Overly permissive security group
- Security audit failure

**Mapped Requirements**: SECURITY-04 (Least-Privilege)

---

## 4. IP Address Management Rules

### BR-4.1: DNS-Based Service Discovery Rule

**Rule**: All inter-service communication MUST use DNS names, NOT static IP addresses.

**Rationale**: AWS services use dynamic IPs, DNS resolution ensures connections to current resource IPs.

**Specific Requirements**:
- Aurora: Use cluster endpoint DNS name (e.g., `cluster.region.rds.amazonaws.com`)
- ElastiCache: Use cache endpoint DNS name (e.g., `cache.region.cache.amazonaws.com`)
- VPC endpoints: Use AWS service DNS names (e.g., `secretsmanager.region.amazonaws.com`)
- NO hardcoded IP addresses in application code or configuration

**Validation**:
- Review application code for hardcoded IPs (should be NONE)
- Verify all connections use DNS names

**Consequences of Violation**:
- Connection failures when AWS rotates IPs
- Maintenance burden (updating hardcoded IPs)

**Mapped Requirements**: NFR-15 (Maintainability)

---

### BR-4.2: IP Exhaustion Monitoring Rule

**Rule**: CloudWatch alarm MUST monitor available IP addresses per subnet and alert when available IPs < 50.

**Rationale**: Prevent IP address exhaustion before it blocks scaling.

**Specific Requirements**:
- CloudWatch metric: `AvailableIPAddressCount` per subnet
- Alarm threshold: Available IPs < 50
- Alarm action: SNS notification to operations team

**Validation**:
- Verify CloudWatch alarm exists for each subnet
- Test alarm by simulating IP exhaustion

**Consequences of Violation**:
- IP exhaustion prevents scaling (cannot launch new ECS tasks or Lambda ENIs)
- Service degradation or outage

**Mapped Requirements**: NFR-8 (Alerting), NFR-11 (Scalability)

---

## 5. Network ACL Rules

### BR-5.1: Security Groups as Primary Security Mechanism Rule

**Rule**: Security Groups MUST be the primary network security enforcement mechanism (Network ACLs optional).

**Rationale**: Security Groups are stateful (simpler, automatic return traffic), Network ACLs are stateless (complex, manual return traffic rules).

**Specific Requirements**:
- Security Groups: 6 security groups with least-privilege rules
- Network ACLs: Default ACL (allow all) - NO custom ACLs
- All security enforcement: Via Security Groups

**Validation**:
- Verify 6 security groups defined
- Verify NO custom Network ACLs created

**Consequences of Violation**:
- Increased operational complexity (managing stateless ACL rules)
- Higher risk of misconfiguration (forgetting return traffic rules)

**Mapped Requirements**: NFR-15 (Maintainability)

---

## 6. VPC Endpoint Rules

### BR-6.1: S3 Gateway Endpoint Rule

**Rule**: VPC MUST use S3 Gateway Endpoint (NOT S3 Interface Endpoint) for cost optimization.

**Rationale**: S3 supports both gateway and interface endpoints, gateway is free (no hourly charge).

**Specific Requirements**:
- S3 endpoint type: Gateway endpoint
- S3 interface endpoint: NOT deployed (unnecessary cost)

**Validation**:
- Verify S3 Gateway Endpoint exists
- Verify NO S3 Interface Endpoint exists

**Consequences of Violation**:
- Unnecessary cost (~$7/month for S3 interface endpoint)

**Mapped Requirements**: NFR-12 (Cost Optimization)

---

### BR-6.2: Interface Endpoints for Services Without Gateway Support Rule

**Rule**: VPC MUST use Interface Endpoints for AWS services that do NOT support Gateway Endpoints (ECR, CloudWatch Logs, Secrets Manager, STS, SES, SQS).

**Rationale**: These services only support interface endpoints (PrivateLink).

**Specific Requirements**:
- Interface endpoints required: ECR API, ECR DKR, CloudWatch Logs, Secrets Manager, STS, SES, SQS (7 total)
- Gateway endpoints: NOT available for these services

**Validation**:
- Verify 7 interface endpoints deployed
- Test connectivity to each service from private subnets

**Consequences of Violation**:
- Resources in private subnets cannot access these AWS services
- Application fails to function

**Mapped Requirements**: NFR-3 (Network Isolation)

---

### BR-6.3: No NAT Gateway Rule (Duplicate of BR-2.3)

**Rule**: VPC MUST NOT deploy NAT Gateway when VPC endpoints provide required AWS service access.

**Rationale**: NAT Gateway adds cost ($32/month) and reduces security (internet egress).

**Specific Requirements**:
- NAT Gateway: NOT deployed
- AWS service access: Via VPC endpoints ONLY

**Validation**:
- Verify no NAT Gateway exists in VPC

**Consequences of Violation**:
- Increased monthly cost
- Lower security posture

**Mapped Requirements**: NFR-3 (Network Isolation), NFR-12 (Cost Optimization)

---

### BR-6.4: VPC Endpoint for Every AWS Service Rule

**Rule**: VPC MUST deploy a VPC endpoint for EVERY AWS service used by the application.

**Rationale**: Ensure private subnet resources can access all required AWS services.

**Specific Requirements**:
- ECS tasks require: S3, ECR API, ECR DKR, CloudWatch Logs, Secrets Manager, STS, SES, SQS (8 services)
- Lambda requires: CloudWatch Logs, Secrets Manager, STS, SES (4 services)
- Total unique services: 8 (Lambda services are subset of ECS services)
- VPC endpoints deployed: 8 (1 gateway + 7 interface)

**Validation**:
- Map each AWS service call in application code to VPC endpoint
- Verify endpoint exists for each service

**Consequences of Violation**:
- Application cannot access required AWS services
- Functionality breaks (cannot send emails, retrieve secrets, etc.)

**Mapped Requirements**: NFR-3 (Network Isolation)

---

## 7. Encryption Rules

### BR-7.1: TLS 1.2+ for All VPC Endpoint Traffic Rule

**Rule**: All traffic to VPC endpoints MUST use TLS 1.2 or higher for encryption in transit.

**Rationale**: Satisfy NFR-5 (Encryption) and SECURITY-01 (Encryption in transit).

**Specific Requirements**:
- VPC endpoints: TLS 1.2+ enforced (AWS default for interface endpoints)
- Application SDK configuration: TLS 1.2+ minimum
- NO plaintext HTTP to VPC endpoints

**Validation**:
- Verify application SDK configuration uses TLS 1.2+
- Test connection to VPC endpoints (should use TLS)

**Consequences of Violation**:
- Unencrypted data in transit
- Security audit failure
- Violates SECURITY-01

**Mapped Requirements**: NFR-5 (Encryption), SECURITY-01 (Encryption in Transit)

---

## 8. Documentation Rules

### BR-8.1: Security Group Rules Documentation Rule

**Rule**: All security group rules MUST be documented with rationale, source/destination, and protocol/port.

**Rationale**: Enable security audits and change impact analysis.

**Specific Requirements**:
- Security group documentation format:
  - Group name
  - Purpose
  - Ingress rules: Protocol, Port, Source, Rationale
  - Egress rules: Protocol, Port, Destination, Rationale
- Documentation location: CDK stack comments or separate security-groups.md file

**Validation**:
- Verify all security groups have documentation
- Review documentation completeness

**Consequences of Violation**:
- Security audit failure
- Difficulty troubleshooting connectivity issues
- Risk of accidental rule deletion

**Mapped Requirements**: SECURITY-05 (Security Group Rules Documented), NFR-15 (Maintainability)

---

## Summary

This document defines 34 business rules across 8 categories:

1. **VPC Configuration Rules** (5 rules): CIDR block, subnet sizing, Multi-AZ distribution
2. **Routing Rules** (7 rules): Public/private routing, VPC endpoints, no NAT Gateway
3. **Security Group Rules** (9 rules): Least-privilege ingress/egress for 6 security groups
4. **IP Address Management Rules** (2 rules): DNS-based discovery, IP exhaustion monitoring
5. **Network ACL Rules** (1 rule): Security Groups as primary mechanism
6. **VPC Endpoint Rules** (4 rules): Gateway vs interface, endpoint requirements
7. **Encryption Rules** (1 rule): TLS 1.2+ for VPC endpoint traffic
8. **Documentation Rules** (1 rule): Security group documentation

**Compliance**: All rules are MANDATORY and will be validated during Infrastructure Design and Code Generation stages.

**Traceability**: Each rule is mapped to functional requirements (FR), non-functional requirements (NFR), or security extension rules (SECURITY).

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-12  
**Status**: Ready for Review
