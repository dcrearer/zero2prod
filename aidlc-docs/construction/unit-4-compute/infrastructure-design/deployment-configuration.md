# Unit 4: Compute Infrastructure - Deployment Configuration

## Overview

This document defines deployment procedures, validation steps, and operational procedures for the ComputeStack.

**Design Date**: 2026-06-12  
**Unit**: 4 of 8 (Compute Infrastructure)  
**Stack Name**: `Zero2ProdComputeStack`

---

## Pre-Deployment Prerequisites

### 1. Stack Dependencies

**Required Stacks** (must be deployed first):
- ✅ NetworkStack (Unit 1): VPC, subnets, security groups
- ✅ DatabaseStack (Unit 2): Aurora database, secrets
- ✅ CacheStack (Unit 3): ElastiCache, secrets

**Verify Stack Outputs**:
```bash
# Check NetworkStack outputs
aws cloudformation describe-stacks --stack-name Zero2ProdNetworkStack \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' --output table

# Check DatabaseStack outputs
aws cloudformation describe-stacks --stack-name Zero2ProdDatabaseStack \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' --output table

# Check CacheStack outputs
aws cloudformation describe-stacks --stack-name Zero2ProdCacheStack \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' --output table
```

**Required Exports**:
- `Zero2Prod-VPC-Id`
- `Zero2Prod-PublicSubnet-1a-Id`, `Zero2Prod-PublicSubnet-1b-Id`
- `Zero2Prod-PrivateSubnet-1a-Id`, `Zero2Prod-PrivateSubnet-1b-Id`
- `Zero2Prod-ALB-SG-Id`, `Zero2Prod-ECS-SG-Id`
- `Zero2Prod-Database-Secret-Arn`
- `Zero2Prod-Cache-Secret-Arn`

### 2. ACM Certificate

**Required**: TLS certificate for `newsletter.crearerd.people.aws.dev`

**Create Certificate** (if not exists):
```bash
# Request ACM certificate
aws acm request-certificate \
  --domain-name newsletter.crearerd.people.aws.dev \
  --validation-method DNS \
  --region us-east-1

# Get certificate ARN
CERTIFICATE_ARN=$(aws acm list-certificates \
  --region us-east-1 \
  --query 'CertificateSummaryList[?DomainName==`newsletter.crearerd.people.aws.dev`].CertificateArn' \
  --output text)

echo "Certificate ARN: $CERTIFICATE_ARN"
```

**Validate Certificate**:
- Add DNS validation records to Route53 or domain registrar
- Wait for certificate status to become `ISSUED`

```bash
# Check certificate status
aws acm describe-certificate \
  --certificate-arn $CERTIFICATE_ARN \
  --region us-east-1 \
  --query 'Certificate.Status' --output text
```

### 3. Container Image

**Required**: Docker image pushed to ECR repository

**Note**: ECR repository is created by ComputeStack, but initial image must be built and pushed before ECS service can start.

**Deployment Order**:
1. Deploy ComputeStack (creates ECR repository)
2. Build and push Docker image (GitHub Actions or manual)
3. Update ECS service to use new image

---

## Deployment Steps

### Step 1: Synthesize CDK Stack

```bash
cd infrastructure/
cdk synth Zero2ProdComputeStack
```

**Review Synthesized Template**:
```bash
# View CloudFormation template
cat cdk.out/Zero2ProdComputeStack.template.json | jq '.'

# Check for errors
cdk synth Zero2ProdComputeStack 2>&1 | grep -i error
```

### Step 2: Review Changes (Diff)

```bash
# Compare with deployed stack
cdk diff Zero2ProdComputeStack
```

**Review**:
- ✅ New resources: ALB, ECS cluster, task definition, service, auto-scaling, ECR, logs
- ✅ IAM role changes: Task execution role, task role
- ✅ Security group rules: ALB → ECS communication
- ⚠️ Deletions: Should be none on first deployment

### Step 3: Deploy Stack

