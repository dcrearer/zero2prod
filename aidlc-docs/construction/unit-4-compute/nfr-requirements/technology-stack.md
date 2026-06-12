# Unit 4: Compute Infrastructure - Technology Stack Decisions

## Overview

This document records all technology stack decisions for the ECS Fargate compute infrastructure, including rationale, alternatives considered, and traceability to NFR requirements.

**Decision Date**: 2026-06-12  
**Unit**: 4 of 8 (Compute Infrastructure)  
**Total Decisions**: 12

---

## Decision 1: Container Orchestration Platform

**Decision**: **AWS ECS Fargate**

**Alternatives Considered**:
- A. AWS ECS Fargate (selected)
- B. AWS ECS EC2 (self-managed instances)
- C. Amazon EKS (Kubernetes)
- D. AWS App Runner (simpler PaaS)

**Rationale**:
- **Serverless**: No EC2 instance management required
- **AWS Integration**: Native integration with ALB, Secrets Manager, CloudWatch, X-Ray
- **Cost**: Pay only for task runtime (no idle capacity costs)
- **Simplicity**: Simpler than Kubernetes (EKS) for monolithic application
- **Proven**: Mature service with 99.99% availability SLA

**Why Not Alternatives**:
- **ECS EC2**: Requires EC2 instance management, patching, scaling (operational overhead)
- **EKS**: Overkill for monolithic application, higher complexity, higher cost
- **App Runner**: Less control over networking, security groups, load balancing

**NFR Support**:
- NFR-1 (Scalability): Auto-scaling based on CPU/memory metrics
- NFR-2 (Performance): Right-sized tasks (1 vCPU / 2 GB)
- NFR-3 (Availability): Multi-AZ deployment, auto-healing
- NFR-7 (Cost): Pay-per-use pricing, no idle capacity

**Traceability**: Unit of Work specification, AWS modernization goals

---

## Decision 2: Load Balancer

**Decision**: **Application Load Balancer (ALB)**

**Alternatives Considered**:
- A. Application Load Balancer (selected)
- B. Network Load Balancer (NLB)
- C. Classic Load Balancer (CLB, deprecated)
- D. API Gateway + Lambda (serverless alternative)

**Rationale**:
- **Layer 7**: HTTP/HTTPS routing with path/header-based rules
- **TLS Termination**: Offloads TLS from application (ACM certificate integration)
- **Health Checks**: Application-level health checks (HTTP /health_check)
- **Target Groups**: Native integration with ECS Fargate
- **Access Logs**: S3 logging for audit and troubleshooting

**Why Not Alternatives**:
- **NLB**: Layer 4 (TCP/UDP) not needed, no HTTP routing, no TLS termination
- **CLB**: Deprecated, lacks modern features
- **API Gateway**: Higher latency, higher cost, designed for serverless functions

**NFR Support**:
- NFR-2 (Performance): Connection pooling, efficient routing
- NFR-3 (Availability): Multi-AZ, auto-healing targets
- NFR-4 (Security): TLS 1.2+ enforcement, access logs

**Traceability**: BR-COMPUTE-001 to BR-COMPUTE-005, User Decision Q1

---

## Decision 3: Container Registry

**Decision**: **Amazon ECR (Elastic Container Registry)**

**Alternatives Considered**:
- A. Amazon ECR (selected)
- B. Docker Hub (public registry)
- C. GitHub Container Registry
- D. Self-hosted registry (Harbor, etc.)

**Rationale**:
- **AWS Integration**: Native ECS integration, IAM authentication
- **Image Scanning**: Automatic vulnerability scanning on push
- **Immutable Tags**: Prevent tag overwrites (reproducibility)
- **Lifecycle Policies**: Automatic cleanup of old images
- **Private**: Images not publicly accessible

**Why Not Alternatives**:
- **Docker Hub**: Public (security risk), rate limiting, no AWS integration
- **GitHub Container Registry**: Requires GitHub authentication, less AWS integration
- **Self-hosted**: Operational overhead, patching, scaling

**NFR Support**:
- NFR-4 (Security): Image scanning, private registry, IAM authentication
- NFR-6 (Maintainability): Immutable tags, lifecycle policies
- NFR-7 (Cost): Pay per GB storage (~$0.10/GB/month)

**Traceability**: BR-COMPUTE-031 to BR-COMPUTE-033, User Decision Q6

---

## Decision 4: CI/CD Platform

**Decision**: **GitHub Actions**

**Alternatives Considered**:
- A. GitHub Actions (selected)
- B. AWS CodePipeline + CodeBuild
- C. Jenkins (self-hosted)
- D. GitLab CI/CD

**Rationale**:
- **GitHub Integration**: Native integration with source code repository
- **OIDC Authentication**: Secure AWS access without long-lived credentials
- **Free Tier**: Free for public repos, low cost for private repos
- **Workflow as Code**: `.github/workflows/*.yml` version-controlled
- **Mature Ecosystem**: Large marketplace of pre-built actions

