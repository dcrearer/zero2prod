# Unit 4: Compute Infrastructure - Testing Instructions

## Overview

This document provides instructions for testing the ComputeStack implementation at various stages.

**Unit**: 4 of 8 (Compute Infrastructure)  
**Test Types**: Unit tests, CDK synthesis validation, integration tests

---

## 1. Unit Tests

### Prerequisites

Ensure pytest and CDK are installed:

```bash
cd cdk/

# Check Python environment
python3 --version

# Install dependencies (if not already done)
pip install -r requirements.txt

# Verify pytest installation
pytest --version
```

### Running Unit Tests

**Run all ComputeStack tests**:
```bash
cd cdk/
pytest tests/test_compute_stack.py -v
```

**Expected Output**:
```
tests/test_compute_stack.py::TestApplicationLoadBalancer::test_alb_created PASSED
tests/test_compute_stack.py::TestApplicationLoadBalancer::test_http_listener_redirects PASSED
tests/test_compute_stack.py::TestApplicationLoadBalancer::test_target_group_created PASSED
tests/test_compute_stack.py::TestECSCluster::test_cluster_created PASSED
tests/test_compute_stack.py::TestTaskDefinition::test_task_definition_created PASSED
tests/test_compute_stack.py::TestTaskDefinition::test_container_definition PASSED
tests/test_compute_stack.py::TestIAMRoles::test_task_execution_role_created PASSED
tests/test_compute_stack.py::TestIAMRoles::test_task_role_created PASSED
tests/test_compute_stack.py::TestECSService::test_service_created PASSED
tests/test_compute_stack.py::TestAutoScaling::test_scalable_target_created PASSED
tests/test_compute_stack.py::TestAutoScaling::test_scaling_policy_created PASSED
tests/test_compute_stack.py::TestECRRepository::test_repository_created PASSED
tests/test_compute_stack.py::TestCloudWatchLogs::test_log_group_created PASSED
tests/test_compute_stack.py::TestSecretsManager::test_hmac_secret_created PASSED
tests/test_compute_stack.py::TestCloudFormationOutputs::test_required_outputs_exist PASSED

================ 15 passed in X.XXs ================
```

### Running Specific Test Classes

```bash
# Test only ALB configuration
pytest tests/test_compute_stack.py::TestApplicationLoadBalancer -v

# Test only ECS configuration
pytest tests/test_compute_stack.py::TestECSCluster -v
pytest tests/test_compute_stack.py::TestTaskDefinition -v
pytest tests/test_compute_stack.py::TestECSService -v

# Test only auto-scaling
pytest tests/test_compute_stack.py::TestAutoScaling -v

# Test only IAM roles
pytest tests/test_compute_stack.py::TestIAMRoles -v
```

### Running Specific Test Methods

```bash
# Test HTTP redirect
pytest tests/test_compute_stack.py::TestApplicationLoadBalancer::test_http_listener_redirects -v

# Test task definition resources
pytest tests/test_compute_stack.py::TestTaskDefinition::test_task_definition_created -v

# Test auto-scaling policy
pytest tests/test_compute_stack.py::TestAutoScaling::test_scaling_policy_created -v
```

### Test Coverage

Run tests with coverage report:

```bash
cd cdk/
pytest tests/test_compute_stack.py --cov=stacks.compute_stack --cov-report=term-missing
```

---

## 2. CDK Synthesis Validation

### Synthesize Stack

Generate CloudFormation template and validate:

```bash
cd cdk/
cdk synth Zero2ProdComputeStack
```

**Expected Output**:
```
Successfully synthesized to /path/to/cdk.out/Zero2ProdComputeStack.template.json
```

### Validate Synthesis

**Check for errors**:
```bash
cdk synth Zero2ProdComputeStack 2>&1 | grep -i error
```

**Expected**: No output (no errors)

### Inspect Generated Template

**View full template**:
```bash
cat cdk.out/Zero2ProdComputeStack.template.json | jq '.'
```

