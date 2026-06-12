#!/usr/bin/env python3
"""
AWS CDK Application Entry Point
Zero2Prod Newsletter Service - AWS Modernization

This CDK application deploys the AWS infrastructure for the Zero2Prod
newsletter service following AWS Well-Architected Framework principles.
"""

import os
import aws_cdk as cdk
from stacks.network_stack import NetworkStack

# Environment configuration
AWS_ACCOUNT = os.environ.get('CDK_DEFAULT_ACCOUNT')
AWS_REGION = os.environ.get('CDK_DEFAULT_REGION', 'us-east-1')

app = cdk.App()

# Network Infrastructure Stack
network_stack = NetworkStack(
    app,
    "Zero2ProdNetworkStack",
    env=cdk.Environment(
        account=AWS_ACCOUNT,
        region=AWS_REGION
    ),
    description="Network infrastructure for Zero2Prod newsletter service (VPC, Subnets, Security Groups, VPC Endpoints)",
    tags={
        'Environment': 'production',
        'Project': 'Zero2Prod',
        'ManagedBy': 'AWS-CDK',
        'Component': 'Network'
    }
)

app.synth()
