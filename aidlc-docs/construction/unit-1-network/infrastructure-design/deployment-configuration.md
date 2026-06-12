# Deployment Configuration - Unit 1: Network Infrastructure

## Overview

This document defines the deployment process, environment configuration, testing strategy, rollback procedures, and CI/CD integration for the NetworkStack. It provides operational guidance for deploying and managing the network infrastructure.

**Scope**: CDK bootstrap, environment configuration, deployment commands, testing, rollback, and GitHub Actions integration.

**Related Documents**:
- CDK Stack Design: `cdk-stack-design.md` (sibling document)
- Resource Specifications: `resource-specifications.md` (sibling document)

---

## 1. CDK Bootstrap Requirements

### 1.1 Bootstrap Overview

**Purpose**: One-time setup to prepare AWS environment for CDK deployments. Creates S3 bucket for CloudFormation templates, ECR repository for Docker images, and IAM roles for deployment.

**When to Run**: Once per AWS account and region before first CDK deployment.

**Bootstrap Command**:

```bash
cdk bootstrap aws://<account-id>/<region>
```

**Example** (production account, us-east-1):

```bash
cdk bootstrap aws://123456789012/us-east-1
```

---

### 1.2 Bootstrap Resources Created

**CloudFormation Stack**: `CDKToolkit`

**Resources Created**:

| Resource | Type | Purpose | Name |
|----------|------|---------|------|
| S3 Bucket | `AWS::S3::Bucket` | Store CloudFormation templates and assets | `cdk-hnb659fds-assets-123456789012-us-east-1` |
| ECR Repository | `AWS::ECR::Repository` | Store Docker images (for containerized constructs) | `cdk-hnb659fds-container-assets-123456789012-us-east-1` |
| IAM Role | `AWS::IAM::Role` | CloudFormation execution role | `cdk-hnb659fds-cfn-exec-role-123456789012-us-east-1` |
| IAM Role | `AWS::IAM::Role` | CDK deployment role | `cdk-hnb659fds-deploy-role-123456789012-us-east-1` |
| IAM Role | `AWS::IAM::Role` | File asset publishing role | `cdk-hnb659fds-file-publishing-role-123456789012-us-east-1` |
| IAM Role | `AWS::IAM::Role` | Image asset publishing role | `cdk-hnb659fds-image-publishing-role-123456789012-us-east-1` |
| SSM Parameter | `AWS::SSM::Parameter` | Bootstrap version | `/cdk-bootstrap/hnb659fds/version` |

**Bootstrap Version**: CDK v2 bootstrap (uses qualifier `hnb659fds`)

---

### 1.3 Bootstrap Verification

**Verify Bootstrap Succeeded**:

```bash
# Check if CDKToolkit stack exists
aws cloudformation describe-stacks --stack-name CDKToolkit --region us-east-1

# Expected output: Stack status = CREATE_COMPLETE or UPDATE_COMPLETE
```

**Check S3 Bucket**:

```bash
# List CDK S3 bucket
aws s3 ls | grep cdk-hnb659fds-assets

# Expected output: cdk-hnb659fds-assets-123456789012-us-east-1
```

**Check IAM Roles**:

```bash
# List CDK IAM roles
aws iam list-roles | grep cdk-hnb659fds

# Expected output: 4 IAM roles listed
```

---

## 2. Environment Configuration

### 2.1 Environment Variables

**Required Environment Variables**:

| Variable | Description | Example Value | Required |
|----------|-------------|---------------|----------|
| `CDK_DEFAULT_ACCOUNT` | AWS account ID | `123456789012` | Yes |
| `CDK_DEFAULT_REGION` | AWS region | `us-east-1` | Yes |
| `ENVIRONMENT` | Environment name | `production`, `staging`, `development` | No (default: `production`) |

**Set Environment Variables**:

```bash
# Linux/macOS
export CDK_DEFAULT_ACCOUNT=123456789012
export CDK_DEFAULT_REGION=us-east-1
export ENVIRONMENT=production

# Windows PowerShell
$env:CDK_DEFAULT_ACCOUNT="123456789012"
$env:CDK_DEFAULT_REGION="us-east-1"
$env:ENVIRONMENT="production"
```

---

### 2.2 CDK Context Configuration

**File**: `cdk/cdk.json`

