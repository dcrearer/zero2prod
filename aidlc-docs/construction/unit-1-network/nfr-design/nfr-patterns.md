# NFR Patterns - Unit 1: Network Infrastructure

## Overview

This document defines the Non-Functional Requirement (NFR) implementation patterns for the network infrastructure. These patterns translate NFR requirements into specific architectural patterns, design principles, and implementation strategies.

**Scope**: NFR patterns for VPC, subnets, security groups, VPC endpoints, routing, and monitoring.

**Related Documents**:
- NFR Requirements Assessment: `/aidlc-docs/construction/unit-1-network/nfr-requirements/nfr-assessment.md`
- Requirements: `/aidlc-docs/inception/requirements/requirements.md`
- Functional Design: `/aidlc-docs/construction/unit-1-network/functional-design/`

---

## 1. Security Patterns

### 1.1 Private Networking Pattern

**NFR Addressed**: NFR-3 (Network Isolation), SECURITY-04 (Private Networking)

**Problem**: Application resources need to access AWS services without internet egress for highest security posture.

**Solution**: Private subnet architecture with VPC endpoints for AWS service access.

**Pattern Description**:

```
Internet → IGW → Public Subnet (ALB only)
                        ↓
              Private Subnet (ECS, Lambda, Aurora, ElastiCache)
                        ↓
              VPC Endpoints (S3, ECR, Logs, Secrets Manager, STS, SES, SQS)
                        ↓
              AWS Services (via PrivateLink)

NO NAT Gateway, NO internet egress from private subnets
```

**Implementation Details**:

1. **Public Subnet Isolation**:
   - Deploy ONLY Application Load Balancer in public subnets
   - Public subnets: `10.0.1.0/24` (AZ-A), `10.0.2.0/24` (AZ-B)
   - Public route table: Default route to Internet Gateway

2. **Private Subnet Isolation**:
   - Deploy application and data tier in private subnets (ECS, Lambda, Aurora, ElastiCache)
   - Private subnets: `10.0.10.0/24` (AZ-A), `10.0.11.0/24` (AZ-B)
   - Private route table: NO default route (no internet egress)
   - Local VPC route only: `10.0.0.0/16` → `local`

3. **VPC Endpoint Private Connectivity**:
   - S3 Gateway Endpoint: Free, automatic routing via route table
   - 7 Interface Endpoints: ECR API, ECR DKR, CloudWatch Logs, Secrets Manager, STS, SES, SQS
   - Private DNS enabled: AWS service DNS names resolve to private VPC IPs
   - Security group: Allow HTTPS (443) from ECS and Lambda only

**Benefits**:
- Highest security: No internet egress path from private subnets
- Data exfiltration prevention: Cannot reach public internet
- Attack surface minimization: Private subnets unreachable from internet

**Cost Impact**: VPC endpoints cost ~$51/month (7 × $7.20 interface endpoints + data transfer)

**Trade-offs**: No internet access for private subnets (intentional security constraint)

**Compliance**: SECURITY-04 (Private Networking), NFR-3 (Network Isolation highest tier)

---

### 1.2 VPC Endpoint Pattern

**NFR Addressed**: NFR-3 (Network Isolation), SECURITY-04 (Private Networking)

**Problem**: Private subnet resources need to access AWS services without NAT Gateway or internet egress.

**Solution**: VPC endpoints (Gateway and Interface) for private AWS service access.

**Pattern Description**:

```
VPC Endpoint Types:
1. Gateway Endpoint (S3): Free, route table-based, no ENI
2. Interface Endpoint (Others): $7.20/month, ENI-based, private DNS

Gateway Endpoint (S3):
  Private Route Table → S3 Prefix List → Gateway Endpoint → S3 Service

Interface Endpoint (ECR, Logs, Secrets Manager, STS, SES, SQS):
  Application → AWS SDK → DNS Resolution → VPC Endpoint Private IP → AWS Service
```

**Implementation Details**:

1. **S3 Gateway Endpoint** (Cost Optimization):
   - Service: `com.amazonaws.us-east-1.s3`
   - Type: Gateway endpoint (free)
   - Route table: Private route table only
   - Use case: ECR image pulls (ECS Fargate pulls container images from ECR via S3)

2. **Interface Endpoints** (7 services):
   - ECR API: `com.amazonaws.us-east-1.ecr.api` (ECS image metadata)
   - ECR DKR: `com.amazonaws.us-east-1.ecr.dkr` (ECS Docker registry)
   - CloudWatch Logs: `com.amazonaws.us-east-1.logs` (application logs)
   - Secrets Manager: `com.amazonaws.us-east-1.secretsmanager` (credentials)
   - STS: `com.amazonaws.us-east-1.sts` (IAM role assumption)
   - SES: `com.amazonaws.us-east-1.ses` (email sending from Lambda)
   - SQS: `com.amazonaws.us-east-1.sqs` (newsletter queue)

