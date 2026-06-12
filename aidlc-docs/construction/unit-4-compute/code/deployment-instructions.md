# Unit 4: Compute Infrastructure - Deployment Instructions

## Overview

This document provides step-by-step instructions for deploying the ComputeStack to AWS.

**Unit**: 4 of 8 (Compute Infrastructure)  
**Stack Name**: `Zero2ProdComputeStack`  
**Deployment Time**: ~10-15 minutes

---

## Prerequisites

### 1. Previous Stacks Deployed

Ensure Units 1-3 are already deployed:

```bash
# Verify NetworkStack
aws cloudformation describe-stacks --stack-name Zero2ProdNetworkStack --query 'Stacks[0].StackStatus'
# Expected: CREATE_COMPLETE or UPDATE_COMPLETE

# Verify DatabaseStack
aws cloudformation describe-stacks --stack-name Zero2ProdDatabaseStack --query 'Stacks[0].StackStatus'
# Expected: CREATE_COMPLETE or UPDATE_COMPLETE

# Verify CacheStack
aws cloudformation describe-stacks --stack-name Zero2ProdCacheStack --query 'Stacks[0].StackStatus'
# Expected: CREATE_COMPLETE or UPDATE_COMPLETE
```

### 2. ACM Certificate

Create an ACM certificate for your domain (e.g., `newsletter.crearerd.people.aws.dev`):

```bash
# Request certificate
aws acm request-certificate \
  --domain-name newsletter.crearerd.people.aws.dev \
  --validation-method DNS \
  --region us-east-1

# Get certificate ARN
CERT_ARN=$(aws acm list-certificates \
  --region us-east-1 \
  --query 'CertificateSummaryList[?DomainName==`newsletter.crearerd.people.aws.dev`].CertificateArn' \
  --output text)

echo "Certificate ARN: $CERT_ARN"
```

**Important**: Add the DNS validation record to your DNS provider and wait for the certificate status to become `ISSUED` before deploying.

```bash
# Check certificate status
aws acm describe-certificate --certificate-arn $CERT_ARN --region us-east-1 --query 'Certificate.Status'
```

### 3. CDK Environment

Ensure AWS CDK is installed and environment is configured:

```bash
cd cdk/

# Check CDK version
cdk --version

# Bootstrap CDK (if not already done)
cdk bootstrap aws://ACCOUNT_ID/us-east-1
```

---

## Deployment Steps

### Step 1: Configure Certificate ARN

Add the certificate ARN to CDK context:

**Option A**: Via `cdk.context.json` (recommended)

```bash
cd cdk/

# Add certificate ARN to cdk.context.json
cat <<EOF > cdk.context.json
{
  "certificate_arn": "$CERT_ARN"
}
EOF
```

**Option B**: Via command-line flag

```bash
cdk deploy Zero2ProdComputeStack --context certificate_arn=$CERT_ARN
```

### Step 2: Synthesize CDK Stack

Generate CloudFormation template:

```bash
cd cdk/
cdk synth Zero2ProdComputeStack
```

**Review Synthesized Template**:
```bash
# View template
cat cdk.out/Zero2ProdComputeStack.template.json | jq '.'

# Check for any errors
cdk synth Zero2ProdComputeStack 2>&1 | grep -i error
```

### Step 3: Review Changes (Diff)

Compare with existing stack (if updating) or preview new resources:

```bash
cdk diff Zero2ProdComputeStack
```

**Expected Resources** (first deployment):
- Application Load Balancer (ALB)
- Target Group
- HTTP Listener (port 80)
- HTTPS Listener (port 443)
- ECS Cluster
- ECS Task Definition
- ECS Service
- Auto-Scaling Target + Policy
- ECR Repository
- CloudWatch Log Group
- Secrets Manager Secret (HMAC)
- IAM Roles (task execution, task runtime)
- CloudFormation Outputs

### Step 4: Deploy Stack

Deploy the ComputeStack:

```bash
cdk deploy Zero2ProdComputeStack
```