```bash
# Deploy with confirmation prompt
cdk deploy Zero2ProdComputeStack

# Or deploy without prompts (CI/CD)
cdk deploy Zero2ProdComputeStack --require-approval never
```

**Deployment Time**: ~8-12 minutes
- ALB creation: ~3 minutes
- ECS cluster: <1 minute
- ECS service: ~5 minutes (waits for task health checks)

**Monitor Deployment**:
```bash
# Watch CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name Zero2ProdComputeStack \
  --max-items 20 \
  --query 'StackEvents[*].[Timestamp,ResourceStatus,ResourceType,LogicalResourceId]' \
  --output table
```

### Step 4: Build and Push Initial Image

**After ComputeStack deployment completes**:

```bash
# Get ECR repository URI
ECR_URI=$(aws cloudformation describe-stacks \
  --stack-name Zero2ProdComputeStack \
  --query 'Stacks[0].Outputs[?OutputKey==`EcrRepositoryUri`].OutputValue' \
  --output text)

echo "ECR URI: $ECR_URI"

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_URI

# Build Docker image
docker build -t zero2prod:latest .

# Tag image with git commit hash
GIT_SHA=$(git rev-parse --short HEAD)
docker tag zero2prod:latest $ECR_URI:sha-$GIT_SHA
docker tag zero2prod:latest $ECR_URI:latest

# Push image
docker push $ECR_URI:sha-$GIT_SHA
docker push $ECR_URI:latest
```

### Step 5: Update ECS Service

**First Deployment**: ECS service will automatically pull the `latest` tag after image is pushed.

**Subsequent Deployments**: Use GitHub Actions workflow (see below) or manual update:

```bash
# Update task definition with new image
aws ecs update-service \
  --cluster zero2prod-cluster \
  --service zero2prod-web-service \
  --force-new-deployment
```

---

## Post-Deployment Validation

### 1. Verify ALB

```bash
# Get ALB DNS name
ALB_DNS=$(aws cloudformation describe-stacks \
  --stack-name Zero2ProdComputeStack \
  --query 'Stacks[0].Outputs[?OutputKey==`AlbDnsName`].OutputValue' \
  --output text)

echo "ALB DNS: $ALB_DNS"

# Test HTTP → HTTPS redirect
curl -I http://$ALB_DNS
# Expected: 301 Moved Permanently, Location: https://...

# Test HTTPS endpoint
curl -k https://$ALB_DNS/health_check
# Expected: 200 OK
```

### 2. Verify ECS Service

```bash
# Check service status
aws ecs describe-services \
  --cluster zero2prod-cluster \
  --services zero2prod-web-service \
  --query 'services[0].{Status:status,DesiredCount:desiredCount,RunningCount:runningCount,PendingCount:pendingCount}' \
  --output table

# Expected:
# Status: ACTIVE
# DesiredCount: 2
# RunningCount: 2
# PendingCount: 0
```

### 3. Verify Task Health

```bash
# List running tasks
TASK_ARNS=$(aws ecs list-tasks \
  --cluster zero2prod-cluster \
  --service-name zero2prod-web-service \
  --query 'taskArns' --output text)

# Check task details
aws ecs describe-tasks \
  --cluster zero2prod-cluster \
  --tasks $TASK_ARNS \
  --query 'tasks[*].{TaskId:taskArn,Status:lastStatus,HealthStatus:healthStatus,AZ:availabilityZone}' \
  --output table

# Expected:
# Status: RUNNING
# HealthStatus: HEALTHY
# AZ: us-east-1a, us-east-1b (spread across AZs)
```

### 4. Verify Auto-Scaling

```bash
# Check auto-scaling policy
aws application-autoscaling describe-scaling-policies \
  --service-namespace ecs \
  --resource-id service/zero2prod-cluster/zero2prod-web-service \
  --query 'ScalingPolicies[*].{PolicyName:PolicyName,TargetValue:TargetTrackingScalingPolicyConfiguration.TargetValue}' \
  --output table

# Expected:
# TargetValue: 70.0 (70% CPU)
```

