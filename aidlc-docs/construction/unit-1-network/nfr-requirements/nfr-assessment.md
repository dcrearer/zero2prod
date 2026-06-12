# NFR Requirements Assessment - Unit 1: Network Infrastructure

## Overview

This document assesses which Non-Functional Requirements (NFRs) from the project requirements document apply to Unit 1: Network Infrastructure. Each NFR is evaluated for applicability, and specific requirements are derived for implementation.

**Unit Scope**: AWS VPC network foundation including subnets, security groups, VPC endpoints, routing, and internet gateway.

**Assessment Date**: 2026-06-12  
**Unit Owner**: Network Infrastructure Team  
**Related Documents**:
- Requirements: `/aidlc-docs/inception/requirements/requirements.md`
- Functional Design: `/aidlc-docs/construction/unit-1-network/functional-design/`

---

## NFR Assessment Summary

| NFR ID | NFR Name | Applicable | Priority | Status |
|--------|----------|------------|----------|--------|
| NFR-1 | Reliability - High Availability | YES | CRITICAL | Assessed |
| NFR-2 | Reliability - Disaster Recovery | YES | HIGH | Assessed |
| NFR-3 | Security - Network Isolation | YES | CRITICAL | Assessed |
| NFR-4 | Security - Secrets Management | YES | CRITICAL | Assessed |
| NFR-5 | Security - Encryption | YES | CRITICAL | Assessed |
| NFR-6 | Security - Access Logging | YES | HIGH | Assessed |
| NFR-7 | Observability - Monitoring | PARTIAL | MEDIUM | Assessed |
| NFR-8 | Observability - Alerting | N/A | LOW | N/A |
| NFR-9 | Performance - API Latency | YES | HIGH | Assessed |
| NFR-10 | Performance - Email Queueing | N/A | N/A | N/A |
| NFR-11 | Scalability - Auto-Scaling | YES | MEDIUM | Assessed |
| NFR-12 | Cost Optimization | YES | LOW | Assessed |
| NFR-13 | Deployment Automation | YES | HIGH | Assessed |
| NFR-14 | Infrastructure as Code | YES | CRITICAL | Assessed |
| NFR-15 | Maintainability - Code Quality | YES | MEDIUM | Assessed |

**Extension Rules Assessment**:

| Extension Rule ID | Extension Name | Applicable | Priority | Status |
|-------------------|----------------|------------|----------|--------|
| SECURITY-01 | Encryption (at rest/in transit) | YES | CRITICAL | Assessed |
| SECURITY-02 | Access Logging | YES | HIGH | Assessed |
| SECURITY-03 | Secrets Management | YES | CRITICAL | Assessed |
| SECURITY-04 | Private Networking & Least Privilege | YES | CRITICAL | Assessed |
| SECURITY-05 | Security Group Documentation | YES | HIGH | Assessed |
| SECURITY-06 | No Hardcoded Credentials | YES | CRITICAL | Assessed |

---

## 1. Performance Requirements

### 1.1 Network Latency (NFR-9)

**Applicable**: YES  
**Priority**: HIGH  
**Well-Architected Pillar**: Performance Efficiency

**Requirement**: Network infrastructure must support API response time < 200ms (p95) for application traffic.

**Network-Specific Performance Targets**:

1. **Inter-Service Latency**:
   - ECS → Aurora (same AZ): < 1ms (target: 0.5ms)
   - ECS → Aurora (cross-AZ): < 2ms (target: 1ms)
   - ECS → ElastiCache (same AZ): < 1ms (target: 0.3ms)
   - ECS → VPC Endpoint (same AZ): < 1ms (target: 0.5ms)
   - Lambda → Aurora (same AZ): < 1ms (target: 0.5ms)
   - Lambda → VPC Endpoint (same AZ): < 1ms (target: 0.5ms)

2. **VPC Endpoint Performance**:
   - Gateway endpoint (S3): < 5ms for ECR image pulls
   - Interface endpoints: < 2ms for AWS API calls (Secrets Manager, SES, SQS)
   - Private DNS resolution: < 1ms

3. **Cross-AZ Traffic**:
   - ALB → ECS (cross-AZ): < 3ms
   - Aurora primary → standby replication: < 5ms (asynchronous)

**Performance Optimization Strategies**:

1. **Same-AZ Placement**:
   - Deploy resources in same AZ when possible to minimize latency
   - Multi-AZ deployment for HA, not all traffic crosses AZs

2. **VPC Endpoint Optimization**:
   - Interface endpoints deployed in BOTH AZs (closest endpoint is used)
   - Private DNS automatically routes to nearest endpoint

3. **Network Capacity**:
   - VPC supports up to 5 Gbps burst capacity per ECS task
   - Aurora network throughput: Up to 10 Gbps
   - ElastiCache network throughput: Up to 6 Gbps

**Monitoring Requirements**:
- CloudWatch metric: VPC endpoint response time (interface endpoints)
- CloudWatch metric: Cross-AZ data transfer latency (if measurable)
- X-Ray traces: End-to-end latency including network hops

**Acceptance Criteria**:
- [ ] Network latency contributes < 10ms to total API response time
- [ ] 99% of inter-service connections establish within 100ms
- [ ] VPC endpoint DNS resolution < 1ms

---

### 1.2 Network Throughput

**Applicable**: YES  
**Priority**: MEDIUM  
**Well-Architected Pillar**: Performance Efficiency

**Requirement**: Network must support expected application throughput without bottlenecks.