**Purpose**: Define CDK feature flags and environment-specific configuration.

```json
{
  "app": "python3 app.py",
  "watch": {
    "include": ["**"],
    "exclude": [
      "README.md",
      "cdk*.json",
      "requirements*.txt",
      "**/__init__.py",
      "**/__pycache__",
      "**/pytest_cache",
      "tests"
    ]
  },
  "context": {
    "@aws-cdk/aws-apigateway:usagePlanKeyOrderInsensitiveId": true,
    "@aws-cdk/core:stackRelativeExports": true,
    "@aws-cdk/aws-rds:lowercaseDbIdentifier": true,
    "@aws-cdk/aws-lambda:recognizeVersionProps": true,
    "@aws-cdk/aws-cloudfront:defaultSecurityPolicyTLSv1.2_2021": true,
    
    "availability-zones:account=123456789012:region=us-east-1": [
      "us-east-1a",
      "us-east-1b"
    ]
  }
}
```

**Key Configuration Options**:

| Context Key | Value | Purpose |
|-------------|-------|---------|
| `availability-zones` | `["us-east-1a", "us-east-1b"]` | Explicit AZ configuration (optional, CDK can auto-detect) |
| `@aws-cdk/core:stackRelativeExports` | `true` | Use stack-relative export names (recommended) |

---

### 2.3 Environment-Specific Configuration

**Development Environment**:

```bash
# cdk/config/dev.py
ENVIRONMENT = "development"
VPC_CIDR = "10.0.0.0/16"
MAX_AZS = 2
ENABLE_VPC_FLOW_LOGS = False
```

**Staging Environment**:

```bash
# cdk/config/staging.py
ENVIRONMENT = "staging"
VPC_CIDR = "10.0.0.0/16"
MAX_AZS = 2
ENABLE_VPC_FLOW_LOGS = False
```

**Production Environment**:

```bash
# cdk/config/prod.py
ENVIRONMENT = "production"
VPC_CIDR = "10.0.0.0/16"
MAX_AZS = 2
ENABLE_VPC_FLOW_LOGS = False  # Enable later if needed
```

**Load Configuration in CDK App**:

```python
# cdk/app.py
import os
from aws_cdk import App
from stacks.network_stack import NetworkStack

# Load environment-specific configuration
env_name = os.environ.get("ENVIRONMENT", "production")
if env_name == "development":
    from config import dev as config
elif env_name == "staging":
    from config import staging as config
else:
    from config import prod as config

app = App()

network_stack = NetworkStack(
    app, "NetworkStack",
    env={"account": os.environ["CDK_DEFAULT_ACCOUNT"], "region": os.environ["CDK_DEFAULT_REGION"]},
    vpc_cidr=config.VPC_CIDR,
    max_azs=config.MAX_AZS
)

app.synth()
```

---

## 3. CDK Deployment Commands

### 3.1 Prerequisites

**Install CDK CLI**:

```bash
# Install CDK CLI globally
npm install -g aws-cdk

# Verify installation
cdk --version

# Expected output: 2.100.0 (or later)
```

**Install Python Dependencies**:

```bash
cd cdk

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

---

### 3.2 CDK Synth (Generate CloudFormation Template)

**Purpose**: Generate CloudFormation template from CDK code for review.

**Command**:

```bash
cdk synth NetworkStack
```

**Output**: CloudFormation template written to `cdk.out/NetworkStack.template.json`

**Review Template**:

```bash
# View synthesized template
cat cdk.out/NetworkStack.template.json | jq

# Count resources
cat cdk.out/NetworkStack.template.json | jq '.Resources | length'

# Expected output: ~35 resources
```

**Verification Checklist**:
- [ ] VPC created with CIDR `10.0.0.0/16`
- [ ] 4 subnets created (2 public, 2 private)
- [ ] 6 security groups created
- [ ] 8 VPC endpoints created (1 Gateway, 7 Interface)
- [ ] No NAT Gateway resources (confirmed absence)

---

### 3.3 CDK Diff (Preview Changes)

**Purpose**: Preview infrastructure changes before deployment.

**Command**:

```bash
cdk diff NetworkStack
```

**Expected Output** (first deployment):

```
Stack NetworkStack
IAM Statement Changes
┌───┬────────────────────────┬────────┬──────────────────┬───────────────────────┬───────────┐
│   │ Resource               │ Effect │ Action           │ Principal             │ Condition │
├───┼────────────────────────┼────────┼──────────────────┼───────────────────────┼───────────┤
│ + │ ${VpcEndpointSg.Arn}   │ Allow  │ ec2:*            │ AWS:${Vpc/Arn}        │           │
└───┴────────────────────────┴────────┴──────────────────┴───────────────────────┴───────────┘

