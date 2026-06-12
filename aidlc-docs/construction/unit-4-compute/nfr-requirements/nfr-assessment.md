# Unit 4: Compute Infrastructure - NFR Assessment

## Overview

This document assesses non-functional requirements for the ECS Fargate compute infrastructure. Most NFR decisions were made during functional design; this assessment validates those decisions and documents the complete NFR profile.

**Assessment Date**: 2026-06-12  
**Unit**: 4 of 8 (Compute Infrastructure)

---

## NFR-1: Scalability Requirements

### Requirement Statement
The compute infrastructure MUST scale horizontally from 2 to 10 ECS tasks based on CPU utilization, supporting traffic growth from 100 to 500+ requests/minute without manual intervention.

### Target Metrics
- **Baseline Capacity**: 2 tasks (100-150 req/min)
- **Auto-Scaling Trigger**: 70% average CPU utilization
- **Maximum Capacity**: 10 tasks (500+ req/min)
- **Scale-Out Time**: <60 seconds from trigger to new task healthy
- **Scale-In Time**: <300 seconds cooldown before scale-in

### Implementation Approach
- **Auto-Scaling Policy**: Target tracking scaling with CPU utilization metric
- **Min/Max Capacity**: 2-10 tasks (prevents over-provisioning)
- **Gradual Scaling**: Add/remove 1 task at a time (smooth transitions)
- **Cooldown Periods**: 60s scale-out, 300s scale-in (prevent thrashing)

### Risk Assessment
**Risk Level**: **LOW**

**Rationale**:
- Target tracking scaling is proven and reliable
- 10-task maximum provides 5x baseline capacity (500%+ headroom)
- 1 vCPU / 2 GB per task sized appropriately for workload
- CloudWatch metrics provide accurate scaling signals

**Mitigation**:
- Monitor CPU utilization trends in CloudWatch
- Adjust target CPU or max capacity if traffic exceeds projections
- Load testing before production to validate scaling behavior

### Acceptance Criteria
- ✅ Service scales out within 60 seconds when CPU >70%
- ✅ Service scales in after 300 seconds when CPU <70%
- ✅ Service never scales below 2 tasks or above 10 tasks
- ✅ Scaling actions are gradual (1 task at a time)

### Traceability
- Functional Design: BR-COMPUTE-013 to BR-COMPUTE-018
- User Decision: Q3 (auto-scaling parameters)

---

## NFR-2: Performance Requirements

### Requirement Statement
The compute infrastructure MUST support response times <200ms (p50) and <500ms (p99) for typical API requests under normal load (100-300 req/min).

### Target Metrics
- **Response Time P50**: <200ms
- **Response Time P95**: <400ms
- **Response Time P99**: <500ms
- **Throughput**: 100-300 req/min per task (moderate traffic)
- **Task Startup Time**: <120 seconds (from launch to healthy)

### Implementation Approach
- **Task Sizing**: 1 vCPU / 2 GB RAM (sized for moderate traffic)
- **Connection Pooling**: Database and cache connection pools reduce latency
- **Health Check**: 60-second grace period allows full initialization
- **AWS X-Ray**: Distributed tracing to identify performance bottlenecks

### Risk Assessment
**Risk Level**: **LOW**

**Rationale**:
- 1 vCPU provides adequate compute for web application workload
- 2 GB RAM sufficient for connection pools and application memory
- Aurora and ElastiCache in same region (low network latency)
- X-Ray tracing enables performance monitoring and optimization

**Mitigation**:
- Monitor response times via CloudWatch and X-Ray
- Analyze slow requests via X-Ray traces
- Increase task size to 2 vCPU / 4 GB if CPU becomes bottleneck
- Optimize database queries based on X-Ray insights

### Acceptance Criteria
- ✅ P50 response time <200ms under 200 req/min load
- ✅ P99 response time <500ms under 200 req/min load
- ✅ Task startup completes within 120 seconds
- ✅ X-Ray traces show end-to-end request flows

### Traceability
- Functional Design: BR-COMPUTE-006 (task sizing), BR-COMPUTE-029 (X-Ray)
- User Decision: Q2 (1 vCPU / 2 GB RAM), Clarification Q3 (X-Ray tracing)

---

## NFR-3: Availability Requirements

### Requirement Statement
The compute infrastructure MUST achieve 99.9% availability (43 minutes downtime/month) through Multi-AZ deployment, auto-healing, and zero-downtime deployments.