**Throughput Requirements**:

1. **ALB Ingress Throughput**:
   - Expected traffic: 100 requests/second (peak)
   - Average request size: 10 KB
   - Expected ingress bandwidth: 1 MB/s (8 Mbps)
   - ALB capacity: Auto-scales to handle traffic

2. **ECS Task Throughput**:
   - Database queries: 50 queries/second per task (small payloads)
   - Redis operations: 1,000 ops/second per task (< 1 KB each)
   - VPC endpoint API calls: 10 calls/second per task
   - Total throughput per task: ~10 Mbps (well below 5 Gbps limit)

3. **Lambda Throughput**:
   - SES API calls: 14 emails/second (100 concurrent Lambda invocations)
   - Database queries: 10 queries/second per Lambda
   - Expected throughput per Lambda: ~1 Mbps

4. **Cross-AZ Data Transfer**:
   - ALB → ECS (cross-AZ): 50% of traffic = 0.5 MB/s
   - Aurora replication (cross-AZ): ~100 KB/s (transaction logs)

**Throughput Optimization**:
- VPC endpoints use AWS backbone network (high throughput, low latency)
- No NAT Gateway bottleneck (VPC endpoints only)
- Aurora read replicas can be added if read throughput becomes bottleneck

**Monitoring Requirements**:
- CloudWatch metric: ALB processed bytes (ingress/egress)
- CloudWatch metric: VPC endpoint data processed
- CloudWatch metric: Cross-AZ data transfer (for cost tracking)

**Acceptance Criteria**:
- [ ] Network supports 100 requests/second without degradation
- [ ] No network throttling or packet loss under expected load
- [ ] VPC endpoints support required throughput (no bottleneck)

---

## 2. Security Requirements

### 2.1 Network Isolation (NFR-3, SECURITY-04)

**Applicable**: YES  
**Priority**: CRITICAL  
**Well-Architected Pillar**: Security

**Requirement**: Private subnets with VPC endpoints (highest security, no internet egress).

**Security Controls**:

1. **Private Subnet Architecture**:
   - Public subnets: ALB ONLY (internet-facing)
   - Private subnets: ECS, Lambda, Aurora, ElastiCache (NO internet access)
   - NO NAT Gateway (no internet egress from private subnets)
   - NO Internet Gateway route in private route table

2. **VPC Endpoints (Private AWS Service Access)**:
   - S3 Gateway Endpoint: ECR image pulls without internet
   - 7 Interface Endpoints: ECR API, ECR DKR, CloudWatch Logs, Secrets Manager, STS, SES, SQS
   - Private DNS enabled: AWS service DNS names resolve to private VPC IPs
   - All AWS API traffic stays within VPC

3. **Security Group Least Privilege** (SECURITY-04):
   - ALB Security Group: Inbound HTTPS from internet, outbound to ECS only
   - ECS Security Group: Inbound from ALB only, outbound to Aurora, ElastiCache, VPC endpoints only
   - Aurora Security Group: Inbound from ECS and Lambda only, NO outbound rules
   - ElastiCache Security Group: Inbound from ECS only, NO outbound rules
   - Lambda Security Group: NO inbound rules, outbound to Aurora and VPC endpoints only
   - VPC Endpoint Security Group: Inbound from ECS and Lambda only, NO outbound rules

4. **Network Segmentation**:
   - Public subnets: ALB only (no direct application access)
   - Private subnets: Application tier (ECS, Lambda), Data tier (Aurora, ElastiCache)
   - No cross-tier traffic except via security group rules

**Compliance Verification**:

| Security Control | Implementation | Verification Method |
|------------------|----------------|---------------------|
| Private subnets have no internet egress | No IGW/NAT in private route table | CDK synth: Check route table routes |
| VPC endpoints for all AWS services | 8 endpoints created | AWS Console: List VPC endpoints |
| Security groups use least privilege | No `0.0.0.0/0` egress (except ALB) | CDK synth: Check security group rules |
| Private DNS enabled for interface endpoints | `private_dns_enabled=true` | AWS Console: Check endpoint settings |

**Acceptance Criteria**:
- [ ] Private subnets have NO route to Internet Gateway or NAT Gateway
- [ ] All 8 VPC endpoints created and functional
- [ ] Security groups enforce least-privilege rules (no `0.0.0.0/0` egress except ALB)
- [ ] Private DNS resolution works for all AWS services
- [ ] Resources in private subnets cannot reach public internet

---

### 2.2 Encryption in Transit (NFR-5, SECURITY-01)

**Applicable**: YES  
**Priority**: CRITICAL  
**Well-Architected Pillar**: Security

**Requirement**: Enforce TLS 1.2+ for all network communications.

**Encryption Requirements**:

1. **ALB → ECS Tasks**:
   - Protocol: HTTPS with TLS 1.2+ (or HTTP if TLS termination at ALB)
   - Decision: TLS termination at ALB, HTTP to ECS (within private VPC)
   - Rationale: ECS tasks in private subnet, TLS termination at ALB is standard practice
   - Alternative: End-to-end TLS (ALB → ECS) for highest security (optional future enhancement)

2. **ECS → Aurora PostgreSQL**:
   - Protocol: PostgreSQL SSL/TLS connection (enforced by Aurora)
   - TLS version: TLS 1.2+ (Aurora default)
   - Verification: Application connection string must include `sslmode=require`