### 5. Verify Health Checks

```bash
# Check target group health
TG_ARN=$(aws elbv2 describe-target-groups \
  --names zero2prod-tg \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

aws elbv2 describe-target-health \
  --target-group-arn $TG_ARN \
  --query 'TargetHealthDescriptions[*].{Target:Target.Id,State:TargetHealth.State,Reason:TargetHealth.Reason}' \
  --output table

# Expected:
# State: healthy (for all 2 tasks)
```

### 6. Verify CloudWatch Logs

```bash
# Check log streams exist
aws logs describe-log-streams \
  --log-group-name /ecs/zero2prod-web \
  --max-items 5 \
  --query 'logStreams[*].{LogStream:logStreamName,LastEvent:lastEventTime}' \
  --output table

# View recent logs
aws logs tail /ecs/zero2prod-web --follow
```

### 7. Test Application Endpoints

```bash
# Test health check endpoint
curl https://newsletter.crearerd.people.aws.dev/health_check
# Expected: 200 OK

# Test database connectivity (via health check)
# Health check validates database connection internally

# Test application functionality
# (User-specific tests, e.g., subscribe to newsletter)
```

---

## GitHub Actions CI/CD Workflow

**File**: `.github/workflows/deploy-ecs.yml`

```yaml
name: Deploy to ECS

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: zero2prod
  ECS_CLUSTER: zero2prod-cluster
  ECS_SERVICE: zero2prod-web-service
  CONTAINER_NAME: zero2prod-web

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/GitHubActionsDeployRole
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Build and push Docker image
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: sha-${{ github.sha }}
        run: |
          # Build image
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
          
          # Push image
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
          
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT
      
      - name: Download task definition
        run: |
          aws ecs describe-task-definition \
            --task-definition zero2prod-web \
            --query 'taskDefinition' > task-definition.json
      
      - name: Update task definition with new image
        id: task-def
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: task-definition.json
          container-name: ${{ env.CONTAINER_NAME }}
          image: ${{ steps.build-image.outputs.image }}
      
      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v2
        with:
          task-definition: ${{ steps.task-def.outputs.task-definition }}
          service: ${{ env.ECS_SERVICE }}
          cluster: ${{ env.ECS_CLUSTER }}
          wait-for-service-stability: true
      
      - name: Verify deployment
        run: |
          # Wait for service to stabilize
          aws ecs wait services-stable \
            --cluster ${{ env.ECS_CLUSTER }} \
            --services ${{ env.ECS_SERVICE }}
          
          # Check running count
          RUNNING=$(aws ecs describe-services \
            --cluster ${{ env.ECS_CLUSTER }} \
            --services ${{ env.ECS_SERVICE }} \
            --query 'services[0].runningCount' --output text)
          
          echo "Running tasks: $RUNNING"
          
          if [ "$RUNNING" -lt 2 ]; then
            echo "ERROR: Expected at least 2 running tasks, got $RUNNING"
            exit 1
          fi
```

**GitHub OIDC Role Setup** (one-time):
```bash
# Create IAM role for GitHub Actions
aws iam create-role \
  --role-name GitHubActionsDeployRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/zero2prod:ref:refs/heads/main"
        }
      }
    }]
  }'

# Attach policies
aws iam attach-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

aws iam attach-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess
```

---

## Troubleshooting Guide

### Issue 1: ECS Service Stuck in PENDING

**Symptoms**:
- Service has 0 running tasks
- Tasks fail to start or immediately exit