3. **Private DNS Configuration**:
   - Enable private DNS for all interface endpoints
   - AWS service DNS names resolve to private VPC IPs (10.0.10.X, 10.0.11.X)
   - No application code changes required (uses standard AWS SDK DNS names)

4. **Multi-AZ Deployment**:
   - Interface endpoints: Deploy in BOTH private subnets (2 ENIs per endpoint)
   - Automatic failover: DNS resolves to nearest healthy endpoint
   - High availability: Endpoint failure in one AZ does not affect other AZ

**Benefits**:
- Private connectivity: No internet egress required
- Security: VPC traffic stays within AWS backbone network
- Performance: Lower latency than NAT Gateway routing

**Cost Impact**: $51/month (7 interface endpoints × $7.20 + data transfer)

**Cost Optimization**: Use S3 Gateway Endpoint (free) instead of S3 Interface Endpoint ($7.20/month)

**Compliance**: SECURITY-04 (Private Networking), NFR-12 (Cost Optimization via Gateway endpoint)

---

### 1.3 Security Group Layering Pattern

**NFR Addressed**: SECURITY-04 (Least Privilege), SECURITY-05 (Security Group Documentation)

**Problem**: Need defense-in-depth security with least-privilege network access control.

**Solution**: Layered security groups with explicit source/destination references (no `0.0.0.0/0` except ALB ingress).

**Pattern Description**:

```
Security Group Layers:
1. Internet Layer: ALB Security Group
2. Application Layer: ECS Security Group, Lambda Security Group
3. Data Layer: Aurora Security Group, ElastiCache Security Group
4. Service Layer: VPC Endpoint Security Group

Traffic Flow:
Internet → ALB SG → ECS SG → Aurora SG
                    ↓
             VPC Endpoint SG → AWS Services
                    ↓
          Lambda SG → Aurora SG
                    ↓
          Lambda SG → VPC Endpoint SG → AWS Services
```

**Implementation Details**:

1. **ALB Security Group** (Internet Layer):
   - Ingress: HTTPS (443) from `0.0.0.0/0` (public access)
   - Ingress: HTTP (80) from `0.0.0.0/0` (redirect to HTTPS)
   - Egress: HTTP (8000) to ECS Security Group ONLY
   - Rationale: Public-facing, needs internet access

2. **ECS Security Group** (Application Layer):
   - Ingress: HTTP (8000) from ALB Security Group ONLY
   - Egress: PostgreSQL (5432) to Aurora Security Group
   - Egress: Redis (6379) to ElastiCache Security Group
   - Egress: HTTPS (443) to VPC Endpoint Security Group
   - Rationale: Application tier, needs database, cache, and AWS service access

3. **Aurora Security Group** (Data Layer):
   - Ingress: PostgreSQL (5432) from ECS Security Group
   - Ingress: PostgreSQL (5432) from Lambda Security Group
   - Egress: NONE (no outbound connections)
   - Rationale: Database tier, accepts connections only

4. **ElastiCache Security Group** (Data Layer):
   - Ingress: Redis (6379) from ECS Security Group ONLY
   - Egress: NONE (no outbound connections)
   - Rationale: Cache tier, accepts connections from web tier only

5. **Lambda Security Group** (Application Layer):
   - Ingress: NONE (event-driven, no network ingress)
   - Egress: PostgreSQL (5432) to Aurora Security Group
   - Egress: HTTPS (443) to VPC Endpoint Security Group
   - Rationale: Worker tier, needs database and AWS service access

6. **VPC Endpoint Security Group** (Service Layer):
   - Ingress: HTTPS (443) from ECS Security Group
   - Ingress: HTTPS (443) from Lambda Security Group
   - Egress: NONE (no outbound connections)
   - Rationale: Service tier, accepts HTTPS from application tier only

**Benefits**:
- Defense in depth: Multiple security layers
- Least privilege: Each security group allows ONLY required traffic
- Blast radius limitation: Compromised resource cannot access arbitrary destinations

**Documentation Requirements** (SECURITY-05):
- All security group rules documented with `description` field
- Documentation format: "Protocol from/to Source/Destination for Purpose"
- Example: "HTTPS from ECS tasks to VPC endpoints for AWS API access"

**Compliance**: SECURITY-04 (Least Privilege), SECURITY-05 (Documentation), NFR-3 (Network Isolation)

---

### 1.4 Encryption in Transit Pattern

**NFR Addressed**: NFR-5 (Encryption), SECURITY-01 (Encryption in Transit)

**Problem**: All network communications must be encrypted with TLS 1.2+ to protect data in transit.

**Solution**: TLS 1.2+ enforcement at every network layer via protocol selection and security group port restrictions.

**Pattern Description**:

```
Encryption Layers:
1. Internet → ALB: HTTPS with TLS 1.2+ (ACM certificate)
2. ALB → ECS: HTTP (TLS termination at ALB, traffic within private VPC)
3. ECS → Aurora: PostgreSQL SSL/TLS (sslmode=require)
4. ECS → ElastiCache: Redis TLS in-transit encryption
5. ECS/Lambda → VPC Endpoints: HTTPS with TLS 1.2+ (AWS SDK default)
6. Aurora Cross-AZ Replication: TLS 1.2+ (AWS managed)
```

**Implementation Details**:

1. **ALB TLS Configuration**:
   - Protocol: HTTPS only (HTTP redirects to HTTPS)
   - TLS version: TLS 1.2 minimum (disable SSLv3, TLS 1.0, TLS 1.1)
   - Certificate: ACM (AWS Certificate Manager) with automatic renewal
   - Cipher suites: AWS recommended strong ciphers

2. **ALB to ECS Traffic**:
   - Option 1: HTTP (TLS termination at ALB, traffic within private VPC)
     - Rationale: ECS tasks in private subnet, no internet exposure
     - Security: Traffic does not leave VPC, acceptable per AWS Well-Architected
   - Option 2: HTTPS end-to-end (ALB → ECS with TLS)
     - Rationale: Highest security, defense in depth
     - Trade-off: Additional certificate management, CPU overhead
   - **Decision**: Option 1 (HTTP within VPC) for initial deployment

3. **ECS to Aurora PostgreSQL**:
   - Protocol: PostgreSQL with SSL/TLS
   - TLS version: TLS 1.2+ (Aurora default)
   - Connection string: `sslmode=require` (enforce SSL)
   - Certificate validation: Aurora provides trusted certificate

4. **ECS to ElastiCache Redis**:
   - Protocol: Redis with TLS in-transit encryption
   - TLS version: TLS 1.2+
   - Configuration: ElastiCache TLS enabled, Redis client configured for TLS
   - Port: 6379 (Redis default, TLS wrapped)

5. **ECS/Lambda to VPC Endpoints**:
   - Protocol: HTTPS (AWS SDK default)
   - TLS version: TLS 1.2+ (enforced by AWS)
   - Security group: Port 443 ONLY (no port 80)
   - Private DNS: Resolves AWS service names to VPC endpoint private IPs

6. **Aurora Cross-AZ Replication**:
   - Protocol: TLS 1.2+ (AWS managed, automatic)
   - Encryption: Automatic for Multi-AZ replication traffic

**Security Group Enforcement**:
- VPC Endpoint Security Group: Allow port 443 ONLY (HTTPS)
- Aurora Security Group: Allow port 5432 ONLY (PostgreSQL SSL/TLS)
- ElastiCache Security Group: Allow port 6379 ONLY (Redis TLS)

**Benefits**:
- Data protection: All network traffic encrypted
- Compliance: Meets SECURITY-01 and NFR-5
- Industry standard: TLS 1.2+ is industry best practice

**Monitoring**:
- ALB metric: TLS negotiation errors (CloudWatch)
- Aurora slow query log: Non-SSL connections (should be 0)
- ElastiCache metric: TLS connection count

**Compliance**: SECURITY-01 (Encryption in Transit), NFR-5 (Encryption)

---

## 2. Reliability Patterns

### 2.1 Multi-AZ Pattern

**NFR Addressed**: NFR-1 (High Availability 99.9%)

**Problem**: Single availability zone failure would cause total service outage.

**Solution**: Multi-AZ deployment of all network infrastructure components.

**Pattern Description**:

```
Availability Zones:
- us-east-1a: Public Subnet 1a, Private Subnet 1a, ALB node, ECS tasks, Aurora primary, ElastiCache node, VPC endpoint ENIs
- us-east-1b: Public Subnet 1b, Private Subnet 1b, ALB node, ECS tasks, Aurora standby, ElastiCache replica, VPC endpoint ENIs

Failure Scenario:
- AZ-A fails → Traffic routes to AZ-B resources automatically
- ALB: Routes to healthy targets in AZ-B (< 2 minutes)
- Aurora: Fails over to standby in AZ-B (< 30 seconds)
- VPC Endpoints: DNS resolves to ENI in AZ-B (< 1 minute)
```

**Implementation Details**:

1. **Subnet Distribution**:
   - Public Subnet 1: `10.0.1.0/24` in `us-east-1a`
   - Public Subnet 2: `10.0.2.0/24` in `us-east-1b`
   - Private Subnet 1: `10.0.10.0/24` in `us-east-1a`
   - Private Subnet 2: `10.0.11.0/24` in `us-east-1b`