3. **ECS → ElastiCache Redis**:
   - Protocol: TLS in-transit encryption enabled
   - TLS version: TLS 1.2+
   - Verification: Redis client configured for TLS

4. **ECS/Lambda → VPC Endpoints**:
   - Protocol: HTTPS with TLS 1.2+ (AWS SDK default)
   - All AWS API calls (Secrets Manager, SES, SQS) use TLS 1.2+
   - VPC endpoints enforce TLS (no plaintext HTTP)

5. **Aurora Cross-AZ Replication**:
   - Protocol: TLS 1.2+ (AWS managed, encrypted by default)

**Network Security Group Enforcement**:
- VPC Endpoint Security Group: Only allow port 443 (HTTPS) from ECS and Lambda
- Aurora Security Group: Only allow port 5432 (PostgreSQL with SSL/TLS)
- ElastiCache Security Group: Only allow port 6379 (Redis with TLS)

**Monitoring Requirements**:
- ALB metric: TLS negotiation errors (CloudWatch)
- Aurora slow query log: Non-SSL connections (should be 0)
- ElastiCache metric: TLS connection count

**Acceptance Criteria**:
- [ ] ALB configured for TLS 1.2+ (no SSLv3, TLS 1.0, TLS 1.1)
- [ ] Aurora connection strings enforce `sslmode=require`
- [ ] ElastiCache TLS in-transit encryption enabled
- [ ] VPC endpoints only accept HTTPS (port 443)
- [ ] No plaintext traffic for sensitive data

---

### 2.3 Secrets Management (NFR-4, SECURITY-03, SECURITY-06)

**Applicable**: YES  
**Priority**: CRITICAL  
**Well-Architected Pillar**: Security

**Requirement**: No hardcoded credentials in VPC configuration, all secrets stored in AWS Secrets Manager.

**Network-Specific Secrets**:

1. **Secrets Stored in Secrets Manager** (accessed via VPC endpoint):
   - Database password (Aurora PostgreSQL)
   - Redis connection string (ElastiCache Serverless)
   - HMAC secret (session cookies)
   - SES API credentials (or IAM role preferred)
   - Cognito client secret

2. **Secrets NOT in CDK Code**:
   - No hardcoded IPs, passwords, or API keys in CDK Python code
   - CDK code references Secrets Manager ARNs, not secret values
   - Secret values injected at runtime via ECS task environment variables

3. **VPC Endpoint for Secrets Manager**:
   - Interface endpoint: `com.amazonaws.us-east-1.secretsmanager`
   - Deployed in BOTH private subnets (Multi-AZ)
   - Private DNS enabled: `secretsmanager.us-east-1.amazonaws.com` resolves to VPC endpoint IP
   - Security Group: Allows inbound HTTPS (443) from ECS and Lambda only

**Compliance Verification**:

| Compliance Rule | Network Implementation | Verification Method |
|-----------------|------------------------|---------------------|
| SECURITY-03: Secrets in managed service | Secrets Manager VPC endpoint deployed | AWS Console: Verify endpoint exists |
| SECURITY-06: No hardcoded credentials | CDK code uses Secrets Manager ARNs | Code review: Search for hardcoded secrets |
| SECURITY-04: Least privilege access | VPC endpoint security group restricts access | CDK synth: Check security group rules |

**Acceptance Criteria**:
- [ ] Secrets Manager VPC endpoint deployed in both private subnets
- [ ] VPC endpoint security group allows HTTPS from ECS and Lambda only
- [ ] No hardcoded credentials in CDK Python code (automated scan)
- [ ] Private DNS resolves `secretsmanager.us-east-1.amazonaws.com` to VPC endpoint

---

### 2.4 Access Logging (NFR-6, SECURITY-02)

**Applicable**: YES  
**Priority**: HIGH  
**Well-Architected Pillar**: Security

**Requirement**: Access logging on Application Load Balancer (network-facing intermediary).

**Logging Requirements**:

1. **ALB Access Logs**:
   - Destination: S3 bucket (`zero2prod-alb-logs-<account-id>-<region>`)
   - Log fields: Timestamp, client IP, target IP, response code, latency, request URL, user-agent
   - Retention: 90 days (per SECURITY-02 requirement)
   - Encryption: S3 bucket encryption at rest (SSE-S3 or SSE-KMS)

2. **VPC Flow Logs** (Optional, not required by SECURITY-02):
   - Capture: Accept/reject logs for all ENIs in VPC
   - Destination: CloudWatch Logs or S3
   - Use case: Troubleshooting connectivity issues, security forensics
   - Cost: ~$0.50 per GB ingested (can be expensive for high-traffic VPCs)
   - Decision: NOT implemented in initial deployment (can be enabled later if needed)

3. **Network Intermediary Definition**:
   - Network intermediary: Application Load Balancer (public-facing)
   - NOT a network intermediary: VPC endpoints (internal AWS service access)
   - SECURITY-02 applies to ALB only

**S3 Bucket Configuration**:

| Property | Value | Rationale |
|----------|-------|-----------|
| Bucket name | `zero2prod-alb-logs-<account-id>-<region>` | Unique per account/region |
| Encryption | SSE-S3 (or SSE-KMS) | SECURITY-01 compliance |
| Lifecycle policy | 90-day retention, then delete | Cost optimization, compliance |
| Public access | Blocked (S3 Block Public Access) | Security best practice |
| IAM policy | Allow ALB service principal write access | Enable ALB to write logs |