**Diagnosis**:
```bash
# Check service events
aws ecs describe-services \
  --cluster zero2prod-cluster \
  --services zero2prod-web-service \
  --query 'services[0].events[:5]' --output table

# Check task stopped reason
aws ecs list-tasks \
  --cluster zero2prod-cluster \
  --service-name zero2prod-web-service \
  --desired-status STOPPED \
  --max-results 1

# Describe stopped task
STOPPED_TASK=$(aws ecs list-tasks \
  --cluster zero2prod-cluster \
  --service-name zero2prod-web-service \
  --desired-status STOPPED \
  --query 'taskArns[0]' --output text)

aws ecs describe-tasks \
  --cluster zero2prod-cluster \
  --tasks $STOPPED_TASK \
  --query 'tasks[0].{StoppedReason:stoppedReason,Containers:containers[*].{Name:name,Reason:reason,ExitCode:exitCode}}' \
  --output json
```

**Common Causes**:
- **Image pull error**: ECR repository empty or image tag not found
  - Solution: Build and push Docker image (see Step 4)
- **Secrets Manager error**: Task execution role lacks `secretsmanager:GetSecretValue` permission
  - Solution: Verify IAM policy in task execution role
- **Resource constraint**: Insufficient CPU/memory in subnet
  - Solution: Check subnet placement, scale down other services
- **Health check failing**: Application not responding on port 8000 or `/health_check` returns non-200
  - Solution: Check application logs, verify database connectivity

### Issue 2: Target Group Health Checks Failing

**Symptoms**:
- Target group shows unhealthy targets
- ALB returns 503 Service Unavailable

**Diagnosis**:
```bash
# Check target health details
TG_ARN=$(aws elbv2 describe-target-groups \
  --names zero2prod-tg \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

aws elbv2 describe-target-health \
  --target-group-arn $TG_ARN \
  --query 'TargetHealthDescriptions[*].{Target:Target.Id,State:TargetHealth.State,Reason:TargetHealth.Reason,Description:TargetHealth.Description}' \
  --output table

# Check application logs
aws logs tail /ecs/zero2prod-web --follow --filter-pattern "health_check"
```

**Common Causes**:
- **Database unreachable**: Health check validates database connectivity
  - Solution: Verify security group allows ECS → Aurora (port 5432)
- **Application crashed**: Process died or hung
  - Solution: Check logs for panic/error, verify secrets loaded correctly
- **Port mismatch**: Container not listening on port 8000
  - Solution: Verify `APP_APPLICATION__PORT=8000` environment variable
- **Health check path wrong**: Application expects different path
  - Solution: Verify application has `/health_check` endpoint

### Issue 3: Auto-Scaling Not Triggering

**Symptoms**:
- CPU exceeds 70% but no scale-out
- CPU drops below 70% but no scale-in

**Diagnosis**:
```bash
# Check current CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=zero2prod-web-service Name=ClusterName,Value=zero2prod-cluster \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Average \
  --query 'Datapoints[*].[Timestamp,Average]' \
  --output table

# Check scaling activities
aws application-autoscaling describe-scaling-activities \
  --service-namespace ecs \
  --resource-id service/zero2prod-cluster/zero2prod-web-service \
  --max-results 5 \
  --query 'ScalingActivities[*].{StartTime:StartTime,Status:StatusCode,Cause:Cause,Description:Description}' \
  --output table
```

**Common Causes**:
- **Cooldown period active**: Scale-out cooldown 60s, scale-in cooldown 300s
  - Solution: Wait for cooldown to expire
- **At capacity limits**: Already at min (2) or max (10) tasks
  - Solution: Adjust capacity limits if needed
- **Metric delay**: CloudWatch metrics have ~1 minute lag
  - Solution: Wait for metrics to stabilize

### Issue 4: Certificate Validation Failing

**Symptoms**:
- ALB HTTPS listener shows `ACM certificate pending validation`
- CloudFormation deployment hangs on ALB resource

**Diagnosis**:
```bash
# Check certificate status
CERT_ARN=$(aws acm list-certificates \
  --region us-east-1 \
  --query 'CertificateSummaryList[?DomainName==`newsletter.crearerd.people.aws.dev`].CertificateArn' \
  --output text)

aws acm describe-certificate \
  --certificate-arn $CERT_ARN \
  --region us-east-1 \
  --query 'Certificate.{Status:Status,ValidationMethod:DomainValidationOptions[0].ValidationMethod,ResourceRecord:DomainValidationOptions[0].ResourceRecord}' \
  --output json
```