**Check specific resources**:
```bash
# Count resources
cat cdk.out/Zero2ProdComputeStack.template.json | jq '.Resources | length'
# Expected: ~30 resources

# List all resource types
cat cdk.out/Zero2ProdComputeStack.template.json | jq '.Resources | to_entries | .[].value.Type' | sort | uniq

# Expected types:
# AWS::ApplicationAutoScaling::ScalableTarget
# AWS::ApplicationAutoScaling::ScalingPolicy
# AWS::EC2::SecurityGroup
# AWS::ECR::Repository
# AWS::ECS::Cluster
# AWS::ECS::Service
# AWS::ECS::TaskDefinition
# AWS::ElasticLoadBalancingV2::Listener
# AWS::ElasticLoadBalancingV2::LoadBalancer
# AWS::ElasticLoadBalancingV2::TargetGroup
# AWS::IAM::Policy
# AWS::IAM::Role
# AWS::Logs::LogGroup
# AWS::SecretsManager::Secret
```

### Validate CloudFormation Template

Use AWS CLI to validate template syntax:

```bash
aws cloudformation validate-template \
  --template-body file://cdk.out/Zero2ProdComputeStack.template.json
```

**Expected Output**:
```json
{
    "Parameters": [],
    "Description": "Compute infrastructure for Zero2Prod newsletter service...",
    "Capabilities": ["CAPABILITY_IAM"],
    "CapabilitiesReason": "The following resource(s) require capabilities: [AWS::IAM::Role, AWS::IAM::Policy]"
}
```

---

## 3. Pre-Deployment Tests

### Check Stack Dependencies

Verify prerequisite stacks are deployed:

```bash
# Check NetworkStack
aws cloudformation describe-stacks \
  --stack-name Zero2ProdNetworkStack \
  --query 'Stacks[0].StackStatus' \
  --output text

# Expected: CREATE_COMPLETE or UPDATE_COMPLETE

# Check DatabaseStack
aws cloudformation describe-stacks \
  --stack-name Zero2ProdDatabaseStack \
  --query 'Stacks[0].StackStatus' \
  --output text

# Expected: CREATE_COMPLETE or UPDATE_COMPLETE

# Check CacheStack
aws cloudformation describe-stacks \
  --stack-name Zero2ProdCacheStack \
  --query 'Stacks[0].StackStatus' \
  --output text

# Expected: CREATE_COMPLETE or UPDATE_COMPLETE
```

### Validate Stack Exports

Check that required exports exist:

```bash
# List all exports
aws cloudformation list-exports --query 'Exports[*].[Name,Value]' --output table

# Verify required exports:
# - Zero2Prod-VPC-Id
# - Zero2Prod-PublicSubnet-1a-Id
# - Zero2Prod-PublicSubnet-1b-Id
# - Zero2Prod-PrivateSubnet-1a-Id
# - Zero2Prod-PrivateSubnet-1b-Id
# - Zero2Prod-ALB-SG-Id
# - Zero2Prod-ECS-SG-Id
# - Zero2Prod-Database-Secret-Arn
# - Zero2Prod-Cache-Secret-Arn
```

### CDK Diff (Dry Run)

Preview changes without deploying:

```bash
cd cdk/
cdk diff Zero2ProdComputeStack
```

**Review**:
- New resources being created
- IAM policy changes
- Security group modifications

---

## 4. Post-Deployment Integration Tests

After deploying ComputeStack, run integration tests to verify functionality.

### Test 1: ECS Service Health

```bash
# Check service is running
SERVICE_STATUS=$(aws ecs describe-services \
  --cluster zero2prod-cluster \
  --services zero2prod-web-service \
  --query 'services[0].status' \
  --output text)

if [ "$SERVICE_STATUS" == "ACTIVE" ]; then
  echo "✅ PASS: ECS service is ACTIVE"
else
  echo "❌ FAIL: ECS service status is $SERVICE_STATUS"
  exit 1
fi

# Check desired count
DESIRED=$(aws ecs describe-services \
  --cluster zero2prod-cluster \
  --services zero2prod-web-service \
  --query 'services[0].desiredCount' \
  --output text)

RUNNING=$(aws ecs describe-services \
  --cluster zero2prod-cluster \
  --services zero2prod-web-service \
  --query 'services[0].runningCount' \
  --output text)

if [ "$RUNNING" -eq "$DESIRED" ] && [ "$DESIRED" -eq 2 ]; then
  echo "✅ PASS: Running $RUNNING/$DESIRED tasks"
else
  echo "❌ FAIL: Expected 2 running tasks, got $RUNNING"
  exit 1
fi
```

### Test 2: Target Group Health