**Monitoring Requirements**:
- S3 bucket metric: Log file count (ensure logs are being written)
- S3 bucket metric: Total storage (monitor cost)
- CloudWatch alarm: Alert if no logs received in 1 hour (indicates logging failure)

**Acceptance Criteria**:
- [ ] S3 bucket created for ALB access logs
- [ ] ALB access logging enabled (logs written to S3)
- [ ] S3 bucket encrypted at rest (SSE-S3 or SSE-KMS)
- [ ] S3 lifecycle policy: 90-day retention
- [ ] CloudWatch alarm: Alert if no logs received in 1 hour

---

### 2.5 Security Group Documentation (SECURITY-05)

**Applicable**: YES  
**Priority**: HIGH  
**Well-Architected Pillar**: Security

**Requirement**: All security group rules must be documented with purpose and rationale.

**Documentation Requirements**:

1. **Inline Rule Descriptions** (AWS Console/CDK):
   - Every ingress and egress rule has a `description` field
   - Description format: `<Protocol> from/to <Source/Destination> for <Purpose>`
   - Example: "HTTPS from ECS tasks to VPC endpoints for AWS API access"

2. **Security Group Documentation Artifacts**:
   - Functional Design document: `business-rules.md` (BR-3.1 to BR-3.9)
   - Domain Entities document: `domain-entities.md` (Security Group Entity section)
   - This NFR Assessment document (Security Group compliance summary)

3. **Security Group Inventory**:

| Security Group | Purpose | Ingress Rules | Egress Rules | Resources Assigned |
|----------------|---------|---------------|--------------|-------------------|
| `zero2prod-alb-sg` | Public internet → ALB | HTTPS (443), HTTP (80) from 0.0.0.0/0 | HTTP (8000) to ECS SG | Application Load Balancer |
| `zero2prod-ecs-sg` | ECS task traffic | HTTP (8000) from ALB SG | PostgreSQL (5432) to Aurora SG, Redis (6379) to ElastiCache SG, HTTPS (443) to VPC Endpoint SG | ECS Fargate tasks |
| `zero2prod-aurora-sg` | Aurora database access | PostgreSQL (5432) from ECS SG, PostgreSQL (5432) from Lambda SG | None | Aurora PostgreSQL cluster |
| `zero2prod-elasticache-sg` | ElastiCache session cache | Redis (6379) from ECS SG | None | ElastiCache Serverless Redis |
| `zero2prod-lambda-sg` | Lambda function traffic | None (event-driven) | PostgreSQL (5432) to Aurora SG, HTTPS (443) to VPC Endpoint SG | Lambda email sender function |
| `zero2prod-vpc-endpoints-sg` | VPC endpoint access | HTTPS (443) from ECS SG, HTTPS (443) from Lambda SG | None | VPC interface endpoints |

4. **Compliance Verification**:
   - Automated scan: Every security group rule has a non-empty `description` field
   - Code review: Security group rules match documented business rules (BR-3.1 to BR-3.9)
   - Audit: Review security group rules quarterly for least-privilege compliance

**Acceptance Criteria**:
- [ ] All 6 security groups have documented purpose
- [ ] All ingress/egress rules have `description` field
- [ ] Security group inventory table maintained in documentation
- [ ] Automated scan: No security group rules without description

---

## 3. Reliability Requirements

### 3.1 High Availability (NFR-1)

**Applicable**: YES  
**Priority**: CRITICAL  
**Well-Architected Pillar**: Reliability

**Requirement**: 99.9% availability through Multi-AZ network deployment.

**Multi-AZ Network Architecture**:

1. **Subnet Distribution**:
   - Public Subnet 1: `us-east-1a` (ALB node)
   - Public Subnet 2: `us-east-1b` (ALB node)
   - Private Subnet 1: `us-east-1a` (ECS, Aurora, ElastiCache, Lambda, VPC endpoints)
   - Private Subnet 2: `us-east-1b` (ECS, Aurora, ElastiCache, Lambda, VPC endpoints)

2. **VPC Endpoint High Availability**:
   - Gateway endpoint (S3): Highly available by design (no AZ placement)
   - Interface endpoints: Deployed in BOTH private subnets (Multi-AZ)
   - DNS resolution: Automatically routes to healthy endpoint in nearest AZ

3. **Failure Scenarios**:

| Failure | Network Impact | Recovery Time |
|---------|---------------|---------------|
| Single AZ failure | Traffic routes to healthy AZ automatically | < 2 minutes (ALB health check interval) |
| VPC endpoint failure (1 AZ) | Traffic routes to endpoint in other AZ | < 1 minute (DNS TTL) |
| Security group misconfiguration | Traffic blocked, requires manual fix | Depends on detection time |
| Route table misconfiguration | Traffic routing breaks, requires manual fix | Depends on detection time |

4. **High Availability Verification**:
   - Test: Simulate AZ failure by shutting down resources in 1 AZ
   - Expected: Application remains available via resources in other AZ
   - Test: Verify ALB distributes traffic to both AZs under normal conditions

**Network SLA Calculation**:
- ALB availability: 99.99% (AWS SLA)
- VPC availability: 99.99% (regional service)
- Interface endpoint availability: 99.95% (per AWS SLA)
- Combined network availability: ~99.9% (conservative estimate)

**Acceptance Criteria**:
- [ ] Subnets deployed in 2 Availability Zones
- [ ] Interface VPC endpoints deployed in both AZs
- [ ] ALB nodes deployed in both AZs
- [ ] Network remains available if 1 AZ fails (tested)
- [ ] Availability target: 99.9% (measured over 30 days)