### Target Metrics
- **Availability SLA**: 99.9% (monthly)
- **Recovery Time Objective (RTO)**: <2 minutes (single task failure)
- **Recovery Point Objective (RPO)**: 0 seconds (no data loss - stateless tasks)
- **Deployment Downtime**: 0 seconds (rolling updates)

### Implementation Approach
- **Multi-AZ Deployment**: 2 tasks across us-east-1a and us-east-1b
- **Auto-Healing**: ECS replaces failed tasks automatically
- **Health Checks**: ALB removes unhealthy tasks within 90 seconds
- **Rolling Deployments**: 100% minimum healthy, 200% maximum capacity
- **Connection Draining**: 300-second graceful shutdown

### Risk Assessment
**Risk Level**: **LOW**

**Rationale**:
- Fargate has 99.99% availability SLA
- Multi-AZ protects against single AZ failure
- Auto-healing replaces failed tasks within 2 minutes
- Rolling deployments ensure no downtime during updates

**Mitigation**:
- Monitor task failure rate in CloudWatch
- Configure CloudWatch alarms for unhealthy task count
- Test AZ failure scenarios (simulate by stopping tasks in one AZ)
- Monitor deployment success rate

### Acceptance Criteria
- ✅ Service survives single task failure with <2 min recovery
- ✅ Service survives single AZ failure (all traffic routes to other AZ)
- ✅ Deployments complete with 0 seconds downtime
- ✅ Monthly availability >99.9% (measured via ALB metrics)

### Traceability
- Functional Design: BR-COMPUTE-012 (Multi-AZ), BR-COMPUTE-020 to BR-COMPUTE-024 (deployment)
- User Decision: Q8 (rolling update), Q10 (2 tasks desired count)

---

## NFR-4: Security Requirements

### Requirement Statement
The compute infrastructure MUST protect sensitive data through encryption (in transit and at rest), secrets management, least privilege IAM, and network isolation.

### Target Metrics
- **Encryption**: 100% of sensitive data encrypted (TLS 1.2+, KMS)
- **Secrets Management**: 0% hardcoded secrets (100% in Secrets Manager)
- **IAM Compliance**: 100% least privilege (scoped permissions only)
- **Network Isolation**: 100% of tasks in private subnets (no public IP)

### Implementation Approach
- **TLS Encryption**: ALB enforces HTTPS (redirects HTTP to HTTPS)
- **Secrets Manager**: DATABASE_URL, REDIS_URI, HMAC_SECRET loaded from Secrets Manager
- **IAM Roles**: Task execution role (ECR, logs, secrets) + task role (runtime permissions)
- **Network Isolation**: Tasks in private subnets, no public IP, security groups restrict access
- **X-Ray Tracing**: Traces do not contain sensitive data (PII filtered)

### Risk Assessment
**Risk Level**: **LOW**

**Rationale**:
- All SECURITY extension rules (SECURITY-01 to SECURITY-06) compliant
- Secrets never hardcoded or logged
- IAM roles follow least privilege principle
- Network isolation prevents external access to tasks

**Mitigation**:
- Audit IAM policies regularly (remove unused permissions)
- Rotate secrets automatically via Secrets Manager
- Monitor CloudTrail for suspicious IAM actions
- Scan ECR images for vulnerabilities (enabled on push)

### Acceptance Criteria
- ✅ All HTTP requests redirected to HTTPS (301)
- ✅ TLS 1.2+ enforced on ALB (verify with SSL Labs)
- ✅ No secrets in task definition JSON or CloudWatch logs
- ✅ IAM roles have only required permissions (validated with Access Analyzer)
- ✅ Tasks have no public IP, reside in private subnets

### Traceability
- Functional Design: BR-COMPUTE-001 (HTTPS), BR-COMPUTE-025 (Secrets Manager), BR-COMPUTE-030 (IAM)
- User Decision: Q1 (ACM certificate), Q5 (minimal IAM), Q7 (Secrets Manager)
- Security Extension: SECURITY-01 to SECURITY-06 (100% compliant)

---

## NFR-5: Reliability Requirements

### Requirement Statement
The compute infrastructure MUST detect and recover from failures automatically through health checks, auto-healing, and comprehensive monitoring.