```bash
# Check all targets are healthy
TG_ARN=$(aws elbv2 describe-target-groups \
  --names zero2prod-tg \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

HEALTHY_COUNT=$(aws elbv2 describe-target-health \
  --target-group-arn $TG_ARN \
  --query 'length(TargetHealthDescriptions[?TargetHealth.State==`healthy`])' \
  --output text)

if [ "$HEALTHY_COUNT" -eq 2 ]; then
  echo "✅ PASS: All 2 targets are healthy"
else
  echo "❌ FAIL: Only $HEALTHY_COUNT/2 targets are healthy"
  exit 1
fi
```

### Test 3: HTTP → HTTPS Redirect

```bash
# Get ALB DNS
ALB_DNS=$(aws cloudformation describe-stacks \
  --stack-name Zero2ProdComputeStack \
  --query 'Stacks[0].Outputs[?OutputKey==`AlbDnsName`].OutputValue' \
  --output text)

# Test HTTP redirect
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$ALB_DNS)
REDIRECT_LOCATION=$(curl -s -I http://$ALB_DNS | grep -i location | awk '{print $2}' | tr -d '\r')

if [ "$HTTP_STATUS" -eq 301 ] && [[ "$REDIRECT_LOCATION" == https* ]]; then
  echo "✅ PASS: HTTP redirects to HTTPS with 301"
else
  echo "❌ FAIL: HTTP redirect failed (status: $HTTP_STATUS, location: $REDIRECT_LOCATION)"
  exit 1
fi
```

### Test 4: Health Check Endpoint

```bash
# Test health check endpoint (skip certificate validation for ALB DNS)
HEALTH_STATUS=$(curl -k -s -o /dev/null -w "%{http_code}" https://$ALB_DNS/health_check)

if [ "$HEALTH_STATUS" -eq 200 ]; then
  echo "✅ PASS: Health check returns 200 OK"
else
  echo "❌ FAIL: Health check failed with status $HEALTH_STATUS"
  exit 1
fi
```

### Test 5: CloudWatch Logs

```bash
# Check log streams exist
LOG_STREAM_COUNT=$(aws logs describe-log-streams \
  --log-group-name /ecs/zero2prod-web \
  --max-items 10 \
  --query 'length(logStreams)' \
  --output text)

if [ "$LOG_STREAM_COUNT" -gt 0 ]; then
  echo "✅ PASS: CloudWatch log streams exist ($LOG_STREAM_COUNT streams)"
else
  echo "❌ FAIL: No CloudWatch log streams found"
  exit 1
fi
```

### Test 6: Auto-Scaling Configuration

```bash
# Check auto-scaling target exists
SCALABLE_TARGET=$(aws application-autoscaling describe-scalable-targets \
  --service-namespace ecs \
  --resource-ids service/zero2prod-cluster/zero2prod-web-service \
  --query 'ScalableTargets[0].{Min:MinCapacity,Max:MaxCapacity}' \
  --output json)

MIN_CAPACITY=$(echo $SCALABLE_TARGET | jq -r '.Min')
MAX_CAPACITY=$(echo $SCALABLE_TARGET | jq -r '.Max')

if [ "$MIN_CAPACITY" -eq 2 ] && [ "$MAX_CAPACITY" -eq 10 ]; then
  echo "✅ PASS: Auto-scaling configured (min: 2, max: 10)"
else
  echo "❌ FAIL: Auto-scaling misconfigured (min: $MIN_CAPACITY, max: $MAX_CAPACITY)"
  exit 1
fi

# Check scaling policy exists
POLICY_COUNT=$(aws application-autoscaling describe-scaling-policies \
  --service-namespace ecs \
  --resource-id service/zero2prod-cluster/zero2prod-web-service \
  --query 'length(ScalingPolicies)' \
  --output text)

if [ "$POLICY_COUNT" -gt 0 ]; then
  echo "✅ PASS: Auto-scaling policy exists"
else
  echo "❌ FAIL: No auto-scaling policy found"
  exit 1
fi
```

### Test 7: ECR Repository

```bash
# Check ECR repository exists
REPO_URI=$(aws ecr describe-repositories \
  --repository-names zero2prod \
  --query 'repositories[0].repositoryUri' \
  --output text 2>/dev/null)

if [ -n "$REPO_URI" ]; then
  echo "✅ PASS: ECR repository exists ($REPO_URI)"
else
  echo "❌ FAIL: ECR repository not found"
  exit 1
fi

# Check image exists
IMAGE_COUNT=$(aws ecr list-images \
  --repository-name zero2prod \
  --query 'length(imageIds)' \
  --output text)

if [ "$IMAGE_COUNT" -gt 0 ]; then
  echo "✅ PASS: Docker images exist in ECR ($IMAGE_COUNT images)"
else
  echo "⚠️  WARNING: No Docker images in ECR (push initial image)"
fi
```