---

### 3.2 Disaster Recovery (NFR-2)

**Applicable**: YES  
**Priority**: HIGH  
**Well-Architected Pillar**: Reliability

**Requirement**: Network infrastructure ready for cross-region DR (warm standby).

**Network DR Strategy**:

1. **Primary Region**: us-east-1 (or configured region)
2. **DR Region**: us-west-2 (or configured secondary region)

3. **Network Infrastructure Replication**:
   - CDK stacks deployable to DR region (Infrastructure as Code)
   - VPC CIDR: Same as primary (`10.0.0.0/16` in DR region)
   - Subnet structure: Same as primary (4 subnets, 2 AZs in DR region)
   - Security groups: Same rules as primary (deployed via CDK)
   - VPC endpoints: Same 8 endpoints in DR region

4. **DR Network Components**:
   - VPC: Created in DR region (separate VPC, not peered)
   - Subnets: Same CIDR blocks (`10.0.1.0/24`, `10.0.2.0/24`, `10.0.10.0/24`, `10.0.11.0/24`)
   - Security Groups: Same 6 security groups with same rules
   - VPC Endpoints: Same 8 endpoints (Gateway + Interface)
   - ALB: Created in DR region (DNS failover via Route 53)

5. **Cross-Region Considerations**:
   - VPC peering: NOT required (primary and DR VPCs are independent)
   - Data replication: Aurora cross-region read replica (data tier, not network tier)
   - DNS failover: Route 53 health checks route traffic to DR region on primary failure

**DR Network Deployment**:

| Component | Primary Region (us-east-1) | DR Region (us-west-2) |
|-----------|----------------------------|------------------------|
| VPC CIDR | `10.0.0.0/16` | `10.0.0.0/16` (separate VPC) |
| Subnets | 4 (2 public, 2 private) | 4 (2 public, 2 private) |
| Security Groups | 6 | 6 (same rules) |
| VPC Endpoints | 8 | 8 (same services) |
| ALB | Active | Warm standby (scaled down) |

**DR Failover Process (Network Perspective)**:
1. Route 53 health check detects primary region failure
2. Route 53 updates DNS to point to DR region ALB
3. Traffic routes to DR region (network ready, no changes needed)
4. ECS tasks in DR region scale up (network supports increased traffic)

**Network RTO/RPO**:
- RTO (Recovery Time Objective): < 5 minutes (network is ready, waiting for DNS propagation)
- RPO (Recovery Point Objective): 0 (network infrastructure is stateless)

**Acceptance Criteria**:
- [ ] CDK stacks deployable to DR region (tested)
- [ ] DR region VPC created with same structure as primary
- [ ] DR region VPC endpoints functional (tested)
- [ ] Route 53 health checks configured for DNS failover
- [ ] DR failover tested successfully (network connectivity verified)

---

## 4. Scalability Requirements

### 4.1 IP Address Space Scalability (NFR-11)

**Applicable**: YES  
**Priority**: MEDIUM  
**Well-Architected Pillar**: Performance Efficiency

**Requirement**: IP address space must support auto-scaling of ECS tasks and Lambda functions.

**Current IP Usage**:

| Resource Type | Current Count | IPs per Resource | Total IPs Used | Subnet |
|---------------|---------------|------------------|----------------|--------|
| ALB nodes | 4 (2 per AZ) | 1 | 4 | Public subnets |
| ECS tasks | 2-10 (min-max) | 1 | 10 (max) | Private subnets |
| Aurora instances | 2 (primary + standby) | 1 | 2 | Private subnets |
| ElastiCache nodes | 2 (Multi-AZ) | 1 | 2 | Private subnets |
| Lambda ENIs | 10 (concurrent) | 1 | 10 | Private subnets |
| VPC endpoint ENIs | 14 (7 services × 2 AZs) | 1 | 14 | Private subnets |
| Reserved (AWS) | - | - | 10 (5 per subnet) | Both |
| **Total** | - | - | **52 IPs** | - |

**Capacity Analysis**:

| Subnet Type | CIDR | Total IPs | Used IPs | Available IPs | Utilization |
|-------------|------|-----------|----------|---------------|-------------|
| Public Subnet 1 (AZ-A) | `10.0.1.0/24` | 256 | 2 (ALB) + 5 (AWS) = 7 | 249 | 2.7% |
| Public Subnet 2 (AZ-B) | `10.0.2.0/24` | 256 | 2 (ALB) + 5 (AWS) = 7 | 249 | 2.7% |
| Private Subnet 1 (AZ-A) | `10.0.10.0/24` | 256 | 19 (resources) + 5 (AWS) = 24 | 232 | 9.4% |
| Private Subnet 2 (AZ-B) | `10.0.11.0/24` | 256 | 19 (resources) + 5 (AWS) = 24 | 232 | 9.4% |

**Scalability Headroom**:

1. **ECS Task Scaling**:
   - Current max: 10 tasks
   - Scalability target: 100 tasks (10x growth)
   - IP requirement: 100 IPs (1 per task)
   - Available IPs per private subnet: 232
   - Conclusion: Sufficient capacity for 10x growth

2. **Lambda ENI Scaling**:
   - Current max concurrent: 100 (reserved concurrency)
   - Lambda ENI reuse: Multiple invocations share ENIs (Hyperplane architecture)
   - Expected max ENIs: ~20 (AWS reuses ENIs efficiently)
   - Conclusion: Sufficient capacity