Resources
[+] AWS::EC2::VPC NetworkStack/Vpc VpcXXXXXXXX
[+] AWS::EC2::Subnet NetworkStack/Vpc/PublicSubnet1 PublicSubnetXXXXXXXX
[+] AWS::EC2::Subnet NetworkStack/Vpc/PublicSubnet2 PublicSubnetXXXXXXXX
[+] AWS::EC2::Subnet NetworkStack/Vpc/PrivateSubnet1 PrivateSubnetXXXXXXXX
[+] AWS::EC2::Subnet NetworkStack/Vpc/PrivateSubnet2 PrivateSubnetXXXXXXXX
[+] AWS::EC2::SecurityGroup NetworkStack/AlbSecurityGroup AlbSecurityGroupXXXXXXXX
... (30 more resources)

Outputs
[+] Output NetworkStack/VpcId VpcId: {"Value":{"Ref":"VpcXXXXXXXX"}}
... (7 more outputs)
```

**Verify Before Deployment**:
- Review resource additions (all should be `[+]` for first deployment)
- Verify no unexpected resource deletions (`[-]`) or modifications (`[~]`)
- Check IAM policy changes (security review)

---

### 3.4 CDK Deploy (Deploy Stack)

**Purpose**: Deploy NetworkStack to AWS.

**Command** (with approval prompt):

```bash
cdk deploy NetworkStack --require-approval broadening
```

**Command** (without approval, for CI/CD):

```bash
cdk deploy NetworkStack --require-approval never
```

**Expected Output**:

```
NetworkStack: deploying...
[0%] start: Publishing asset cdk-hnb659fds-assets-123456789012-us-east-1
[50%] success: Published asset cdk-hnb659fds-assets-123456789012-us-east-1
[50%] start: Publishing NetworkStack
[75%] success: Published NetworkStack
NetworkStack: creating CloudFormation changeset...

 ✅  NetworkStack

Outputs:
NetworkStack.VpcId = vpc-0a1b2c3d4e5f6g7h8
NetworkStack.PublicSubnetIds = subnet-public-1a,subnet-public-1b
NetworkStack.PrivateSubnetIds = subnet-private-1a,subnet-private-1b
NetworkStack.AlbSecurityGroupId = sg-alb
NetworkStack.EcsSecurityGroupId = sg-ecs
NetworkStack.AuroraSecurityGroupId = sg-aurora
NetworkStack.ElastiCacheSecurityGroupId = sg-elasticache
NetworkStack.LambdaSecurityGroupId = sg-lambda
NetworkStack.VpcEndpointSecurityGroupId = sg-vpc-endpoints

Stack ARN:
arn:aws:cloudformation:us-east-1:123456789012:stack/NetworkStack/abc123
```

**Deployment Time**: ~5-7 minutes (VPC endpoints take longest to create)

---

### 3.5 CDK Destroy (Delete Stack)

**Purpose**: Delete NetworkStack (use with caution).

**Command**:

```bash
cdk destroy NetworkStack
```

**Warning**: Cannot destroy NetworkStack if other stacks depend on its exports.

**Verification Before Destroy**:

```bash
# Check if other stacks depend on NetworkStack
aws cloudformation list-exports --region us-east-1 | grep Zero2Prod