**Common Causes**:
- **DNS validation record missing**: CNAME record not added to Route53
  - Solution: Add validation record from ACM console or CLI
- **DNS propagation delay**: Record added but not yet propagated
  - Solution: Wait 5-15 minutes for DNS propagation

---

## Cost Monitoring

### Daily Cost Estimate

**Baseline (2 tasks)**:
- ECS Fargate (2 × 1 vCPU / 2 GB): $88.56/month
- ALB: $16.20/month
- NAT Gateway (2 AZs, data transfer): $72.00/month
- ElastiCache Redis (t3.micro): $12.41/month
- Aurora Serverless v2 (0.5 ACU min): $43.80/month
- **Total Baseline**: ~$233/month

**Maximum (10 tasks)**:
- ECS Fargate (10 × 1 vCPU / 2 GB): $442.80/month
- Other services unchanged
- **Total Maximum**: ~$587/month

**Monitor Costs**:
```bash
# Get current month costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --group-by Type=SERVICE \
  --query 'ResultsByTime[0].Groups[*].[Keys[0],Metrics.UnblendedCost.Amount]' \
  --output table
```

### Cost Optimization Actions

1. **Right-size tasks**: If CPU consistently <30%, reduce to 0.5 vCPU / 1 GB
2. **Adjust auto-scaling**: Lower max capacity if never reaching 10 tasks
3. **Enable ALB access logs compression**: Reduce S3 storage costs (Unit 7)
4. **Review CloudWatch Logs retention**: Reduce from 30 days to 7 days if acceptable

---

## Operational Procedures

### Rolling Back a Deployment

```bash
# List task definition revisions
aws ecs list-task-definitions \
  --family-prefix zero2prod-web \
  --query 'taskDefinitionArns[-5:]' \
  --output table

# Update service to previous revision
aws ecs update-service \
  --cluster zero2prod-cluster \
  --service zero2prod-web-service \
  --task-definition zero2prod-web:PREVIOUS_REVISION

# Wait for rollback to complete
aws ecs wait services-stable \
  --cluster zero2prod-cluster \
  --services zero2prod-web-service
```

### Scaling Manually

```bash
# Scale out (increase desired count)
aws ecs update-service \
  --cluster zero2prod-cluster \
  --service zero2prod-web-service \
  --desired-count 4

# Scale in (decrease desired count)
aws ecs update-service \
  --cluster zero2prod-cluster \
  --service zero2prod-web-service \
  --desired-count 2
```

### Draining Tasks for Maintenance

```bash
# Stop tasks gracefully (300s connection draining)
TASK_ARN=$(aws ecs list-tasks \
  --cluster zero2prod-cluster \
  --service-name zero2prod-web-service \
  --query 'taskArns[0]' --output text)

aws ecs stop-task \
  --cluster zero2prod-cluster \
  --task $TASK_ARN \
  --reason "Maintenance window"

# Service will automatically launch replacement task
```

### Updating Environment Variables

```bash
# Update task definition with new environment variables
# (Requires redeployment)

# 1. Download current task definition
aws ecs describe-task-definition \
  --task-definition zero2prod-web \
  --query 'taskDefinition' > task-def.json

# 2. Edit task-def.json (update environment variables)

# 3. Register new task definition
aws ecs register-task-definition --cli-input-json file://task-def.json

# 4. Update service
aws ecs update-service \
  --cluster zero2prod-cluster \
  --service zero2prod-web-service \
  --task-definition zero2prod-web:NEW_REVISION
```

---

## References

- CDK Stack Design: `cdk-stack-design.md`
- Logical Components: `../nfr-design/logical-components.md`
- Domain Entities: `../functional-design/domain-entities.md`
- Business Rules: `../functional-design/business-rules.md`