2. **Application Load Balancer Multi-AZ**:
   - ALB nodes: Deployed in both public subnets (automatic by AWS)
   - Health checks: Monitor ECS task health in both AZs
   - Traffic distribution: Round-robin across healthy targets in all AZs
   - AZ failure: ALB stops routing to failed AZ automatically

3. **VPC Endpoint Multi-AZ**:
   - Interface endpoints: 2 ENIs per endpoint (one in each private subnet)
   - DNS resolution: Automatically routes to nearest healthy ENI
   - AZ failure: DNS resolves to ENI in healthy AZ
   - Total ENIs: 7 endpoints × 2 AZs = 14 ENIs

4. **Resource Distribution**:
   - ECS tasks: Spread across both AZs (ECS placement strategy)
   - Lambda functions: ENIs in both AZs (AWS Hyperplane automatic)
   - Aurora: Primary in AZ-A, standby in AZ-B (automatic failover)
   - ElastiCache: Primary in AZ-A, replica in AZ-B (automatic failover)

**Availability Calculation**:
- ALB: 99.99% (AWS SLA)
- VPC: 99.99% (regional service)
- VPC Interface Endpoints: 99.95% (AWS SLA)
- Aurora Multi-AZ: 99.95% (AWS SLA)
- Combined: ~99.9% (conservative estimate)

**Benefits**:
- Fault tolerance: Single AZ failure does not cause outage
- Automatic recovery: AWS services handle failover automatically
- No manual intervention: Failover completes within 2 minutes

**Failure Testing**: Simulate AZ failure by shutting down resources in one AZ, verify service continuity

**Compliance**: NFR-1 (High Availability 99.9%)

---

### 2.2 Subnet Redundancy Pattern

**NFR Addressed**: NFR-1 (High Availability), NFR-11 (Scalability)

**Problem**: Need redundant subnets to ensure availability and sufficient IP address space.

**Solution**: Deploy 2 subnets per type (public/private) across 2 AZs with adequate IP capacity.

**Pattern Description**:

```
Subnet Redundancy:
- Public Subnets: 2 × /24 (256 addresses each) = 512 addresses total
- Private Subnets: 2 × /24 (256 addresses each) = 512 addresses total

IP Usage (per subnet):
- AWS reserved: 5 addresses (first 4 + broadcast)
- Current usage: ~24 addresses (ALB, ECS, Aurora, ElastiCache, VPC endpoints)
- Available capacity: ~227 addresses (89% free)
- Growth headroom: 10x scale (24 → 240 resources)
```

**Implementation Details**:

1. **Public Subnet Redundancy**:
   - Public Subnet 1a: `10.0.1.0/24` (256 addresses)
   - Public Subnet 1b: `10.0.2.0/24` (256 addresses)
   - Resources: ALB nodes (2 per AZ = 4 total)
   - Utilization: 2.7% (7 / 256 addresses)

2. **Private Subnet Redundancy**:
   - Private Subnet 1a: `10.0.10.0/24` (256 addresses)
   - Private Subnet 1b: `10.0.11.0/24` (256 addresses)
   - Resources: ECS tasks (10 max), Lambda ENIs (20 max), Aurora (1), ElastiCache (1), VPC endpoint ENIs (7)
   - Utilization: 9.4% (24 / 256 addresses)

3. **IP Address Scalability**:
   - Current capacity: 256 addresses per subnet
   - Current usage: ~24 addresses per private subnet
   - Available capacity: ~232 addresses per private subnet
   - Growth headroom: 10x scale (240 resources per subnet)

4. **Reserved CIDR Space** (for future expansion):
   - `10.0.3.0/24` to `10.0.9.0/24`: Reserved for additional public subnets
   - `10.0.12.0/24` to `10.0.255.0/24`: Reserved for additional private subnets
   - Total reserved: 61,952 addresses

**Benefits**:
- Redundancy: Each subnet has a pair in another AZ
- Scalability: 10x growth capacity without CIDR expansion
- Flexibility: Can add new subnets without VPC reconfiguration

**Monitoring**:
- CloudWatch metric: Available IPs per subnet
- Warning threshold: < 100 available IPs (39% utilization)
- Critical threshold: < 50 available IPs (80% utilization)

**Compliance**: NFR-1 (High Availability), NFR-11 (Scalability)

---

### 2.3 Internet Gateway High Availability

**NFR Addressed**: NFR-1 (High Availability)

**Problem**: Internet Gateway must remain available for public ALB access.

**Solution**: AWS-managed Internet Gateway with built-in high availability.

**Pattern Description**:

```
Internet Gateway:
- AWS-managed: Horizontally scaled, redundant, highly available
- VPC attachment: Single IGW per VPC (AWS design)
- Availability: 99.99+ (no single point of failure)
- Failure: Automatic failover within AWS (no manual action)

Public Route Table:
- Default route: 0.0.0.0/0 → Internet Gateway
- Redundancy: IGW is highly available (AWS managed)
- Failover: Automatic (no manual intervention)
```