# If exports are in use, destroy dependent stacks first
```

**Destroy Order** (reverse of deployment order):

1. Destroy ComputeStack (Unit 4)
2. Destroy LambdaStack (Unit 5)
3. Destroy CacheStack (Unit 3)
4. Destroy DatabaseStack (Unit 2)
5. Destroy NetworkStack (Unit 1)

---

## 4. Stack Outputs

### 4.1 CloudFormation Outputs

**Purpose**: Export network resource IDs for consumption by other stacks.

**Output Definitions**:

| Output Name | Export Name | Value | Description |
|-------------|-------------|-------|-------------|
| `VpcId` | `Zero2ProdVpcId` | `{VPC.VpcId}` | VPC ID for Zero2Prod application |
| `PublicSubnetIds` | `Zero2ProdPublicSubnetIds` | `subnet-xxx,subnet-yyy` | Comma-separated public subnet IDs |
| `PrivateSubnetIds` | `Zero2ProdPrivateSubnetIds` | `subnet-xxx,subnet-yyy` | Comma-separated private subnet IDs |
| `AlbSecurityGroupId` | `Zero2ProdAlbSecurityGroupId` | `{AlbSg.SecurityGroupId}` | ALB security group ID |
| `EcsSecurityGroupId` | `Zero2ProdEcsSecurityGroupId` | `{EcsSg.SecurityGroupId}` | ECS security group ID |
| `AuroraSecurityGroupId` | `Zero2ProdAuroraSecurityGroupId` | `{AuroraSg.SecurityGroupId}` | Aurora security group ID |
| `ElastiCacheSecurityGroupId` | `Zero2ProdElastiCacheSecurityGroupId` | `{ElastiCacheSg.SecurityGroupId}` | ElastiCache security group ID |
| `LambdaSecurityGroupId` | `Zero2ProdLambdaSecurityGroupId` | `{LambdaSg.SecurityGroupId}` | Lambda security group ID |
| `VpcEndpointSecurityGroupId` | `Zero2ProdVpcEndpointSecurityGroupId` | `{VpcEndpointSg.SecurityGroupId}` | VPC Endpoint security group ID |

**View Stack Outputs** (after deployment):

```bash
# Describe stack outputs
aws cloudformation describe-stacks --stack-name NetworkStack --region us-east-1 --query "Stacks[0].Outputs"

# Expected output: JSON array of outputs
```

**Example Output**:

```json
[
  {
    "OutputKey": "VpcId",
    "OutputValue": "vpc-0a1b2c3d4e5f6g7h8",
    "ExportName": "Zero2ProdVpcId"
  },
  {
    "OutputKey": "PublicSubnetIds",
    "OutputValue": "subnet-public-1a,subnet-public-1b",
    "ExportName": "Zero2ProdPublicSubnetIds"
  },
  ...
]
```

---

### 4.2 Consuming Stack Outputs in Other Stacks

**Method 1: CloudFormation Fn::ImportValue**:

```python
from aws_cdk import Fn

# Import VPC ID from NetworkStack
vpc_id = Fn.import_value("Zero2ProdVpcId")

# Import subnet IDs
private_subnet_ids = Fn.import_value("Zero2ProdPrivateSubnetIds").split(",")
```

**Method 2: Direct Stack References** (if stacks are in same CDK app):

```python
from stacks.network_stack import NetworkStack

# Reference NetworkStack in another stack
database_stack = DatabaseStack(
    app, "DatabaseStack",
    vpc=network_stack.vpc,
    aurora_sg=network_stack.aurora_sg
)
```

---

## 5. Testing Strategy

### 5.1 Unit Tests (CDK Assertions)

**Purpose**: Test CDK constructs generate correct CloudFormation resources.

**Test Framework**: pytest with `aws_cdk.assertions`

**Test File**: `cdk/tests/unit/test_network_stack.py`

**Example Unit Tests**:

```python
import aws_cdk as cdk
from aws_cdk.assertions import Template, Match
from stacks.network_stack import NetworkStack


def test_vpc_created():
    """Test VPC is created with correct CIDR."""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    template.resource_count_is("AWS::EC2::VPC", 1)
    template.has_resource_properties("AWS::EC2::VPC", {
        "CidrBlock": "10.0.0.0/16",
        "EnableDnsHostnames": True,
        "EnableDnsSupport": True
    })


def test_subnets_created():
    """Test 4 subnets are created."""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    template.resource_count_is("AWS::EC2::Subnet", 4)


def test_security_groups_created():
    """Test 6 security groups are created."""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    template.resource_count_is("AWS::EC2::SecurityGroup", 6)


def test_vpc_endpoints_created():
    """Test 8 VPC endpoints are created."""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    template.resource_count_is("AWS::EC2::VPCEndpoint", 8)


def test_no_nat_gateway():
    """Test no NAT Gateway is created."""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    template.resource_count_is("AWS::EC2::NatGateway", 0)