**Why Not Alternatives**:
- **CodePipeline**: Higher cost, more complex setup, AWS-specific
- **Jenkins**: Self-hosted (operational overhead), patching, scaling
- **GitLab CI/CD**: Requires GitLab (source code on GitHub)

**NFR Support**:
- NFR-6 (Maintainability): Automated builds, <5 min deployment
- NFR-7 (Cost): Low cost (~$1-2/month for builds)

**Traceability**: BR-COMPUTE-033, User Decision Q6, Clarification Q2

---

## Decision 5: Secrets Management

**Decision**: **AWS Secrets Manager**

**Alternatives Considered**:
- A. AWS Secrets Manager (selected)
- B. AWS Systems Manager Parameter Store
- C. HashiCorp Vault (self-hosted)
- D. Environment variables in task definition (hardcoded)

**Rationale**:
- **Automatic Rotation**: Built-in rotation for RDS passwords
- **Encryption**: KMS encryption at rest and in transit
- **Auditing**: CloudTrail logs all secret access
- **ECS Integration**: Native ECS task definition integration
- **Versioning**: Automatic versioning of secret values

**Why Not Alternatives**:
- **Parameter Store**: No automatic rotation (manual), lower cost but less features
- **Vault**: Self-hosted (operational overhead), patching, high availability
- **Hardcoded**: Security risk, no rotation, difficult to update

**NFR Support**:
- NFR-4 (Security): No hardcoded secrets, encryption, rotation, audit
- NFR-5 (Reliability): Automatic secret rotation without downtime
- NFR-7 (Cost): $0.40/secret/month (low cost)

**Traceability**: BR-COMPUTE-025, BR-COMPUTE-027, User Decision Q7, SECURITY-03

---

## Decision 6: Observability - Logging

**Decision**: **Amazon CloudWatch Logs**

**Alternatives Considered**:
- A. Amazon CloudWatch Logs (selected)
- B. AWS CloudWatch Logs + Firehose → S3
- C. ELK Stack (Elasticsearch, Logstash, Kibana)
- D. Splunk (third-party)

**Rationale**:
- **AWS Integration**: Native ECS Fargate integration
- **Structured Logging**: JSON logs supported
- **Log Insights**: Built-in query language (SQL-like)
- **Retention**: Configurable retention (30 days selected)
- **Cost**: $0.50/GB ingested + $0.03/GB storage

**Why Not Alternatives**:
- **Firehose → S3**: Additional cost, complexity, query latency (batch processing)
- **ELK Stack**: Self-hosted (operational overhead), high cost, complex
- **Splunk**: High cost ($150+/GB/month), overkill for moderate traffic

**NFR Support**:
- NFR-5 (Reliability): Centralized logging for troubleshooting
- NFR-6 (Maintainability): 30-day retention, Log Insights queries
- NFR-7 (Cost): ~$2.50/month (5 GB logs)

**Traceability**: BR-COMPUTE-034, User Decision Q9

---

## Decision 7: Observability - Distributed Tracing

**Decision**: **AWS X-Ray**

**Alternatives Considered**:
- A. AWS X-Ray (selected)
- B. Jaeger (open-source)
- C. Zipkin (open-source)
- D. Datadog APM (third-party)

**Rationale**:
- **AWS Integration**: Native integration with ALB, ECS, Aurora, ElastiCache
- **Service Map**: Visualize request flows across services
- **Trace Analysis**: Identify slow requests, errors, bottlenecks
- **Low Overhead**: Minimal application code changes
- **Cost**: First 100,000 traces/month free

**Why Not Alternatives**:
- **Jaeger**: Self-hosted (operational overhead), no AWS integration
- **Zipkin**: Self-hosted, less mature than Jaeger
- **Datadog**: High cost ($15+/host/month), requires agent

**NFR Support**:
- NFR-2 (Performance): Identify slow requests, optimize bottlenecks
- NFR-5 (Reliability): Diagnose errors and failures
- NFR-7 (Cost): $0 (within free tier for <10k traces/month)

**Traceability**: BR-COMPUTE-029, Clarification Q3

---

## Decision 8: Auto-Scaling Mechanism

**Decision**: **AWS Application Auto Scaling (Target Tracking)**

**Alternatives Considered**:
- A. Target Tracking Scaling (selected)
- B. Step Scaling
- C. Scheduled Scaling
- D. Manual Scaling (no auto-scaling)

**Rationale**:
- **Automatic**: Adjusts capacity to maintain target CPU utilization
- **Simple**: Single metric (CPU) easy to configure and understand
- **Gradual**: Scales incrementally (1 task at a time)
- **Predictable**: Target 70% CPU provides consistent behavior

