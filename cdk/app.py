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
from stacks.database_stack import DatabaseStack
from stacks.cache_stack import CacheStack
from stacks.compute_stack import ComputeStack

# Environment configuration
AWS_ACCOUNT = os.environ.get('CDK_DEFAULT_ACCOUNT')
AWS_REGION = os.environ.get('CDK_DEFAULT_REGION', 'us-east-1')

app = cdk.App()

env = cdk.Environment(account=AWS_ACCOUNT, region=AWS_REGION)

# Unit 1: Network Infrastructure Stack
network_stack = NetworkStack(
    app,
    "Zero2ProdNetworkStack",
    env=env,
    description="Network infrastructure for Zero2Prod newsletter service (VPC, Subnets, Security Groups, VPC Endpoints)",
    tags={
        'Environment': 'production',
        'Project': 'Zero2Prod',
        'ManagedBy': 'AWS-CDK',
        'Component': 'Network'
    }
)

# Unit 2: Database Infrastructure Stack
database_stack = DatabaseStack(
    app,
    "Zero2ProdDatabaseStack",
    vpc=network_stack.vpc,
    private_subnets=network_stack.vpc.isolated_subnets,
    aurora_sg=network_stack.aurora_sg,
    env=env,
    description="Database infrastructure for Zero2Prod newsletter service (Aurora PostgreSQL Serverless v2, Secrets Manager, CloudWatch)",
    tags={
        'Environment': 'production',
        'Project': 'Zero2Prod',
        'ManagedBy': 'AWS-CDK',
        'Component': 'Database'
    }
)

# Dependency: Database stack requires Network stack (implicit via passed resources)
database_stack.add_dependency(network_stack)

# Unit 3: Cache Infrastructure Stack
cache_stack = CacheStack(
    app,
    "Zero2ProdCacheStack",
    vpc=network_stack.vpc,
    private_subnets=network_stack.vpc.isolated_subnets,
    elasticache_sg=network_stack.elasticache_sg,
    alarm_topic=database_stack.alarm_topic,
    env=env,
    description="Cache infrastructure for Zero2Prod newsletter service (ElastiCache Serverless for Redis, Secrets Manager, CloudWatch)",
    tags={
        'Environment': 'production',
        'Project': 'Zero2Prod',
        'ManagedBy': 'AWS-CDK',
        'Component': 'Cache'
    }
)

# Dependencies: Cache stack requires Network stack (VPC, subnets, SGs) and Database stack (SNS topic)
cache_stack.add_dependency(network_stack)
cache_stack.add_dependency(database_stack)

# Unit 4: Compute Infrastructure Stack
compute_stack = ComputeStack(
    app,
    "Zero2ProdComputeStack",
    vpc=network_stack.vpc,
    public_subnets=network_stack.vpc.public_subnets,
    private_subnets=network_stack.vpc.isolated_subnets,
    alb_sg=network_stack.alb_sg,
    ecs_sg=network_stack.ecs_sg,
    database_secret=database_stack.database_secret,
    cache_secret=cache_stack.cache_secret,
    env=env,
    description="Compute infrastructure for Zero2Prod newsletter service (ALB, ECS Fargate, Auto-Scaling, ECR, CloudWatch)",
    tags={
        'Environment': 'production',
        'Project': 'Zero2Prod',
        'ManagedBy': 'AWS-CDK',
        'Component': 'Compute'
    }
)

# Dependencies: Compute stack requires Network, Database, and Cache stacks
compute_stack.add_dependency(network_stack)
compute_stack.add_dependency(database_stack)
compute_stack.add_dependency(cache_stack)

app.synth()