def test_alb_security_group_rules():
    """Test ALB security group has correct ingress rules."""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    # Check for HTTPS ingress rule
    template.has_resource_properties("AWS::EC2::SecurityGroupIngress", {
        "IpProtocol": "tcp",
        "FromPort": 443,
        "ToPort": 443,
        "CidrIp": "0.0.0.0/0"
    })
```

**Run Unit Tests**:

```bash
cd cdk
pytest tests/unit/ -v

# Expected output: All tests pass
```

**Test Coverage**:

```bash
# Run tests with coverage
pytest tests/unit/ --cov=stacks --cov-report=term-missing

# Target coverage: > 80% for network_stack.py
```

---

### 5.2 CDK Snapshot Tests

**Purpose**: Detect unintended CloudFormation template changes.

**Test File**: `cdk/tests/unit/test_network_stack_snapshot.py`

**Snapshot Test**:

```python
import aws_cdk as cdk
from aws_cdk.assertions import Template
from stacks.network_stack import NetworkStack


def test_network_stack_snapshot(snapshot):
    """Generate CloudFormation template snapshot."""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = Template.from_stack(stack)
    
    # Compare template with snapshot
    assert template.to_json() == snapshot
```

**Generate Snapshot Baseline**:

```bash
# First run: Generate baseline snapshot
pytest tests/unit/test_network_stack_snapshot.py --snapshot-update

# Output: Snapshot saved to tests/unit/__snapshots__/
```

**Subsequent Runs**:

```bash
# Compare current template with baseline
pytest tests/unit/test_network_stack_snapshot.py

# If template changes unexpectedly: Test fails
# If change is intentional: Update snapshot with --snapshot-update
```

---

### 5.3 Integration Tests (Post-Deployment)

**Purpose**: Verify deployed infrastructure is functional.

**Test Framework**: pytest with boto3 (AWS SDK)

**Test File**: `cdk/tests/integration/test_vpc_endpoints.py`

**Example Integration Tests**:

```python
import boto3
import pytest


@pytest.fixture(scope="module")
def ec2_client():
    """Create EC2 client."""
    return boto3.client('ec2', region_name='us-east-1')


def test_vpc_exists(ec2_client):
    """Test VPC is created with correct CIDR."""
    vpcs = ec2_client.describe_vpcs(
        Filters=[{'Name': 'tag:Name', 'Values': ['zero2prod-vpc']}]
    )
    
    assert len(vpcs['Vpcs']) == 1
    assert vpcs['Vpcs'][0]['CidrBlock'] == '10.0.0.0/16'
    assert vpcs['Vpcs'][0]['EnableDnsHostnames'] == True


def test_subnets_exist(ec2_client):
    """Test 4 subnets are created."""
    subnets = ec2_client.describe_subnets(
        Filters=[{'Name': 'tag:Name', 'Values': ['zero2prod-*']}]
    )
    
    assert len(subnets['Subnets']) == 4


def test_vpc_endpoints_exist(ec2_client):
    """Test 8 VPC endpoints are created."""
    endpoints = ec2_client.describe_vpc_endpoints(
        Filters=[{'Name': 'tag:Name', 'Values': ['zero2prod-*-endpoint']}]
    )
    
    assert len(endpoints['VpcEndpoints']) == 8


def test_private_dns_enabled(ec2_client):
    """Test interface endpoints have private DNS enabled."""
    endpoints = ec2_client.describe_vpc_endpoints(
        Filters=[
            {'Name': 'vpc-endpoint-type', 'Values': ['Interface']},
            {'Name': 'tag:Name', 'Values': ['zero2prod-*-endpoint']}
        ]
    )
    
    for endpoint in endpoints['VpcEndpoints']:
        assert endpoint['PrivateDnsEnabled'] == True


def test_security_groups_exist(ec2_client):
    """Test 6 security groups are created."""
    security_groups = ec2_client.describe_security_groups(
        Filters=[{'Name': 'tag:Name', 'Values': ['zero2prod-*-sg']}]
    )
    
    assert len(security_groups['SecurityGroups']) == 6
```

**Run Integration Tests** (after deployment):

```bash
cd cdk

# Set AWS credentials
export AWS_PROFILE=zero2prod-production

# Run integration tests
pytest tests/integration/ -v

