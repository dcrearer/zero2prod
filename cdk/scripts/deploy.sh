#!/bin/bash
set -e

echo "=========================================="
echo "CDK Deployment Script"
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

# Run unit tests
echo "Running unit tests..."
if pytest tests/unit/ -v --tb=short; then
    echo "✅ Unit tests passed"
else
    echo "❌ Unit tests failed"
    exit 1
fi
echo ""

# Synthesize CloudFormation template
echo "Synthesizing CloudFormation template..."
if cdk synth > /dev/null; then
    echo "✅ Synthesis successful"
else
    echo "❌ Synthesis failed"
    exit 1
fi
echo ""

# Show diff
echo "Showing deployment changes..."
cdk diff
echo ""

# Confirm deployment
read -p "Deploy to AWS? (y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Deployment cancelled"
    exit 0
fi
echo ""

# Deploy
echo "Deploying Zero2ProdNetworkStack..."
echo "This will take approximately 5-7 minutes..."
echo ""

if cdk deploy --require-approval never --outputs-file cdk-outputs.json; then
    echo ""
    echo "=========================================="
    echo "✅ Deployment Complete"
    echo "=========================================="
    echo ""
    echo "Stack outputs saved to: cdk-outputs.json"
    echo ""
    echo "To view stack resources:"
    echo "  aws cloudformation describe-stack-resources --stack-name Zero2ProdNetworkStack"
    echo ""
    echo "To view stack outputs:"
    echo "  aws cloudformation describe-stacks --stack-name Zero2ProdNetworkStack --query 'Stacks[0].Outputs'"
    echo ""
    echo "To run integration tests:"
    echo "  pytest tests/integration/ -v"
else
    echo ""
    echo "=========================================="
    echo "❌ Deployment Failed"
    echo "=========================================="
    echo ""
    echo "Check CloudFormation events for details:"
    echo "  aws cloudformation describe-stack-events --stack-name Zero2ProdNetworkStack"
    exit 1
fi
