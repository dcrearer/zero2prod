#!/bin/bash
set -e

echo "=========================================="
echo "CDK Destroy Script"
echo "=========================================="
echo ""
echo "⚠️  WARNING: This will DELETE all network infrastructure"
echo "This includes:"
echo "  - VPC and subnets"
echo "  - Security groups"
echo "  - VPC endpoints"
echo "  - All associated resources"
echo ""

# Check if AWS credentials are configured
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ ERROR: AWS credentials not configured"
    exit 1
fi

echo "✅ AWS credentials configured"
echo ""

# Get AWS account and region
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}

echo "AWS Account: $AWS_ACCOUNT"
echo "AWS Region: $AWS_REGION"
echo ""

# Confirm destruction
read -p "Are you sure you want to destroy the stack? (yes/NO): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Destruction cancelled"
    exit 0
fi
echo ""

read -p "Type 'DELETE' to confirm: " confirm2
if [ "$confirm2" != "DELETE" ]; then
    echo "Destruction cancelled"
    exit 0
fi
echo ""

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ ERROR: Virtual environment not found"
    exit 1
fi

echo "Activating virtual environment..."
source .venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Destroy stack
echo "Destroying Zero2ProdNetworkStack..."
echo "This will take approximately 2-3 minutes..."
echo ""

if cdk destroy --force; then
    echo ""
    echo "=========================================="
    echo "✅ Stack Destroyed"
    echo "=========================================="
    echo ""
    echo "All network infrastructure has been deleted."
else
    echo ""
    echo "=========================================="
    echo "❌ Destruction Failed"
    echo "=========================================="
    echo ""
    echo "Check CloudFormation events for details:"
    echo "  aws cloudformation describe-stack-events --stack-name Zero2ProdNetworkStack"
    exit 1
fi