# Expected output: All tests pass
```

---

### 5.4 Testing Checklist

**Pre-Deployment Testing**:
- [ ] Unit tests pass (`pytest tests/unit/`)
- [ ] Snapshot tests pass (no unintended template changes)
- [ ] `cdk synth` succeeds (CloudFormation template generated)
- [ ] `cdk diff` reviewed (no unexpected changes)
- [ ] Code review completed (security group rules, VPC endpoints)

**Post-Deployment Testing**:
- [ ] `cdk deploy` completes successfully
- [ ] Integration tests pass (`pytest tests/integration/`)
- [ ] VPC exists with correct CIDR (`10.0.0.0/16`)
- [ ] 4 subnets created (2 public, 2 private)
- [ ] 6 security groups created
- [ ] 8 VPC endpoints created (1 Gateway, 7 Interface)
- [ ] Private DNS enabled for interface endpoints
- [ ] No NAT Gateway exists (verified absence)
- [ ] Stack outputs exported correctly

---

## 6. Rollback Strategy

### 6.1 Automatic Rollback (CloudFormation Default)

**CloudFormation Automatic Rollback**:
- If stack creation fails, CloudFormation automatically deletes all created resources
- If stack update fails, CloudFormation automatically rolls back to previous state

**Rollback Triggers**:
- Resource creation failure (e.g., VPC CIDR conflict)
- Dependency violation (e.g., security group circular dependency)
- IAM permission denied
- Resource limit exceeded

**No Manual Rollback Needed**: CloudFormation handles rollback automatically.

---

### 6.2 Manual Rollback (Deployment Failure)

**If Deployment Fails After Partial Success**:

```bash
# Option 1: Delete stack (if safe to delete)
cdk destroy NetworkStack

# Option 2: Roll back to previous stack version (if update failed)
aws cloudformation cancel-update-stack --stack-name NetworkStack --region us-east-1
```

**Rollback Steps**:

1. **Identify Failed Resource**:
   ```bash
   # View stack events to identify failure
   aws cloudformation describe-stack-events --stack-name NetworkStack --region us-east-1
   ```

2. **Fix Root Cause** (e.g., fix CDK code, increase resource limits)

3. **Redeploy**:
   ```bash
   cdk deploy NetworkStack
   ```

---

### 6.3 Rollback Testing

**Test Rollback Scenario** (in dev environment):

1. Deploy NetworkStack successfully
2. Introduce a breaking change (e.g., invalid CIDR)
3. Attempt deployment (should fail)
4. Verify CloudFormation rolls back to previous state
5. Verify resources remain unchanged after rollback

**Example Breaking Change**:

```python
# Introduce invalid VPC CIDR (will fail)
vpc = ec2.Vpc(self, "Vpc", cidr="10.0.0.0/33")  # Invalid CIDR (too small)
```

**Expected Rollback Behavior**:
- CloudFormation detects invalid CIDR
- Deployment fails
- CloudFormation rolls back to previous VPC configuration
- No resources are left in inconsistent state

---

## 7. CI/CD Integration (GitHub Actions)

### 7.1 GitHub Actions Workflow

**File**: `.github/workflows/deploy-network-stack.yml`

**Workflow Overview**:

1. Trigger on push to `main` branch (if network stack files changed)
2. Configure AWS credentials (OIDC)
3. Install CDK CLI and Python dependencies
4. Run unit tests
5. CDK synth (generate CloudFormation template)
6. CDK diff (preview changes)
7. Manual approval gate (production only)
8. CDK deploy (deploy stack)
9. Run integration tests (smoke tests)

**Workflow Definition**:

```yaml
name: Deploy Network Stack

on:
  push:
    branches:
      - main
    paths:
      - 'cdk/stacks/network_stack.py'
      - 'cdk/app.py'
      - 'cdk/requirements.txt'
      - '.github/workflows/deploy-network-stack.yml'