### Target Metrics
- **Mean Time to Detect (MTTD)**: <90 seconds (3 failed health checks)
- **Mean Time to Recover (MTTR)**: <2 minutes (task replacement)
- **Health Check Success Rate**: >99% (under normal conditions)
- **Error Rate**: <0.1% (5xx responses)

### Implementation Approach
- **ALB Health Checks**: 30-second interval, database validation
- **ECS Auto-Healing**: Replaces unhealthy tasks automatically
- **CloudWatch Logs**: Centralized logging (30-day retention)
- **AWS X-Ray**: Distributed tracing for error diagnosis
- **CloudWatch Alarms**: Alert on high error rate or unhealthy tasks (future)

### Risk Assessment
**Risk Level**: **LOW**

**Rationale**:
- Health checks detect failures within 90 seconds (3 × 30s)
- ECS launches replacement tasks automatically
- Logs and traces enable rapid troubleshooting
- Database-only health check focuses on critical path

**Mitigation**:
- Monitor health check success rate in CloudWatch
- Set up alarms for unhealthy task count >0 for >5 minutes
- Analyze X-Ray traces for intermittent errors
- Review CloudWatch logs for application errors

### Acceptance Criteria
- ✅ Unhealthy tasks deregistered within 90 seconds
- ✅ Replacement tasks launched within 60 seconds of failure
- ✅ Health check success rate >99% (measured over 24 hours)
- ✅ All application logs available in CloudWatch Logs

### Traceability
- Functional Design: BR-COMPUTE-005, BR-COMPUTE-009 to BR-COMPUTE-011 (health checks)
- User Decision: Q4 (health check config), Clarification Q1 (database-only validation)

---

## NFR-6: Maintainability Requirements

### Requirement Statement
The compute infrastructure MUST support automated deployments, comprehensive logging, and traceability from running tasks to source code commits.

### Target Metrics
- **Deployment Automation**: 100% (GitHub Actions CI/CD)
- **Deployment Success Rate**: >95%
- **Deployment Time**: <5 minutes (from commit to production)
- **Log Retention**: 30 days (CloudWatch Logs)
- **Traceability**: 100% (sha-based image tags)

### Implementation Approach
- **GitHub Actions**: Automated builds on push to main
- **Immutable Tags**: `sha-<git-hash>` tags prevent overwrites
- **ECR Image Scanning**: Vulnerability scanning on push
- **CloudWatch Logs**: Structured logging with 30-day retention
- **X-Ray Tracing**: Request flow visualization

### Risk Assessment
**Risk Level**: **LOW**

**Rationale**:
- GitHub Actions provides reliable CI/CD automation
- Immutable tags ensure reproducibility
- Image scanning detects vulnerabilities early
- Comprehensive logging enables troubleshooting

**Mitigation**:
- Monitor GitHub Actions workflow success rate
- Set up alerts for failed builds or deployments
- Review image scan findings before deployment
- Increase log retention to 90 days if compliance requires

### Acceptance Criteria
- ✅ Every push to main triggers automated build and deployment
- ✅ Image tags are immutable (cannot be overwritten)
- ✅ ECR scans all images on push
- ✅ Logs retained for 30 days in CloudWatch
- ✅ Running tasks traceable to git commits via image tags

### Traceability
- Functional Design: BR-COMPUTE-031 to BR-COMPUTE-033 (ECR), BR-COMPUTE-034 (logs)
- User Decision: Q6 (GitHub Actions), Q9 (log retention)

---

## NFR-7: Cost Optimization Requirements

### Requirement Statement
The compute infrastructure MUST optimize costs through right-sizing, auto-scaling, and efficient resource utilization while meeting performance and availability requirements.

### Target Metrics
- **Baseline Cost**: ~$159/month (2 tasks + supporting services)
- **Maximum Cost**: <$679/month (10 tasks + supporting services)
- **CPU Utilization**: 50-80% (optimal range)
- **Task Efficiency**: >100 req/min per task

### Implementation Approach
- **Right-Sizing**: 1 vCPU / 2 GB balances performance and cost
- **Auto-Scaling**: Scale based on demand (2-10 tasks)
- **Fargate Spot**: Consider Fargate Spot for 70% savings (future optimization)
- **Log Retention**: 30-day retention balances cost and troubleshooting
- **ECR Lifecycle**: Keep only last 10 images (reduce storage cost)

### Risk Assessment
**Risk Level**: **LOW**