3. **Future Expansion**:
   - Reserved CIDR space: `10.0.3.0/24` to `10.0.9.0/24`, `10.0.12.0/24` to `10.0.255.0/24`
   - Future capacity: 61,952 additional IPs (242 × 256)
   - Use case: Add new subnets if existing subnets reach 85% utilization

**IP Exhaustion Monitoring**:
- CloudWatch metric: Available IPs per subnet (AWS-provided metric)
- Warning threshold: < 100 available IPs (39% utilization)
- Critical threshold: < 50 available IPs (80% utilization)
- Action: Expand subnet or add new subnet

**Acceptance Criteria**:
- [ ] Current IP utilization < 10% (headroom for growth)
- [ ] Subnet sizing supports 10x growth in ECS tasks
- [ ] CloudWatch alarm: Alert if available IPs < 100 per subnet
- [ ] Reserved CIDR space documented for future expansion

---

### 4.2 VPC Endpoint Scalability

**Applicable**: YES  
**Priority**: LOW  
**Well-Architected Pillar**: Performance Efficiency

**Requirement**: VPC endpoints must scale to support increased traffic from auto-scaling ECS tasks and Lambda functions.

**VPC Endpoint Scaling Characteristics**:

1. **Gateway Endpoint (S3)**:
   - Scaling: Automatic (AWS-managed, highly available)
   - Throughput: Unlimited (no documented limits)
   - Cost: Free (no per-GB charges for gateway endpoint itself)

2. **Interface Endpoints** (ECR API, ECR DKR, Logs, Secrets Manager, STS, SES, SQS):
   - Scaling: Automatic (AWS-managed)
   - Throughput: 10 Gbps per ENI (2 ENIs per endpoint for Multi-AZ)
   - Maximum connections: 55,000 per ENI (110,000 per endpoint for Multi-AZ)
   - Cost: $0.01 per GB processed (after $7/month flat fee)

**Scalability Analysis**:

| VPC Endpoint | Expected Traffic (peak) | Max Connections Needed | Scalability Status |
|--------------|-------------------------|------------------------|-------------------|
| S3 (Gateway) | 100 MB/s (ECR image pulls) | N/A (gateway endpoint) | No limits, scales automatically |
| ECR API | 10 requests/s (100 ECS tasks × 0.1 req/s) | 100 | No scalability concerns |
| ECR DKR | 50 MB/s (100 ECS tasks × 0.5 MB/s) | 100 | No scalability concerns |
| CloudWatch Logs | 1 MB/s (100 ECS tasks + 100 Lambda) | 200 | No scalability concerns |
| Secrets Manager | 10 requests/s (100 ECS tasks × 0.1 req/s) | 100 | No scalability concerns |
| STS | 10 requests/s (IAM role assumption) | 100 | No scalability concerns |
| SES | 14 emails/s (Lambda concurrency) | 14 | No scalability concerns |
| SQS | 100 messages/s (newsletter queueing) | 100 | No scalability concerns |

**Conclusion**: VPC endpoints have sufficient capacity for expected traffic (10x growth headroom).

**Acceptance Criteria**:
- [ ] VPC endpoints support peak traffic without throttling
- [ ] No VPC endpoint connection limits reached (monitor via CloudWatch if available)
- [ ] Gateway endpoint (S3) handles ECR image pulls without bottleneck

---

## 5. Observability Requirements

### 5.1 Network Monitoring (NFR-7)

**Applicable**: PARTIAL  
**Priority**: MEDIUM  
**Well-Architected Pillar**: Operational Excellence

**Requirement**: CloudWatch metrics for network performance and VPC resource utilization.

**Network-Specific CloudWatch Metrics**:

1. **ALB Metrics** (already covered by NFR-7):
   - Request count, target response time, HTTP error rates
   - Healthy/unhealthy target count
   - Network layer: ALB is the network intermediary

2. **VPC Metrics** (network-specific):
   - Available IPs per subnet (AWS-provided metric)
   - VPC endpoint data processed (interface endpoints only)
   - Cross-AZ data transfer (for cost tracking)

3. **VPC Flow Logs** (optional, not in initial scope):
   - Capture: Accept/reject logs for troubleshooting
   - Destination: CloudWatch Logs or S3
   - Cost: ~$0.50 per GB (can be expensive)
   - Decision: Enable only if connectivity issues arise

**Monitoring Dashboard**:

| Metric | Source | Threshold | Action |
|--------|--------|-----------|--------|
| Available IPs per subnet | CloudWatch | < 100 | Alert network team |
| VPC endpoint data processed | CloudWatch | > 100 GB/month | Review cost optimization |
| ALB unhealthy targets | CloudWatch | > 0 for 5 minutes | Page on-call |

**Monitoring Limitations**:
- VPC endpoint latency: Not directly measurable (no AWS metric)
- Security group rule hits: Not measurable (no AWS metric)
- Cross-AZ latency: Not directly measurable (X-Ray can show end-to-end)

**Acceptance Criteria**:
- [ ] CloudWatch dashboard includes available IPs per subnet
- [ ] CloudWatch alarm: Alert if available IPs < 100
- [ ] VPC endpoint data processed tracked (cost monitoring)
- [ ] ALB metrics included in operational dashboard

---

### 5.2 Network Alerting (NFR-8)

**Applicable**: N/A  
**Priority**: N/A