**Why Not Alternatives**:
- **Step Scaling**: More complex, requires multiple CloudWatch alarms
- **Scheduled Scaling**: Traffic patterns not predictable enough
- **Manual Scaling**: Requires human intervention, slower response

**NFR Support**:
- NFR-1 (Scalability): Automatic scaling 2-10 tasks based on demand
- NFR-7 (Cost): Scales down during low traffic (cost optimization)

**Traceability**: BR-COMPUTE-013 to BR-COMPUTE-018, User Decision Q3

---

## Decision 9: Deployment Strategy

**Decision**: **ECS Rolling Update**

**Alternatives Considered**:
- A. ECS Rolling Update (selected)
- B. Blue/Green Deployment (CodeDeploy)
- C. Canary Deployment
- D. In-place Update (downtime)

**Rationale**:
- **Zero Downtime**: 100% minimum healthy ensures service availability
- **Simple**: No additional services (CodeDeploy) required
- **Automatic Rollback**: Stops deployment if health checks fail
- **Cost-Effective**: No additional infrastructure during deployment

**Why Not Alternatives**:
- **Blue/Green**: More complex, requires CodeDeploy, higher cost (double capacity longer)
- **Canary**: Requires CodeDeploy, traffic splitting, more complex validation
- **In-place**: Downtime unacceptable for production

**NFR Support**:
- NFR-3 (Availability): 0 seconds downtime during deployments
- NFR-6 (Maintainability): Simple deployment process, <5 min deployment time

**Traceability**: BR-COMPUTE-019 to BR-COMPUTE-024, User Decision Q8

---

## Decision 10: Network Mode

**Decision**: **awsvpc (VPC Mode)**

**Alternatives Considered**:
- A. awsvpc (selected)
- B. bridge (shared network namespace)
- C. host (host network namespace)

**Rationale**:
- **Required**: Only network mode supported by Fargate
- **Isolation**: Each task gets own ENI and private IP address
- **Security Groups**: Task-level security group assignment
- **Performance**: No network virtualization overhead

**Why Not Alternatives**:
- **bridge**: Not supported by Fargate
- **host**: Not supported by Fargate, security risk (shared network)

**NFR Support**:
- NFR-4 (Security): Task-level network isolation, security groups
- NFR-2 (Performance): Direct network access, no overhead

**Traceability**: Task Definition entity, Fargate requirement

---

## Decision 11: IAM Authentication Strategy

**Decision**: **Secrets Manager Password Authentication** (not IAM database authentication)

**Alternatives Considered**:
- A. Secrets Manager Password Authentication (selected)
- B. IAM Database Authentication
- C. Hardcoded Password (not acceptable)

**Rationale**:
- **Simplicity**: Standard password authentication (no additional setup)
- **Rotation**: Secrets Manager supports automatic rotation
- **Compatibility**: Works with all PostgreSQL clients
- **No Additional Latency**: No IAM token generation overhead

**Why Not Alternatives**:
- **IAM Database Authentication**: More complex, requires RDS modification, token expiration (15 min), minimal security benefit over Secrets Manager
- **Hardcoded**: Security risk, violates SECURITY-03

**NFR Support**:
- NFR-4 (Security): No hardcoded passwords, automatic rotation
- NFR-2 (Performance): No IAM token generation latency

**Traceability**: User Decision Q5 (follow-up), BR-COMPUTE-025

---

## Decision 12: Task Resource Allocation

**Decision**: **1 vCPU / 2 GB RAM**

**Alternatives Considered**:
- A. 0.5 vCPU / 1 GB RAM
- B. 1 vCPU / 2 GB RAM (selected)
- C. 2 vCPU / 4 GB RAM
- D. 4 vCPU / 8 GB RAM

**Rationale**:
- **Performance**: Adequate for moderate traffic (100-500 req/min)
- **Headroom**: 70% CPU target = 30% headroom for spikes
- **Connection Pools**: 2 GB RAM sufficient for database/cache connections
- **Cost-Effective**: Balances performance and cost

**Why Not Alternatives**:
- **0.5 vCPU / 1 GB**: Risk of CPU throttling under moderate load
- **2 vCPU / 4 GB**: Over-provisioned for current traffic, 2x cost
- **4 vCPU / 8 GB**: Significant over-provisioning, 4x cost

**NFR Support**:
- NFR-2 (Performance): <200ms p50 response time target
- NFR-7 (Cost): $130/month baseline (2 tasks) acceptable

**Traceability**: BR-COMPUTE-006, User Decision Q2, NFR-2

---

## Technology Stack Summary