**Rationale**:
- Baseline cost ($159/month) reasonable for production workload
- Auto-scaling prevents over-provisioning
- Max capacity cap ($679/month) provides cost predictability

**Mitigation**:
- Monitor CPU utilization; reduce task size if consistently <30%
- Monitor cost trends in AWS Cost Explorer
- Consider Fargate Spot for non-critical tasks (70% cost reduction)
- Review CloudWatch metrics retention (reduce if >30 days not needed)

### Acceptance Criteria
- ✅ Baseline cost <$200/month (2 tasks)
- ✅ Maximum cost <$700/month (10 tasks)
- ✅ CPU utilization 50-80% during normal traffic
- ✅ Cost alarms configured (alert if >$750/month)

### Traceability
- User Decision Log: Total cost summary ($159 baseline, $679 maximum)
- User Decision: Q2 (task sizing), Q3 (auto-scaling)

---

## NFR Summary Matrix

| NFR Category | Requirement | Target | Risk | Status |
|--------------|-------------|--------|------|--------|
| Scalability | Auto-scaling 2-10 tasks | 70% CPU trigger | LOW | ✅ ACHIEVABLE |
| Performance | Response time <200ms p50 | 1 vCPU / 2 GB | LOW | ✅ ACHIEVABLE |
| Availability | 99.9% uptime | Multi-AZ, auto-healing | LOW | ✅ ACHIEVABLE |
| Security | SECURITY-01 to SECURITY-06 | 100% compliant | LOW | ✅ ACHIEVABLE |
| Reliability | MTTD <90s, MTTR <2min | Health checks, auto-healing | LOW | ✅ ACHIEVABLE |
| Maintainability | GitHub Actions CI/CD | <5 min deployment | LOW | ✅ ACHIEVABLE |
| Cost Optimization | $159-$679/month | Right-sizing, auto-scaling | LOW | ✅ ACHIEVABLE |

**Overall Assessment**: All NFRs are ACHIEVABLE with LOW risk using the selected architecture and configuration.

---

## NFR Traceability to Functional Design

| NFR | Functional Design Business Rules | User Decisions |
|-----|----------------------------------|----------------|
| NFR-1 (Scalability) | BR-COMPUTE-013 to BR-COMPUTE-018 | Q3 (auto-scaling) |
| NFR-2 (Performance) | BR-COMPUTE-006, BR-COMPUTE-029 | Q2 (task sizing), Clarification Q3 (X-Ray) |
| NFR-3 (Availability) | BR-COMPUTE-012, BR-COMPUTE-020 to BR-COMPUTE-024 | Q8 (rolling update), Q10 (2 tasks) |
| NFR-4 (Security) | BR-COMPUTE-001, BR-COMPUTE-025, BR-COMPUTE-030 | Q1 (certificate), Q5 (IAM), Q7 (secrets) |
| NFR-5 (Reliability) | BR-COMPUTE-005, BR-COMPUTE-009 to BR-COMPUTE-011 | Q4 (health checks), Clarification Q1 |
| NFR-6 (Maintainability) | BR-COMPUTE-031 to BR-COMPUTE-034 | Q6 (GitHub Actions), Q9 (logs) |
| NFR-7 (Cost) | User Decision Log cost analysis | Q2 (sizing), Q3 (scaling) |

---

## Risk Mitigation Summary

### Low-Risk NFRs (All 7)
All NFRs assessed as LOW risk due to:
- Proven AWS services (ECS Fargate, ALB, Auto Scaling)
- Conservative capacity planning (5x headroom)
- Comprehensive monitoring (CloudWatch, X-Ray)
- Auto-healing and Multi-AZ deployment

### Monitoring and Validation Plan
1. **Pre-Production**: Load testing to validate performance and scaling
2. **Post-Deployment**: 
   - Monitor CloudWatch metrics (CPU, memory, request count, latency)
   - Analyze X-Ray traces for slow requests
   - Review cost trends in AWS Cost Explorer
   - Test failover scenarios (task failure, AZ failure)
3. **Ongoing**:
   - Weekly review of CloudWatch dashboards
   - Monthly cost review and optimization
   - Quarterly capacity planning review

---

## References

- Functional Design: `../functional-design/business-logic-model.md`
- Business Rules: `../functional-design/business-rules.md`
- User Decisions: `../functional-design/user-decision-log.md`
- Security Extension: SECURITY-01 through SECURITY-06 (100% compliant)
