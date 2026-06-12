#!/bin/bash
set -e

echo "=========================================="
echo "CDK Diff Script"
echo "=========================================="
echo ""

# Check if AWS credentials are configured
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ ERROR: AWS credentials not configured"
    echo "Please configure AWS credentials using 'aws configure' or environment variables"
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

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ ERROR: Virtual environment not found"
    echo "Please run ./scripts/bootstrap.sh first"
    exit 1
fi

echo "Activating virtual environment..."
source .venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Synthesize and show diff
echo "Showing changes between local code and deployed stack..."
echo ""

cdk diff

echo ""
echo "=========================================="
echo "Diff Complete"
echo "=========================================="
echo ""
echo "To deploy changes:"
echo "  ./scripts/deploy.sh"