**Rationale**: NFR-8 focuses on application-level alerting (service down, high error rate, Lambda errors, DLQ messages). Network infrastructure itself has no critical alerts in initial scope.

**Network-Related Alerts** (covered under NFR-8, not network-specific):
- ALB target group has 0 healthy targets → Page on-call (application-level, not network-level)

**Future Consideration**:
- If VPC Flow Logs enabled, add alert for unusual traffic patterns (security monitoring)
- If VPC endpoint failures occur, add alert for endpoint unavailability

---

## 6. Operational Excellence Requirements

### 6.1 Infrastructure as Code (NFR-14)

**Applicable**: YES  
**Priority**: CRITICAL  
**Well-Architected Pillar**: Operational Excellence

**Requirement**: AWS CDK Python for all network infrastructure (VPC, subnets, security groups, VPC endpoints).

**CDK Stack Structure**:

1. **Network Stack** (Unit 1):
   - VPC with CIDR `10.0.0.0/16`
   - 4 Subnets (2 public, 2 private) in 2 AZs
   - 6 Security Groups with least-privilege rules
   - 8 VPC Endpoints (1 Gateway, 7 Interface)
   - 2 Route Tables (1 public, 1 private)
   - 1 Internet Gateway

2. **CDK Construct Level**:
   - VPC: L2 construct (`aws_cdk.aws_ec2.Vpc`)
   - Subnets: L2 construct (`aws_cdk.aws_ec2.Subnet`)
   - Security Groups: L2 construct (`aws_cdk.aws_ec2.SecurityGroup`)
   - VPC Endpoints: L2 construct (`aws_cdk.aws_ec2.InterfaceVpcEndpoint`, `aws_cdk.aws_ec2.GatewayVpcEndpoint`)
   - Route Tables: L2 construct (`aws_cdk.aws_ec2.CfnRouteTable`)

3. **CDK Best Practices**:
   - Environment-specific configuration: `dev.py`, `prod.py` (VPC CIDR, AZ count)
   - No hardcoded values: Use CDK context variables and environment variables
   - Output exports: VPC ID, Subnet IDs, Security Group IDs (for cross-stack references)
   - Tagging strategy: `Environment`, `Project`, `ManagedBy=CDK`

**Infrastructure Drift Detection**:
- CDK diff: Compare deployed stack with CDK code (`cdk diff`)
- CloudFormation drift detection: Detect manual changes via AWS Console

**Deployment Process**:
```bash
# Bootstrap CDK (one-time per account/region)
cdk bootstrap aws://<account-id>/<region>

# Synthesize CloudFormation template
cdk synth NetworkStack

# Preview changes
cdk diff NetworkStack

# Deploy network stack
cdk deploy NetworkStack
```

**Acceptance Criteria**:
- [ ] All network infrastructure defined in CDK Python code
- [ ] No manual AWS Console changes (all changes via CDK)
- [ ] CDK stack deploys successfully without errors
- [ ] `cdk diff` shows no drift (deployed stack matches code)
- [ ] Stack outputs exported for cross-stack references

---

### 6.2 Deployment Automation (NFR-13)

**Applicable**: YES  
**Priority**: HIGH  
**Well-Architected Pillar**: Operational Excellence

**Requirement**: GitHub Actions CI/CD pipeline for network infrastructure deployment.

**Network Stack Deployment Pipeline**:

1. **Pipeline Stages** (network-specific):
   - **Stage 1: CDK Synth**: Generate CloudFormation template from CDK code
   - **Stage 2: CDK Diff**: Preview infrastructure changes
   - **Stage 3: Manual Approval**: Require approval for production deployments (network changes are high-risk)
   - **Stage 4: CDK Deploy**: Deploy network stack to AWS
   - **Stage 5: Smoke Tests**: Verify VPC endpoints, security groups, route tables

2. **Deployment Triggers**:
   - Trigger: Push to `main` branch with changes in `cdk/network-stack/` directory
   - Branch protection: Require PR approval before merge to `main`
   - Manual trigger: Allow manual deployment for hotfixes

3. **Deployment Safety**:
   - Change sets: CloudFormation change sets show exactly what will change
   - Rollback: CloudFormation automatic rollback on failure
   - Manual approval gate: Network changes require explicit approval

4. **GitHub Actions Workflow** (network stack):
```yaml
name: Deploy Network Stack

on:
  push:
    branches: [main]
    paths: ['cdk/network-stack/**']

jobs:
  deploy-network:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
      - name: Configure AWS credentials (OIDC)
      - name: Install CDK CLI
      - name: CDK synth
      - name: CDK diff
      - name: Manual approval (production only)
      - name: CDK deploy
      - name: Smoke tests (verify VPC endpoints)
```

**Acceptance Criteria**:
- [ ] GitHub Actions workflow deploys network stack on push to `main`
- [ ] Pipeline includes manual approval gate for production
- [ ] CDK diff output visible in pipeline logs
- [ ] Smoke tests verify VPC endpoints and connectivity
- [ ] Pipeline fails if CDK deployment fails (no silent errors)

---

### 6.3 Maintainability (NFR-15)

**Applicable**: YES  
**Priority**: MEDIUM  
**Well-Architected Pillar**: Operational Excellence

**Requirement**: Network infrastructure code must be maintainable and well-documented.

**Code Quality Standards** (network-specific):

1. **CDK Code Structure**:
   - Modular design: Separate constructs for VPC, subnets, security groups, VPC endpoints
   - Reusable constructs: Create custom constructs for common patterns
   - Type hints: Use Python type hints for all function parameters
   - Docstrings: Document all CDK constructs with purpose and parameters