**Implementation Details**:

1. **Internet Gateway Configuration**:
   - Attachment: Single IGW attached to VPC
   - High availability: AWS-managed redundancy (no customer configuration)
   - Failover: Automatic within AWS infrastructure

2. **Public Route Table Configuration**:
   - Route: `0.0.0.0/0` → Internet Gateway
   - Subnet associations: Both public subnets (Multi-AZ)
   - Automatic failover: AWS handles IGW routing changes

**Benefits**:
- No single point of failure: IGW is horizontally scaled
- Automatic recovery: AWS manages failover
- No customer maintenance: Fully managed service

**Compliance**: NFR-1 (High Availability)

---

## 3. Performance Patterns

### 3.1 VPC Endpoint Routing Optimization Pattern

**NFR Addressed**: NFR-9 (API Latency < 200ms p95)

**Problem**: Network latency must be minimized to meet API response time targets.

**Solution**: Same-AZ VPC endpoint placement with private DNS for lowest latency routing.

**Pattern Description**:

```
VPC Endpoint Placement:
- Interface endpoints: 2 ENIs per endpoint (one in each AZ)
- DNS resolution: Routes to nearest ENI in same AZ as requester
- Same-AZ latency: < 1ms (VPC internal routing)
- Cross-AZ latency: < 2ms (acceptable fallback)

Latency Budget:
- ALB → ECS (same AZ): < 1ms
- ECS → Aurora (same AZ): < 1ms
- ECS → VPC Endpoint (same AZ): < 1ms
- ECS → ElastiCache (same AZ): < 1ms
- Total network latency: < 10ms (leaves 190ms for application processing)
```

**Implementation Details**:

1. **Interface Endpoint Multi-AZ Deployment**:
   - Deploy interface endpoints in BOTH private subnets
   - Private DNS enabled: Automatically routes to nearest ENI
   - Same-AZ preference: DNS resolves to ENI in same AZ as requester

2. **Gateway Endpoint (S3) Optimization**:
   - Route table-based: No ENI, no AZ placement
   - Routing: Automatic via route table S3 prefix list
   - Performance: < 5ms for ECR image pulls

3. **Network Latency Monitoring**:
   - X-Ray traces: Capture end-to-end latency including network hops
   - CloudWatch metric: VPC endpoint response time (if available)
   - Target: Network latency < 10ms per request

**Benefits**:
- Low latency: Same-AZ routing minimizes network hops
- High availability: Cross-AZ failover if AZ fails
- Automatic optimization: DNS routing handled by AWS

**Compliance**: NFR-9 (API Latency < 200ms p95)

---

### 3.2 Security Group Stateful Connection Tracking Pattern

**NFR Addressed**: NFR-9 (API Latency), NFR-15 (Maintainability)

**Problem**: Need efficient network access control without impacting latency.

**Solution**: Security groups with stateful connection tracking (automatic return traffic).

**Pattern Description**:

```
Security Group Statefulness:
- Ingress rule: Allow inbound traffic on specific port
- Egress rule: Allow outbound traffic on specific port
- Return traffic: Automatically allowed (stateful tracking)
- No explicit return rules needed: Simplifies configuration

Example:
- ECS Security Group egress: Allow PostgreSQL (5432) to Aurora SG
- Aurora Security Group ingress: Allow PostgreSQL (5432) from ECS SG
- Return traffic: Automatically allowed (no additional rules)
```

**Implementation Details**:

1. **Stateful Connection Tracking**:
   - Security groups track connection state
   - Return traffic automatically allowed
   - No need for explicit return rules (unlike Network ACLs)

2. **Performance Benefit**:
   - No Network ACL evaluation: Security groups only (fewer checks)
   - Stateful tracking: Faster than stateless ACL evaluation
   - Lower latency: Reduced packet processing overhead

3. **Maintainability Benefit**:
   - Simpler rules: No return traffic rules needed
   - Less error-prone: Automatic return traffic handling
   - Easier troubleshooting: Fewer rules to audit

**Benefits**:
- Performance: Lower latency than Network ACLs
- Simplicity: Fewer rules to manage
- Reliability: Less risk of misconfiguration

**Compliance**: NFR-9 (API Latency), NFR-15 (Maintainability)

---

## 4. Scalability Patterns

### 4.1 IP Address Space Planning Pattern

**NFR Addressed**: NFR-11 (Scalability), NFR-1 (High Availability)

**Problem**: IP address space must support current and future resource scaling.

**Solution**: Right-sized subnets with 10x growth capacity and reserved CIDR space.

**Pattern Description**:

```
IP Address Planning:
1. Calculate current IP requirements
2. Apply 10x growth factor
3. Size subnets to accommodate growth
4. Reserve additional CIDR space for new subnets

Current Usage:
- Public subnets: 4 IPs (ALB nodes)
- Private subnets: 24 IPs per AZ (ECS, Aurora, ElastiCache, VPC endpoints)

Growth Capacity:
- Public subnets: 256 addresses (64x current usage)
- Private subnets: 256 addresses (10.7x current usage)
- Reserved CIDR: 61,952 addresses (future expansion)
```

**Implementation Details**:

1. **Current IP Usage Calculation**:
   - Public Subnet 1a: 2 ALB + 5 AWS reserved = 7 IPs
   - Public Subnet 1b: 2 ALB + 5 AWS reserved = 7 IPs
   - Private Subnet 1a: 19 resources + 5 AWS reserved = 24 IPs
   - Private Subnet 1b: 19 resources + 5 AWS reserved = 24 IPs

2. **Subnet Sizing**:
   - All subnets: `/24` (256 addresses)
   - Public utilization: 2.7% (plenty of headroom)
   - Private utilization: 9.4% (supports 10x growth)

3. **Reserved CIDR Space**:
   - VPC CIDR: `10.0.0.0/16` (65,536 addresses)
   - Used CIDRs: `10.0.1.0/24`, `10.0.2.0/24`, `10.0.10.0/24`, `10.0.11.0/24`
   - Reserved: `10.0.3.0/24` to `10.0.255.0/24` (61,952 addresses)

4. **Growth Strategy**:
   - Phase 1: Scale within existing subnets (10x capacity)
   - Phase 2: Add new subnets if utilization > 80%
   - Phase 3: VPC peering or transit gateway for multi-VPC growth

**Benefits**:
- Scalability: 10x growth without CIDR changes
- Flexibility: Can add new subnets without reconfiguration
- Future-proof: Massive reserved capacity

**Monitoring**:
- CloudWatch metric: Available IPs per subnet
- Warning threshold: < 100 available IPs
- Critical threshold: < 50 available IPs

**Compliance**: NFR-11 (Scalability)

---

### 4.2 CIDR Reservation Strategy Pattern

**NFR Addressed**: NFR-11 (Scalability), NFR-2 (Disaster Recovery)

**Problem**: Need to reserve IP address space for future growth and disaster recovery.

**Solution**: Strategic CIDR block allocation with reserved ranges.

**Pattern Description**:

```
CIDR Allocation Strategy:
- VPC CIDR: 10.0.0.0/16 (65,536 addresses)
- Active subnets: 10.0.1.0/24, 10.0.2.0/24, 10.0.10.0/24, 10.0.11.0/24 (1,024 addresses)
- Reserved: 10.0.3.0/24 to 10.0.255.0/24 (61,952 addresses)

Reservation Categories:
- Public subnet expansion: 10.0.3.0/24 to 10.0.9.0/24 (7 × 256 = 1,792 addresses)
- Private subnet expansion: 10.0.12.0/24 to 10.0.50.0/24 (39 × 256 = 9,984 addresses)
- DR region: Same CIDR in DR VPC (separate VPC, no peering)
- Future use: 10.0.51.0/24 to 10.0.255.0/24 (52,224 addresses)
```

**Implementation Details**:

1. **CIDR Block Selection**:
   - Primary VPC: `10.0.0.0/16` (RFC 1918 private address)
   - DR VPC: `10.0.0.0/16` (separate VPC in DR region, no conflict)

2. **Subnet Naming Convention**:
   - Public: `10.0.<odd>.0/24` (10.0.1.0, 10.0.3.0, 10.0.5.0, etc.)
   - Private: `10.0.<even>.0/24` starting at 10 (10.0.10.0, 10.0.12.0, 10.0.14.0, etc.)

3. **Reserved CIDR Documentation**:
   - Document reserved CIDR ranges in VPC design document
   - Tag reserved CIDRs as "Reserved for Future Use"
   - Prevent accidental allocation

**Benefits**:
- Future expansion: 64,000+ addresses reserved
- DR readiness: Same CIDR in DR region (independent VPC)
- Consistency: Structured naming convention

**Compliance**: NFR-11 (Scalability), NFR-2 (Disaster Recovery)

---

## 5. Observability Patterns

### 5.1 CloudWatch Metrics for VPC Pattern

**NFR Addressed**: NFR-7 (Observability), NFR-8 (Alerting)

**Problem**: Need visibility into network resource utilization and performance.

**Solution**: CloudWatch metrics and alarms for VPC resources.

**Pattern Description**:

```
VPC Metrics:
1. Available IPs per subnet (AWS-provided)
2. VPC endpoint data processed (interface endpoints)
3. ALB metrics (request count, latency, error rates)

Alarms:
1. Available IPs < 50: Critical (80% utilization)
2. VPC endpoint data > 100 GB/month: Cost warning
3. ALB unhealthy targets > 0: Service degradation
```