jobs:
  deploy-network-stack:
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # Required for OIDC
      contents: read
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsCDKRole
          aws-region: us-east-1
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install CDK CLI
        run: npm install -g aws-cdk
      
      - name: Install Python dependencies
        run: |
          cd cdk
          pip install -r requirements.txt
      
      - name: Run unit tests
        run: |
          cd cdk
          pytest tests/unit/ -v
      
      - name: CDK synth
        run: |
          cd cdk
          cdk synth NetworkStack
      
      - name: CDK diff
        run: |
          cd cdk
          cdk diff NetworkStack
      
      - name: Manual approval (production only)
        if: github.ref == 'refs/heads/main'
        uses: trstringer/manual-approval@v1
        with:
          secret: ${{ github.TOKEN }}
          approvers: network-team
          minimum-approvals: 1
          issue-title: "Deploy NetworkStack to production"
      
      - name: CDK deploy
        run: |
          cd cdk
          cdk deploy NetworkStack --require-approval never
      
      - name: Run integration tests (smoke tests)
        run: |
          cd cdk
          pytest tests/integration/ -v
```

---

### 7.2 OIDC Authentication Setup

**Purpose**: Use temporary AWS credentials via OIDC (no long-lived access keys stored in GitHub secrets).

**IAM Role Setup** (one-time):

1. **Create IAM OIDC Identity Provider** (in AWS Console):
   - Provider URL: `https://token.actions.githubusercontent.com`
   - Audience: `sts.amazonaws.com`

2. **Create IAM Role** (`GitHubActionsCDKRole`):
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
         },
         "Action": "sts:AssumeRoleWithWebIdentity",
         "Condition": {
           "StringEquals": {
             "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
           },
           "StringLike": {
             "token.actions.githubusercontent.com:sub": "repo:your-org/zero2prod:*"
           }
         }
       }
     ]
   }
   ```

3. **Attach IAM Policies** to `GitHubActionsCDKRole`:
   - `arn:aws:iam::aws:policy/PowerUserAccess` (or custom policy with least privilege)

**Verify OIDC Authentication**:

```bash
# Trigger GitHub Actions workflow
git push origin main

# Verify workflow uses OIDC (no access keys in logs)
# Expected: "Assuming role arn:aws:iam::123456789012:role/GitHubActionsCDKRole"
```

---

### 7.3 Manual Approval Gate

**Purpose**: Require explicit approval for production deployments (network changes are high-risk).

**Configuration**:

```yaml
- name: Manual approval (production only)
  if: github.ref == 'refs/heads/main'
  uses: trstringer/manual-approval@v1
  with:
    secret: ${{ github.TOKEN }}
    approvers: network-team
    minimum-approvals: 1
    issue-title: "Deploy NetworkStack to production"
```

**Approval Process**:

1. GitHub Actions creates a GitHub issue: "Deploy NetworkStack to production"
2. Designated approvers (e.g., `network-team`) review changes
3. Approver comments on issue: "approved"
4. Workflow resumes and deploys stack

**Bypass Manual Approval** (for dev/staging):

```yaml
- name: Manual approval (production only)
  if: github.ref == 'refs/heads/main' && env.ENVIRONMENT == 'production'
  # Only require approval for production
```

---

### 7.4 Deployment Notifications

**Slack Notification** (on deployment success/failure):

```yaml
- name: Notify Slack on success
  if: success()
  uses: slackapi/slack-github-action@v1
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
    payload: |
      {
        "text": "NetworkStack deployed successfully to production",
        "attachments": [
          {
            "color": "good",
            "fields": [
              {"title": "Stack", "value": "NetworkStack", "short": true},
              {"title": "Environment", "value": "production", "short": true},
              {"title": "Commit", "value": "${{ github.sha }}", "short": false}
            ]
          }
        ]
      }

- name: Notify Slack on failure
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
    payload: |
      {
        "text": "NetworkStack deployment FAILED",
        "attachments": [
          {
            "color": "danger",
            "fields": [
              {"title": "Stack", "value": "NetworkStack", "short": true},
              {"title": "Environment", "value": "production", "short": true},
              {"title": "Commit", "value": "${{ github.sha }}", "short": false}
            ]
          }
        ]
      }
```

---

## 8. Deployment Checklist

### 8.1 Pre-Deployment Checklist

**Before Deploying NetworkStack**:

- [ ] CDK bootstrap completed (`cdk bootstrap aws://account/region`)
- [ ] AWS credentials configured (OIDC or access keys)
- [ ] Environment variables set (`CDK_DEFAULT_ACCOUNT`, `CDK_DEFAULT_REGION`)
- [ ] CDK CLI installed (`cdk --version`)
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Unit tests pass (`pytest tests/unit/`)
- [ ] `cdk synth` succeeds (CloudFormation template generated)
- [ ] `cdk diff` reviewed (no unexpected changes)
- [ ] Code review completed (security group rules, VPC endpoints)
- [ ] Change management ticket created (production deployments)