2. **Configuration Management**:
   - Environment variables: VPC CIDR, AZ list, region (externalized from code)
   - CDK context: Use `cdk.json` for environment-specific configuration
   - No hardcoded values: Use constants and configuration files

3. **Documentation**:
   - Functional Design: Business logic model, domain entities, business rules
   - Infrastructure Design: CDK implementation details (future stage)
   - README: Deployment instructions, troubleshooting guide
   - Inline comments: Document complex CDK patterns

4. **Testing**:
   - CDK unit tests: Test CDK constructs generate correct CloudFormation
   - CDK snapshot tests: Detect unintended infrastructure changes
   - Integration tests: Verify deployed infrastructure (smoke tests)

**Code Review Checklist** (network stack):
- [ ] All security group rules have descriptions
- [ ] No hardcoded IPs, CIDRs, or credentials
- [ ] CDK constructs use type hints and docstrings
- [ ] Environment-specific configuration externalized
- [ ] Unit tests cover all custom CDK constructs

**Acceptance Criteria**:
- [ ] CDK code passes linting (pylint, mypy)
- [ ] CDK unit tests achieve > 80% coverage of custom constructs
- [ ] Documentation artifacts complete (functional design, README)
- [ ] Code review checklist followed for all PRs

---

## 7. Cost Optimization Requirements

### 7.1 Cost Optimization (NFR-12)

**Applicable**: YES  
**Priority**: LOW  
**Well-Architected Pillar**: Cost Optimization

**Requirement**: Operations-first approach (prioritize simplicity over cost).

**Network Cost Analysis**:

1. **VPC Costs** (monthly estimate):
   - VPC itself: Free
   - Subnets: Free
   - Internet Gateway: Free
   - Route Tables: Free
   - Security Groups: Free

2. **VPC Endpoint Costs**:
   - S3 Gateway Endpoint: Free
   - Interface Endpoints: $7.20/month per endpoint × 7 = $50.40/month
   - Data processed: $0.01 per GB (estimated 50 GB/month = $0.50/month)
   - Total VPC endpoint cost: ~$51/month

3. **Cross-AZ Data Transfer**:
   - Intra-AZ: Free
   - Cross-AZ: $0.01 per GB (estimated 10 GB/month = $0.10/month)

4. **NAT Gateway Cost Comparison** (alternative not chosen):
   - NAT Gateway: $32/month (per AZ, need 2 for HA = $64/month)
   - Data transfer: $0.045 per GB (estimated 50 GB/month = $2.25/month)
   - Total NAT Gateway cost: ~$66/month
   - Conclusion: VPC endpoints ($51/month) cheaper than NAT Gateway ($66/month)

**Cost Optimization Decisions**:

| Decision | Rationale | Cost Impact |
|----------|-----------|-------------|
| Use VPC endpoints instead of NAT Gateway | Better security, no internet egress, cheaper | Save $15/month |
| Deploy interface endpoints in both AZs | High availability (Multi-AZ) | +$50/month (necessary for HA) |
| Use S3 Gateway Endpoint (not Interface) | Gateway endpoint is free for S3 | Save $7/month |
| No VPC Flow Logs in initial deployment | High cost (~$50-100/month for busy VPC) | Save $50+/month |

**Total Network Cost**: ~$51/month (VPC endpoints only)

**Cost Monitoring**:
- AWS Cost Explorer: Track VPC endpoint costs (separate tag)
- CloudWatch metric: VPC endpoint data processed (monitor for unexpected spikes)
- Budget alert: Email if network costs exceed $100/month

**Acceptance Criteria**:
- [ ] Network infrastructure costs < $60/month (within expected range)
- [ ] Cost allocation tags applied to all network resources
- [ ] Budget alert configured for network cost overruns

---

## Summary

**Total NFRs Assessed**: 15 (11 applicable, 2 partially applicable, 2 not applicable)  
**Total Extension Rules Assessed**: 6 (all applicable)  
**Priority Breakdown**:
- CRITICAL: 6 NFRs + 4 Extension Rules = 10 requirements
- HIGH: 4 NFRs + 2 Extension Rules = 6 requirements
- MEDIUM: 3 NFRs
- LOW: 2 NFRs

**Key Findings**:

1. **Network Infrastructure is Critical to Security Posture**:
   - Private subnet architecture (no internet egress)
   - VPC endpoints for AWS service access (8 endpoints)
   - Least-privilege security groups (6 security groups)
   - TLS 1.2+ encryption enforcement

2. **Network Supports High Availability**:
   - Multi-AZ deployment (2 AZs)
   - VPC endpoints deployed in both AZs
   - IP address space supports 10x growth

3. **Network is Foundation for All Other Units**:
   - Unit 2 (Aurora), Unit 3 (ElastiCache), Unit 4 (ECS), Unit 5 (Lambda) all depend on network infrastructure
   - Security groups defined in network stack are referenced by application stacks

4. **Operations-First Approach Reflected in Costs**:
   - VPC endpoints ($51/month) more expensive than minimum viable solution
   - Prioritize security and simplicity over cost (per NFR-12)

**Next Steps**:
- Create Technology Stack document (technology-stack.md)
- Proceed to NFR Design stage to define NFR implementation patterns
- Proceed to Infrastructure Design stage to implement CDK Python code

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-12  
**Status**: Ready for Review