**Implementation Details**:

1. **Available IP Monitoring**:
   - Metric: `AvailableIPAddressCount` per subnet (AWS-provided)
   - Dashboard: Show available IPs for all 4 subnets
   - Alarm: Alert if available IPs < 50 (indicates approaching exhaustion)

2. **VPC Endpoint Data Monitoring**:
   - Metric: `DataProcessed` per interface endpoint (AWS-provided)
   - Dashboard: Show monthly data processed per endpoint
   - Cost tracking: Alert if monthly data > 100 GB (indicates unusual traffic)

3. **ALB Monitoring** (application-level, included for completeness):
   - Metric: `HealthyHostCount`, `RequestCount`, `TargetResponseTime`, `HTTPCode_Target_5XX_Count`
   - Dashboard: Operational dashboard includes ALB metrics
   - Alarms: Critical alerts for unhealthy targets and high error rates

4. **VPC Flow Logs** (optional, not in initial scope):
   - Use case: Security forensics, troubleshooting connectivity issues
   - Destination: CloudWatch Logs or S3
   - Cost: ~$0.50 per GB ingested (can be expensive)
   - Decision: Enable only if connectivity issues arise

**Benefits**:
- Visibility: Monitor network resource utilization
- Proactive alerting: Detect IP exhaustion before it blocks scaling
- Cost tracking: Monitor VPC endpoint data transfer costs

**Monitoring Dashboard**:
- Metric: Available IPs per subnet (line chart)
- Metric: VPC endpoint data processed (bar chart)
- Metric: ALB healthy targets (gauge)

**Compliance**: NFR-7 (Observability), NFR-8 (Alerting)

---

### 5.2 Tagging Strategy Pattern

**NFR Addressed**: NFR-12 (Cost Optimization), NFR-15 (Maintainability)

**Problem**: Need to track network resource costs and ownership.

**Solution**: Consistent tagging strategy for all network resources.

**Pattern Description**:

```
Required Tags:
- Name: Human-readable resource name
- Project: "zero2prod"
- Environment: "production" | "staging" | "development"
- ManagedBy: "CDK"
- CostCenter: "network-infrastructure"

Optional Tags:
- Owner: Team or individual responsible
- Backup: "true" | "false" (if applicable)
- Compliance: "SECURITY-04" (if security-related)
```

**Implementation Details**:

1. **VPC Tags**:
   - Name: `zero2prod-vpc`
   - Project: `zero2prod`
   - Environment: `production`
   - ManagedBy: `CDK`

2. **Subnet Tags**:
   - Name: `zero2prod-public-1a`, `zero2prod-private-1a`, etc.
   - Type: `Public` | `Private`
   - AZ: `us-east-1a` | `us-east-1b`

3. **Security Group Tags**:
   - Name: `zero2prod-alb-sg`, `zero2prod-ecs-sg`, etc.
   - Purpose: `ALB internet-facing traffic`, `ECS task traffic`, etc.

4. **VPC Endpoint Tags**:
   - Name: `zero2prod-s3-gateway-endpoint`, `zero2prod-ecr-api-endpoint`, etc.
   - Service: `s3`, `ecr-api`, `logs`, etc.

**Benefits**:
- Cost allocation: Track network costs by project and environment
- Resource management: Identify and organize resources
- Compliance: Tag security-related resources

**Cost Tracking**:
- AWS Cost Explorer: Filter by `CostCenter=network-infrastructure`
- Monthly cost breakdown: VPC endpoints, data transfer, etc.

**Compliance**: NFR-12 (Cost Optimization), NFR-15 (Maintainability)

---

## 6. Cost Optimization Patterns

### 6.1 VPC Endpoint Selection Pattern (Gateway vs Interface)

**NFR Addressed**: NFR-12 (Cost Optimization)

**Problem**: VPC endpoints have different pricing models (gateway vs interface).

**Solution**: Use gateway endpoints where available (free), interface endpoints only when required.

**Pattern Description**:

```
VPC Endpoint Selection:
- Gateway Endpoint: Free, route table-based, limited services (S3, DynamoDB)
- Interface Endpoint: $7.20/month per endpoint, ENI-based, all other services

Decision Tree:
- S3 access required? → Gateway Endpoint (free)
- DynamoDB access required? → Gateway Endpoint (free)
- Other AWS service? → Interface Endpoint ($7.20/month)

Cost Comparison:
- S3 Gateway Endpoint: $0/month
- S3 Interface Endpoint: $7.20/month (avoided via gateway)
- Savings: $7.20/month per service
```

**Implementation Details**:

1. **S3 Gateway Endpoint**:
   - Service: `com.amazonaws.us-east-1.s3`
   - Type: Gateway endpoint
   - Cost: $0/month (free)
   - Use case: ECR image pulls (ECS Fargate)