### Test 8: Secrets Manager

```bash
# Check HMAC secret exists
HMAC_SECRET=$(aws secretsmanager describe-secret \
  --secret-id zero2prod/hmac/secret \
  --query 'Name' \
  --output text 2>/dev/null)

if [ "$HMAC_SECRET" == "zero2prod/hmac/secret" ]; then
  echo "✅ PASS: HMAC secret exists"
else
  echo "❌ FAIL: HMAC secret not found"
  exit 1
fi
```

### Run All Integration Tests

Create a test script:

```bash
#!/bin/bash
# File: cdk/tests/integration-tests.sh

set -e

echo "Running ComputeStack Integration Tests..."
echo "=========================================="

# Test 1: ECS Service Health
echo "Test 1: ECS Service Health"
# ... (paste test 1 code)

# Test 2: Target Group Health
echo "Test 2: Target Group Health"
# ... (paste test 2 code)

# Test 3-8: Continue with remaining tests...

echo "=========================================="
echo "✅ All integration tests passed!"
```

Run the script:
```bash
chmod +x cdk/tests/integration-tests.sh
./cdk/tests/integration-tests.sh
```

---

## 5. Load Testing (Optional)

Test auto-scaling behavior under load:

```bash
# Install hey (HTTP load generator)
# macOS: brew install hey
# Linux: go install github.com/rakyll/hey@latest

# Get ALB DNS
ALB_DNS=$(aws cloudformation describe-stacks \
  --stack-name Zero2ProdComputeStack \
  --query 'Stacks[0].Outputs[?OutputKey==`AlbDnsName`].OutputValue' \
  --output text)

# Generate load (200 requests/sec for 2 minutes)
hey -z 2m -c 50 -q 4 https://$ALB_DNS/health_check

# Monitor task count during load
watch -n 5 'aws ecs describe-services \
  --cluster zero2prod-cluster \
  --services zero2prod-web-service \
  --query "services[0].{Desired:desiredCount,Running:runningCount}" \
  --output table'

# Check CloudWatch CPU metrics
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
```

---

## 6. Troubleshooting Tests

### Debug Failed Unit Tests

```bash
# Run with verbose output
pytest tests/test_compute_stack.py -v -s

# Run with full error details
pytest tests/test_compute_stack.py -v --tb=long

# Run specific failing test
pytest tests/test_compute_stack.py::TestClass::test_method -vv
```

### Debug CDK Synthesis Errors

```bash
# Check for Python syntax errors
python3 -m py_compile stacks/compute_stack.py

# Check CDK context
cat cdk.context.json

# Synthesize with debug output
cdk synth Zero2ProdComputeStack --verbose
```

### Debug Integration Test Failures

```bash
# Check CloudFormation stack events
aws cloudformation describe-stack-events \
  --stack-name Zero2ProdComputeStack \
  --max-items 20 \
  --query 'StackEvents[*].[Timestamp,ResourceStatus,ResourceType,ResourceStatusReason]' \
  --output table

# Check ECS task logs
aws logs tail /ecs/zero2prod-web --follow

# Describe failed tasks
aws ecs describe-tasks \
  --cluster zero2prod-cluster \
  --tasks $(aws ecs list-tasks --cluster zero2prod-cluster --desired-status STOPPED --query 'taskArns[0]' --output text)
```

---

## Test Summary

| Test Type | Location | Purpose | Duration |
|-----------|----------|---------|----------|
| Unit Tests | `cdk/tests/test_compute_stack.py` | Validate CDK constructs | ~5 seconds |
| CDK Synthesis | `cdk synth` | Validate template generation | ~3 seconds |
| Pre-Deployment | Shell scripts | Verify prerequisites | ~10 seconds |
| Integration Tests | Shell scripts | Verify deployed resources | ~30 seconds |
| Load Tests | `hey` command | Test auto-scaling | ~2 minutes |

---

## References

- Code Summary: `code-summary.md`
- Deployment Instructions: `deployment-instructions.md`
- Troubleshooting Guide: `../infrastructure-design/deployment-configuration.md#troubleshooting-guide`