---

### 8.2 Deployment Checklist

**During Deployment**:

- [ ] Monitor CloudFormation events (`aws cloudformation describe-stack-events`)
- [ ] Verify resource creation progress (VPC → Subnets → Security Groups → VPC Endpoints)
- [ ] Check for deployment errors (CloudFormation stack status = `CREATE_FAILED`)
- [ ] If deployment fails, review error messages and roll back

**Expected Deployment Time**: ~5-7 minutes

---

### 8.3 Post-Deployment Checklist

**After Deployment Completes**:

- [ ] Stack status = `CREATE_COMPLETE` or `UPDATE_COMPLETE`
- [ ] Stack outputs exported (verify with `aws cloudformation describe-stacks`)
- [ ] VPC exists with correct CIDR (`10.0.0.0/16`)
- [ ] 4 subnets created (2 public, 2 private)
- [ ] 6 security groups created with correct rules
- [ ] 8 VPC endpoints created (1 Gateway, 7 Interface)
- [ ] Private DNS enabled for interface endpoints
- [ ] No NAT Gateway exists (verified absence)
- [ ] Integration tests pass (`pytest tests/integration/`)
- [ ] CloudWatch metrics available (VPC endpoint data processed)
- [ ] Update change management ticket (deployment complete)

---

## 9. Troubleshooting

### 9.1 Common Deployment Errors

**Error: "VPC CIDR conflict"**

```
Error: Cannot create VPC with CIDR 10.0.0.0/16: CIDR block overlaps with existing VPC
```

**Solution**: Change VPC CIDR or delete conflicting VPC.

---

**Error: "Security group circular dependency"**

```
Error: Circular dependency detected: SecurityGroup A references SecurityGroup B, which references SecurityGroup A
```

**Solution**: Create security groups first, then add rules (as implemented in NetworkStack).

---

**Error: "IAM permission denied"**

```
Error: User is not authorized to perform: ec2:CreateVpcEndpoint
```

**Solution**: Add `ec2:CreateVpcEndpoint` permission to IAM role/user.

---

**Error: "VPC endpoint limit exceeded"**

```
Error: Cannot create VPC endpoint: VpcEndpointLimitExceeded
```

**Solution**: Request VPC endpoint limit increase (default: 255 per VPC).

---

### 9.2 Debug Commands

**View CloudFormation Stack Events**:

```bash
aws cloudformation describe-stack-events --stack-name NetworkStack --region us-east-1 --max-items 20
```

**View Stack Status**:

```bash
aws cloudformation describe-stacks --stack-name NetworkStack --region us-east-1 --query "Stacks[0].StackStatus"
```

**View Failed Resources**:

```bash
aws cloudformation describe-stack-resources --stack-name NetworkStack --region us-east-1 --query "StackResources[?ResourceStatus=='CREATE_FAILED']"
```

**View CDK Context** (AZ mapping):

```bash
cat cdk.context.json | jq
```

---

## 10. Summary

**Deployment Overview**:
- Bootstrap CDK (one-time): `cdk bootstrap aws://account/region`
- Synthesize template: `cdk synth NetworkStack`
- Preview changes: `cdk diff NetworkStack`
- Deploy stack: `cdk deploy NetworkStack`
- Verify deployment: `pytest tests/integration/`

**Testing Strategy**:
- Unit tests: Verify CloudFormation template correctness
- Snapshot tests: Detect unintended template changes
- Integration tests: Verify deployed infrastructure functionality

**CI/CD Integration**:
- GitHub Actions workflow triggers on push to `main`
- OIDC authentication (no long-lived access keys)
- Manual approval gate for production deployments
- Slack notifications on success/failure

**Rollback Strategy**:
- CloudFormation automatic rollback on failure
- Manual rollback: `cdk destroy NetworkStack` or `aws cloudformation cancel-update-stack`

**Deployment Time**: ~5-7 minutes

**Next Steps**: Proceed to Code Generation stage to implement NetworkStack.

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-12  
**Status**: Ready for Implementation