2. **Interface Endpoints** (required, no gateway alternative):
   - ECR API, ECR DKR, CloudWatch Logs, Secrets Manager, STS, SES, SQS
   - Cost: 7 × $7.20/month = $50.40/month
   - Data transfer: $0.01 per GB (estimated $0.50/month)

3. **Total VPC Endpoint Cost**:
   - Interface endpoints: $50.40/month
   - Data transfer: $0.50/month
   - Total: $51/month

**Cost Savings**:
- S3 Gateway Endpoint (free) vs S3 Interface Endpoint ($7.20/month): Save $7.20/month
- Total savings: $7.20/month by using gateway endpoint

**Cost Comparison with NAT Gateway**:
- NAT Gateway: $32/month per AZ × 2 AZs = $64/month
- NAT data transfer: $0.045 per GB × 50 GB/month = $2.25/month
- Total NAT cost: $66/month
- VPC endpoints cost: $51/month
- Savings: $15/month by using VPC endpoints instead of NAT Gateway

**Benefits**:
- Cost optimization: Use free gateway endpoints where possible
- Security: VPC endpoints more secure than NAT Gateway
- Operations: No NAT Gateway to manage

**Compliance**: NFR-12 (Cost Optimization)

---

### 6.2 No NAT Gateway Pattern

**NFR Addressed**: NFR-12 (Cost Optimization), NFR-3 (Network Isolation)

**Problem**: NAT Gateway adds cost ($32/month per AZ + data transfer) and reduces security.

**Solution**: Use VPC endpoints for AWS service access, no NAT Gateway.

**Pattern Description**:

```
No NAT Gateway Architecture:
- Private subnets: NO internet egress
- AWS service access: Via VPC endpoints ONLY
- Cost savings: $32/month per AZ (2 AZs = $64/month)
- Security: No internet egress path

Comparison:
- With NAT Gateway: $66/month (NAT + data transfer)
- With VPC Endpoints: $51/month (interface endpoints + data transfer)
- Savings: $15/month
```

**Implementation Details**:

1. **NAT Gateway NOT Deployed**:
   - Private route table: NO NAT Gateway route
   - Private subnets: NO internet egress
   - AWS services: Accessed via VPC endpoints

2. **VPC Endpoint Coverage**:
   - All required AWS services have VPC endpoints
   - Private DNS enabled: Application code unchanged
   - No internet access needed: Application fully functional

**Cost Breakdown**:
- NAT Gateway: $32/month per AZ × 2 = $64/month (avoided)
- NAT data transfer: $0.045 per GB (avoided)
- VPC endpoints: $51/month (required)
- Net savings: $13/month

**Security Benefit**:
- No internet egress: Cannot reach public internet from private subnets
- Data exfiltration prevention: No path for data to leave VPC
- Attack surface reduction: No NAT Gateway to secure

**Compliance**: NFR-12 (Cost Optimization), NFR-3 (Network Isolation highest tier)

---

## Summary

This document defines 17 NFR implementation patterns across 6 categories:

1. **Security Patterns** (4 patterns):
   - Private Networking Pattern (NFR-3, SECURITY-04)
   - VPC Endpoint Pattern (NFR-3, SECURITY-04)
   - Security Group Layering Pattern (SECURITY-04, SECURITY-05)
   - Encryption in Transit Pattern (NFR-5, SECURITY-01)

2. **Reliability Patterns** (3 patterns):
   - Multi-AZ Pattern (NFR-1)
   - Subnet Redundancy Pattern (NFR-1, NFR-11)
   - Internet Gateway High Availability (NFR-1)

3. **Performance Patterns** (2 patterns):
   - VPC Endpoint Routing Optimization Pattern (NFR-9)
   - Security Group Stateful Connection Tracking Pattern (NFR-9, NFR-15)

4. **Scalability Patterns** (2 patterns):
   - IP Address Space Planning Pattern (NFR-11, NFR-1)
   - CIDR Reservation Strategy Pattern (NFR-11, NFR-2)

5. **Observability Patterns** (2 patterns):
   - CloudWatch Metrics for VPC Pattern (NFR-7, NFR-8)
   - Tagging Strategy Pattern (NFR-12, NFR-15)

6. **Cost Optimization Patterns** (2 patterns):
   - VPC Endpoint Selection Pattern (NFR-12)
   - No NAT Gateway Pattern (NFR-12, NFR-3)

**Key Takeaways**:
- Private networking via VPC endpoints is the foundation for security
- Multi-AZ deployment ensures 99.9% availability
- Right-sized subnets support 10x growth
- VPC endpoints are cheaper than NAT Gateway ($15/month savings)
- Security group layering provides defense in depth

**Next Steps**: Proceed to Logical Components document to define component architecture.

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-12  
**Status**: Ready for Review