**Expected Output**:
```
✨  Synthesis time: Xs

Zero2ProdComputeStack: deploying... [1/1]
Zero2ProdComputeStack: creating CloudFormation changeset...

 ✅  Zero2ProdComputeStack

✨  Deployment time: XXXs

Outputs:
Zero2ProdComputeStack.AlbDnsName = zero2prod-alb-XXXXXXXXXX.us-east-1.elb.amazonaws.com
Zero2ProdComputeStack.ClusterName = zero2prod-cluster
Zero2ProdComputeStack.EcrRepositoryUri = ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/zero2prod
Zero2ProdComputeStack.ServiceName = zero2prod-web-service

Stack ARN:
arn:aws:cloudformation:us-east-1:ACCOUNT_ID:stack/Zero2ProdComputeStack/...
```

**Deployment Duration**: ~10-15 minutes
- ALB creation: ~3 minutes
- ECS cluster: <1 minute
- ECS service: ~5 minutes (will fail initially without Docker image - this is expected)

### Step 5: Build and Push Initial Docker Image

After stack deployment, build and push the Docker image to ECR:

```bash
# Get ECR repository URI from stack outputs
ECR_URI=$(aws cloudformation describe-stacks \
  --stack-name Zero2ProdComputeStack \
  --query 'Stacks[0].Outputs[?OutputKey==`EcrRepositoryUri`].OutputValue' \
  --output text)

echo "ECR URI: $ECR_URI"

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_URI

# Build Docker image (from repository root)
cd /Users/crearerd/Dev/rust/zero2prod
docker build -t zero2prod:latest .

# Tag image
GIT_SHA=$(git rev-parse --short HEAD)
docker tag zero2prod:latest $ECR_URI:sha-$GIT_SHA
docker tag zero2prod:latest $ECR_URI:latest

# Push to ECR
docker push $ECR_URI:sha-$GIT_SHA
docker push $ECR_URI:latest
```

### Step 6: Wait for ECS Service to Stabilize

After pushing the image, ECS will automatically pull it and start tasks:

```bash
# Monitor service events
aws ecs describe-services \
  --cluster zero2prod-cluster \
  --services zero2prod-web-service \
  --query 'services[0].events[:5]'

# Wait for service stability (can take 2-3 minutes)
aws ecs wait services-stable \
  --cluster zero2prod-cluster \
  --services zero2prod-web-service

echo "ECS service is stable!"
```

---

## Post-Deployment Validation

### 1. Verify ECS Service

```bash
# Check service status
aws ecs describe-services \
  --cluster zero2prod-cluster \
  --services zero2prod-web-service \
  --query 'services[0].{Status:status,DesiredCount:desiredCount,RunningCount:runningCount}' \
  --output table

# Expected:
# Status: ACTIVE
# DesiredCount: 2
# RunningCount: 2
```

### 2. Verify Running Tasks

```bash
# List running tasks
aws ecs list-tasks \
  --cluster zero2prod-cluster \
  --service-name zero2prod-web-service \
  --desired-status RUNNING

# Check task health
TASK_ARNS=$(aws ecs list-tasks \
  --cluster zero2prod-cluster \
  --service-name zero2prod-web-service \
  --query 'taskArns' --output text)

aws ecs describe-tasks \
  --cluster zero2prod-cluster \
  --tasks $TASK_ARNS \
  --query 'tasks[*].{TaskId:taskArn,Status:lastStatus,HealthStatus:healthStatus,AZ:availabilityZone}' \
  --output table

# Expected:
# Status: RUNNING
# HealthStatus: HEALTHY
# AZ: us-east-1a, us-east-1b
```

### 3. Verify Target Group Health

```bash
# Get target group ARN
TG_ARN=$(aws elbv2 describe-target-groups \
  --names zero2prod-tg \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

# Check target health
aws elbv2 describe-target-health \
  --target-group-arn $TG_ARN \
  --query 'TargetHealthDescriptions[*].{Target:Target.Id,State:TargetHealth.State}' \
  --output table

# Expected:
# State: healthy (for both targets)
```

### 4. Test Application Endpoints

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

# Test health check endpoint (use -k to skip certificate validation for ALB DNS)
curl -k https://$ALB_DNS/health_check
# Expected: 200 OK
```

### 5. Check CloudWatch Logs

```bash
# View recent logs
aws logs tail /ecs/zero2prod-web --follow

# OR
aws logs describe-log-streams \
  --log-group-name /ecs/zero2prod-web \
  --max-items 5 \
  --query 'logStreams[*].{LogStream:logStreamName,LastEvent:lastEventTime}' \
  --output table
