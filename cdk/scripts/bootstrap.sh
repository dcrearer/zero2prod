#!/bin/bash
set -e

echo "=========================================="
echo "CDK Bootstrap Script"
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

# Check if Python virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Bootstrap CDK
echo "Bootstrapping CDK..."
echo "This may take a few minutes on first run..."
cdk bootstrap aws://$AWS_ACCOUNT/$AWS_REGION

echo ""
echo "=========================================="
echo "✅ CDK Bootstrap Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review changes: ./scripts/diff.sh"
echo "  2. Deploy stack: ./scripts/deploy.sh"
