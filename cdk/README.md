# Zero2Prod AWS CDK Infrastructure

AWS CDK infrastructure code for the Zero2Prod newsletter service modernization.

## Overview

This CDK application deploys AWS infrastructure following the Well-Architected Framework principles. The infrastructure is organized into modular stacks:

- **NetworkStack**: VPC, subnets, security groups, VPC endpoints
- Additional stacks will be added for database, compute, worker, authentication, and observability components

## Prerequisites

- Python 3.11 or higher
- AWS CLI configured with appropriate credentials
- AWS CDK CLI: `npm install -g aws-cdk`
- An AWS account with appropriate permissions

## Setup

1. Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Bootstrap CDK (first time only):
```bash
./scripts/bootstrap.sh
```

## Deployment

### Deploy Network Infrastructure

```bash
# Show changes (dry run)
./scripts/diff.sh

# Deploy to AWS
./scripts/deploy.sh
```

### Destroy Infrastructure

```bash
./scripts/destroy.sh
```

## Testing

Run unit tests:
```bash
pytest tests/unit/ -v
```

Run integration tests (requires deployed infrastructure):
```bash
pytest tests/integration/ -v
```

Run all tests with coverage:
```bash
pytest --cov=stacks --cov-report=html
```

## Project Structure

```
cdk/
├── app.py                      # CDK app entry point
├── cdk.json                    # CDK configuration
├── requirements.txt            # Python dependencies
├── stacks/                     # CDK stack definitions
│   ├── __init__.py
│   └── network_stack.py        # Network infrastructure
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
└── scripts/                    # Deployment scripts
    ├── bootstrap.sh
    ├── deploy.sh
    ├── destroy.sh
    └── diff.sh
```

## Architecture

### Network Infrastructure

- **VPC**: 10.0.0.0/16 CIDR block with DNS enabled
- **Subnets**: 
  - 2 Public subnets (10.0.1.0/24, 10.0.2.0/24) in us-east-1a, us-east-1b
  - 2 Private subnets (10.0.10.0/24, 10.0.11.0/24) in us-east-1a, us-east-1b
- **Security Groups**: Layered security for ALB, ECS, Aurora, ElastiCache, Lambda, VPC Endpoints
- **VPC Endpoints**: Private connectivity to AWS services (S3, ECR, CloudWatch, Secrets Manager, STS, SES, SQS)

### Multi-AZ Design

All infrastructure is deployed across two Availability Zones (us-east-1a, us-east-1b) for high availability and fault tolerance.

### Private Networking

The architecture uses VPC endpoints for AWS service connectivity, eliminating the need for NAT Gateways and providing enhanced security and cost savings.

## Cost Estimation

Network infrastructure monthly costs:
- VPC Endpoints (7 Interface): ~$51/month
- Data transfer (estimated): ~$10-20/month
- Total: ~$61-71/month

## Security

- All data stores encrypted at rest (AWS KMS)
- All network traffic encrypted in transit (TLS 1.2+)
- Private subnets with no direct internet access
- Security groups with least-privilege access rules
- VPC Flow Logs enabled for network monitoring

## Compliance

This infrastructure follows:
- AWS Well-Architected Framework
- Security Baseline extension (SECURITY-01 through SECURITY-06)
- NFR requirements defined in requirements.md

## Documentation

Full design documentation is available in:
- `/aidlc-docs/construction/unit-1-network/functional-design/`
- `/aidlc-docs/construction/unit-1-network/nfr-requirements/`
- `/aidlc-docs/construction/unit-1-network/nfr-design/`
- `/aidlc-docs/construction/unit-1-network/infrastructure-design/`

## Troubleshooting

### CDK Bootstrap Issues
If you encounter bootstrap errors, ensure you have the correct AWS credentials and permissions:
```bash
aws sts get-caller-identity
```

### Deployment Failures
Check CloudFormation events in the AWS Console for detailed error messages:
```bash
aws cloudformation describe-stack-events --stack-name Zero2ProdNetworkStack
```

### VPC Endpoint Connectivity
Test VPC endpoint connectivity from within the VPC:
```bash
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=<vpc-id>"
```

## Support

For issues or questions, refer to the design documentation or contact the infrastructure team.