```

---

## GitHub Actions CI/CD Setup

### 1. Create GitHub OIDC Provider (One-Time)

```bash
# Create OIDC provider for GitHub Actions
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### 2. Create IAM Role for GitHub Actions

```bash
# Create trust policy
cat <<EOF > github-trust-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
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
    }
  ]
}
EOF

# Replace ACCOUNT_ID and YOUR_ORG
sed -i '' 's/ACCOUNT_ID/123456789012/g' github-trust-policy.json
sed -i '' 's/YOUR_ORG/dcrearer/g' github-trust-policy.json

# Create role
aws iam create-role \
  --role-name GitHubActionsDeployRole \
  --assume-role-policy-document file://github-trust-policy.json \
  --description "GitHub Actions deployment role for Zero2Prod"

# Attach policies
aws iam attach-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

aws iam attach-role-policy \
  --role-name GitHubActionsDeployRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess

# Get role ARN
aws iam get-role --role-name GitHubActionsDeployRole --query 'Role.Arn'
```

### 3. Add Secret to GitHub Repository

1. Navigate to GitHub repository: `https://github.com/YOUR_ORG/zero2prod`
2. Go to **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret**
4. Name: `AWS_OIDC_ROLE_ARN`
5. Value: (paste role ARN from previous step)
6. Click **Add secret**

### 4. Test GitHub Actions Workflow

```bash
# Push to main branch to trigger deployment
git add .
git commit -m "feat: add ComputeStack and GitHub Actions workflow"
git push origin main

# Monitor workflow in GitHub Actions tab
```

---

## Troubleshooting

### Issue: ECS Service Shows 0 Running Tasks

**Cause**: Docker image not pushed to ECR, or task definition references non-existent image.

**Solution**:
```bash
# Check ECR images
aws ecr list-images --repository-name zero2prod

# If empty, push image (see Step 5 above)

# Check task stopped reason
aws ecs describe-tasks \
  --cluster zero2prod-cluster \
  --tasks $(aws ecs list-tasks --cluster zero2prod-cluster --desired-status STOPPED --query 'taskArns[0]' --output text) \
  --query 'tasks[0].{Reason:stoppedReason,Containers:containers[*].{Name:name,Reason:reason}}'
```

### Issue: Target Group Shows Unhealthy Targets

**Cause**: Application not responding on port 8000 or `/health_check` endpoint failing.

**Solution**:
```bash
# Check application logs
aws logs tail /ecs/zero2prod-web --follow

# Check task environment variables
aws ecs describe-task-definition \
  --task-definition zero2prod-web \
  --query 'taskDefinition.containerDefinitions[0].environment'

# Verify DATABASE_URL and REDIS_URI secrets exist
aws secretsmanager get-secret-value --secret-id zero2prod/database/master-credentials
aws secretsmanager get-secret-value --secret-id zero2prod/cache/connection
```

### Issue: Certificate Validation Pending

**Cause**: DNS validation record not added or DNS propagation delay.

**Solution**:
```bash
# Get validation record
aws acm describe-certificate --certificate-arn $CERT_ARN --region us-east-1 --query 'Certificate.DomainValidationOptions[0].ResourceRecord'

# Add CNAME record to Route53 or DNS provider
# Wait 5-15 minutes for propagation
```

---

## Cost Monitoring

After deployment, monitor costs:

```bash
# Get current month costs (requires Cost Explorer enabled)
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --group-by Type=SERVICE
```

**Expected Monthly Costs** (Unit 4 only):
- ECS Fargate (2 tasks, 1 vCPU / 2 GB): ~$88.56/month
- ALB: ~$16.20/month
- ECR storage: ~$1/month (10 images)
- CloudWatch Logs: ~$0.50/month (30 days, 1 GB/month)
- **Total Baseline**: ~$106/month

---

## Next Steps

1. **Unit 5: Worker Infrastructure** - Deploy background worker for email processing
2. **Configure DNS** - Point domain to ALB DNS name in Route53
3. **Monitor Application** - Set up CloudWatch dashboards and alarms (Unit 7)
4. **Load Testing** - Verify auto-scaling behavior under load

---

## References

- Code Summary: `code-summary.md`
- Testing Instructions: `testing-instructions.md`
- Detailed Deployment Configuration: `../infrastructure-design/deployment-configuration.md`
- CDK Stack Design: `../infrastructure-design/cdk-stack-design.md`