| Component | Technology | Version/Config | Rationale |
|-----------|-----------|----------------|-----------|
| **Orchestration** | AWS ECS Fargate | Latest | Serverless, AWS integration, auto-scaling |
| **Load Balancer** | Application Load Balancer | - | Layer 7, TLS termination, health checks |
| **Container Registry** | Amazon ECR | Immutable tags | Image scanning, lifecycle policies |
| **CI/CD** | GitHub Actions | Workflow as code | Native GitHub integration, OIDC |
| **Secrets** | AWS Secrets Manager | KMS encrypted | Automatic rotation, auditing |
| **Logging** | CloudWatch Logs | 30-day retention | Native ECS integration, Log Insights |
| **Tracing** | AWS X-Ray | Free tier | Distributed tracing, service map |
| **Auto-Scaling** | Application Auto Scaling | Target tracking 70% CPU | Simple, automatic, cost-effective |
| **Deployment** | ECS Rolling Update | 100%/200% config | Zero downtime, auto-rollback |
| **Network** | awsvpc | Private subnets | Task isolation, security groups |
| **Authentication** | Secrets Manager Password | Auto-rotation | Simple, secure, performant |
| **Task Size** | 1 vCPU / 2 GB RAM | Fargate | Balanced performance and cost |

---

## Technology Constraints

### Must Use (Requirements)
- **AWS Services**: Project goal is AWS modernization
- **Fargate**: Serverless compute (no EC2 management)
- **Private Subnets**: Security requirement (SECURITY-05)
- **Secrets Manager**: No hardcoded secrets (SECURITY-03)
- **TLS 1.2+**: Encryption in transit (SECURITY-02)

### Must Not Use (Exclusions)
- **Public Subnets** for ECS tasks: Security violation
- **Hardcoded Secrets**: Security violation (SECURITY-03)
- **HTTP-only**: Must redirect to HTTPS (BR-COMPUTE-001)
- **Mutable Image Tags**: Reproducibility requirement (BR-COMPUTE-031)

### May Use (Optional)
- **Fargate Spot**: 70% cost savings (future optimization)
- **CloudWatch Container Insights**: Enhanced metrics ($0.30/task/month)
- **AWS Config**: Configuration compliance monitoring
- **GuardDuty**: Threat detection

---

## Integration Points

### With Previous Units
| Unit | Service | Integration |
|------|---------|-------------|
| Unit 1 | VPC, Subnets, Security Groups | Tasks in private subnets, ALB in public subnets |
| Unit 2 | Aurora PostgreSQL, Secrets Manager | DATABASE_URL from Secrets Manager |
| Unit 3 | ElastiCache, Secrets Manager | REDIS_URI from Secrets Manager |

### With Future Units
| Unit | Service | Integration |
|------|---------|-------------|
| Unit 5 | Worker (ECS Tasks) | Shared ECR repository, same CI/CD pipeline |
| Unit 7 | Observability | CloudWatch dashboards, X-Ray service map |
| Unit 8 | CI/CD | GitHub Actions workflow, deployment automation |

---

## Technology Risk Assessment

| Technology | Maturity | Vendor Lock-in | Operational Complexity | Overall Risk |
|------------|----------|----------------|------------------------|--------------|
| ECS Fargate | High | High (AWS) | Low (serverless) | LOW |
| ALB | High | High (AWS) | Low (managed) | LOW |
| ECR | High | Medium (OCI standard) | Low (managed) | LOW |
| GitHub Actions | High | Medium (portable) | Low (SaaS) | LOW |
| Secrets Manager | High | High (AWS) | Low (managed) | LOW |
| CloudWatch Logs | High | High (AWS) | Low (managed) | LOW |
| X-Ray | Medium | High (AWS) | Low (managed) | LOW |

**Overall Technology Risk**: **LOW** - All technologies are mature, managed services with proven reliability.

---

## Future Optimization Opportunities

### Cost Optimization
1. **Fargate Spot**: 70% cost savings for non-critical tasks (consider for worker tasks in Unit 5)
2. **Reserved Capacity**: Commit to baseline capacity for 1-year term (30-50% discount)
3. **Savings Plans**: Compute Savings Plan for 1-3 year commitment (up to 66% discount)

### Performance Optimization
1. **CloudWatch Container Insights**: Enhanced metrics (CPU, memory, network per container)
2. **Task Size Tuning**: Monitor actual utilization, right-size tasks (may reduce to 0.5 vCPU if usage <30%)
3. **Connection Pooling**: Optimize database/cache connection pool sizes based on X-Ray traces

### Observability Enhancement
1. **CloudWatch Dashboards**: Custom dashboards for key metrics
2. **CloudWatch Alarms**: Alerts for unhealthy tasks, high error rate, high latency
3. **CloudWatch Insights**: Automated log analysis for error patterns

---

## References

- NFR Assessment: `nfr-assessment.md`
- Functional Design: `../functional-design/business-logic-model.md`
- User Decisions: `../functional-design/user-decision-log.md`
- AWS Service Documentation: [ECS](https://docs.aws.amazon.com/ecs/), [Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html), [ALB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/)
