"""
Network Infrastructure Stack for Zero2Prod Newsletter Service

This stack creates the foundational network infrastructure including:
- VPC with public and private subnets across 2 Availability Zones
- Internet Gateway for public subnet connectivity
- Route tables for public and private subnets
- Security groups for ALB, ECS, Aurora, ElastiCache, Lambda, and VPC Endpoints
- VPC Endpoints for private AWS service connectivity (S3, ECR, CloudWatch, etc.)

Architecture follows AWS Well-Architected Framework with emphasis on:
- Security: Private subnets, least-privilege security groups, encryption in transit
- Reliability: Multi-AZ deployment for high availability
- Cost Optimization: VPC endpoints instead of NAT Gateway
- Operational Excellence: Comprehensive tagging and CloudFormation exports
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    Tags,
    aws_ec2 as ec2,
)
from constructs import Construct


class NetworkStack(Stack):
    """
    Network infrastructure stack for Zero2Prod newsletter service.

    Creates VPC, subnets, security groups, and VPC endpoints following
    the network design specifications.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC Configuration
        self.vpc = self._create_vpc()

        # Security Groups (create all first to avoid circular dependencies)
        self.alb_sg = self._create_alb_security_group()
        self.ecs_sg = self._create_ecs_security_group()
        self.aurora_sg = self._create_aurora_security_group()
        self.elasticache_sg = self._create_elasticache_security_group()
        self.lambda_sg = self._create_lambda_security_group()
        self.vpc_endpoint_sg = self._create_vpc_endpoint_security_group()

        # VPC Endpoints (created before adding cross-SG rules)
        self._create_vpc_endpoints()

        # Add security group rules after all SGs and endpoints are created
        self._configure_security_group_rules()

        # CloudFormation Outputs
        self._create_outputs()

    def _create_vpc(self) -> ec2.Vpc:
        """
        Create VPC with public and private subnets across 2 Availability Zones.

        VPC Configuration:
        - CIDR: 10.0.0.0/16
        - DNS: Enabled
        - Public Subnets: 10.0.1.0/24 (us-east-1a), 10.0.2.0/24 (us-east-1b)
        - Private Subnets: 10.0.10.0/24 (us-east-1a), 10.0.11.0/24 (us-east-1b)
        - NAT Gateways: 0 (using VPC endpoints for AWS service access)
        """
        vpc = ec2.Vpc(
            self,
            "Zero2ProdVPC",
            vpc_name="zero2prod-vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,
            nat_gateways=0,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        Tags.of(vpc).add("Name", "zero2prod-vpc")
        Tags.of(vpc).add("Component", "Network")

        return vpc

    def _create_alb_security_group(self) -> ec2.SecurityGroup:
        """
        Create security group for Application Load Balancer.

        Ingress Rules:
        - HTTP (80) from 0.0.0.0/0
        - HTTPS (443) from 0.0.0.0/0

        Egress Rules:
        - HTTP (8000) to ECS Security Group (added later to avoid circular dependency)
        """
        sg = ec2.SecurityGroup(
            self,
            "ALBSecurityGroup",
            vpc=self.vpc,
            security_group_name="zero2prod-alb-sg",
            description="Security group for Zero2Prod Application Load Balancer",
            allow_all_outbound=False,
        )

        sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP from internet"
        )

        sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from internet"
        )

        Tags.of(sg).add("Name", "zero2prod-alb-sg")
        Tags.of(sg).add("Component", "Network")

        return sg

    def _create_ecs_security_group(self) -> ec2.SecurityGroup:
        """
        Create security group for ECS Fargate tasks.

        Ingress Rules:
        - HTTP (8000) from ALB Security Group (added later to avoid circular dependency)

        Egress Rules:
        - PostgreSQL (5432) to Aurora Security Group (added later)
        - Redis (6379) to ElastiCache Security Group (added later)
        - HTTPS (443) to VPC Endpoint Security Group (added later)
        """
        sg = ec2.SecurityGroup(
            self,
            "ECSSecurityGroup",
            vpc=self.vpc,
            security_group_name="zero2prod-ecs-sg",
            description="Security group for Zero2Prod ECS Fargate tasks",
            allow_all_outbound=False,
        )

        Tags.of(sg).add("Name", "zero2prod-ecs-sg")
        Tags.of(sg).add("Component", "Network")

        return sg

    def _create_aurora_security_group(self) -> ec2.SecurityGroup:
        """
        Create security group for Aurora PostgreSQL cluster.

        Ingress Rules:
        - PostgreSQL (5432) from ECS Security Group (added later)
        - PostgreSQL (5432) from Lambda Security Group (added later)

        Egress Rules:
        - None (database does not initiate outbound connections)
        """
        sg = ec2.SecurityGroup(
            self,
            "AuroraSecurityGroup",
            vpc=self.vpc,
            security_group_name="zero2prod-aurora-sg",
            description="Security group for Zero2Prod Aurora PostgreSQL cluster",
            allow_all_outbound=False,
        )

        Tags.of(sg).add("Name", "zero2prod-aurora-sg")
        Tags.of(sg).add("Component", "Network")

        return sg

    def _create_elasticache_security_group(self) -> ec2.SecurityGroup:
        """
        Create security group for ElastiCache Redis cluster.

        Ingress Rules:
        - Redis (6379) from ECS Security Group (added later)

        Egress Rules:
        - None (cache does not initiate outbound connections)
        """
        sg = ec2.SecurityGroup(
            self,
            "ElastiCacheSecurityGroup",
            vpc=self.vpc,
            security_group_name="zero2prod-elasticache-sg",
            description="Security group for Zero2Prod ElastiCache Redis cluster",
            allow_all_outbound=False,
        )

        Tags.of(sg).add("Name", "zero2prod-elasticache-sg")
        Tags.of(sg).add("Component", "Network")

        return sg

    def _create_lambda_security_group(self) -> ec2.SecurityGroup:
        """
        Create security group for Lambda worker functions.

        Ingress Rules:
        - None (Lambda functions do not accept inbound connections)

        Egress Rules:
        - PostgreSQL (5432) to Aurora Security Group
        - HTTPS (443) to VPC Endpoint Security Group
        """
        sg = ec2.SecurityGroup(
            self,
            "LambdaSecurityGroup",
            vpc=self.vpc,
            security_group_name="zero2prod-lambda-sg",
            description="Security group for Zero2Prod Lambda worker functions",
            allow_all_outbound=False,
        )

        Tags.of(sg).add("Name", "zero2prod-lambda-sg")
        Tags.of(sg).add("Component", "Network")

        return sg

    def _create_vpc_endpoint_security_group(self) -> ec2.SecurityGroup:
        """
        Create security group for VPC Interface Endpoints.

        Ingress Rules:
        - HTTPS (443) from ECS Security Group (added later)
        - HTTPS (443) from Lambda Security Group (added later)

        Egress Rules:
        - None (endpoints do not initiate outbound connections)
        """
        sg = ec2.SecurityGroup(
            self,
            "VPCEndpointSecurityGroup",
            vpc=self.vpc,
            security_group_name="zero2prod-vpc-endpoint-sg",
            description="Security group for Zero2Prod VPC Interface Endpoints",
            allow_all_outbound=False,
        )

        Tags.of(sg).add("Name", "zero2prod-vpc-endpoint-sg")
        Tags.of(sg).add("Component", "Network")

        return sg

    def _configure_security_group_rules(self) -> None:
        """
        Configure security group rules after all security groups are created.
        This avoids circular dependencies in CloudFormation.

        Note: CDK automatically creates corresponding egress rules when using
        ec2.Peer.security_group_id(), so we only need to define ingress rules.
        """
        # ECS ingress from ALB (port 8000)
        self.ecs_sg.connections.allow_from(
            other=self.alb_sg,
            port_range=ec2.Port.tcp(8000),
            description="Allow HTTP from ALB"
        )

        # Aurora ingress from ECS (port 5432)
        self.aurora_sg.connections.allow_from(
            other=self.ecs_sg,
            port_range=ec2.Port.tcp(5432),
            description="Allow PostgreSQL from ECS"
        )

        # Aurora ingress from Lambda (port 5432)
        self.aurora_sg.connections.allow_from(
            other=self.lambda_sg,
            port_range=ec2.Port.tcp(5432),
            description="Allow PostgreSQL from Lambda"
        )

        # ElastiCache ingress from ECS (port 6379)
        self.elasticache_sg.connections.allow_from(
            other=self.ecs_sg,
            port_range=ec2.Port.tcp(6379),
            description="Allow Redis from ECS"
        )

        # VPC Endpoints ingress from ECS (port 443)
        self.vpc_endpoint_sg.connections.allow_from(
            other=self.ecs_sg,
            port_range=ec2.Port.tcp(443),
            description="Allow HTTPS from ECS"
        )

        # VPC Endpoints ingress from Lambda (port 443)
        self.vpc_endpoint_sg.connections.allow_from(
            other=self.lambda_sg,
            port_range=ec2.Port.tcp(443),
            description="Allow HTTPS from Lambda"
        )

    def _create_vpc_endpoints(self) -> None:
        """
        Create VPC endpoints for private AWS service connectivity.

        Gateway Endpoints (no additional cost):
        - S3

        Interface Endpoints ($0.01/hour each):
        - ECR API
        - ECR DKR
        - CloudWatch Logs
        - Secrets Manager
        - STS
        - SES
        - SQS
        """
        # S3 Gateway Endpoint (no cost)
        s3_endpoint = self.vpc.add_gateway_endpoint(
            "S3GatewayEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)],
        )
        Tags.of(s3_endpoint).add("Name", "zero2prod-s3-endpoint")
        Tags.of(s3_endpoint).add("Component", "Network")

        # ECR API Interface Endpoint
        ecr_api_endpoint = self.vpc.add_interface_endpoint(
            "ECRAPIEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ECR,
            security_groups=[self.vpc_endpoint_sg],
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            private_dns_enabled=True,
        )
        Tags.of(ecr_api_endpoint).add("Name", "zero2prod-ecr-api-endpoint")
        Tags.of(ecr_api_endpoint).add("Component", "Network")

        # ECR DKR Interface Endpoint
        ecr_dkr_endpoint = self.vpc.add_interface_endpoint(
            "ECRDKREndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
            security_groups=[self.vpc_endpoint_sg],
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            private_dns_enabled=True,
        )
        Tags.of(ecr_dkr_endpoint).add("Name", "zero2prod-ecr-dkr-endpoint")
        Tags.of(ecr_dkr_endpoint).add("Component", "Network")

        # CloudWatch Logs Interface Endpoint
        logs_endpoint = self.vpc.add_interface_endpoint(
            "CloudWatchLogsEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            security_groups=[self.vpc_endpoint_sg],
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            private_dns_enabled=True,
        )
        Tags.of(logs_endpoint).add("Name", "zero2prod-logs-endpoint")
        Tags.of(logs_endpoint).add("Component", "Network")

        # Secrets Manager Interface Endpoint
        secrets_endpoint = self.vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            security_groups=[self.vpc_endpoint_sg],
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            private_dns_enabled=True,
        )
        Tags.of(secrets_endpoint).add("Name", "zero2prod-secrets-endpoint")
        Tags.of(secrets_endpoint).add("Component", "Network")

        # STS Interface Endpoint
        sts_endpoint = self.vpc.add_interface_endpoint(
            "STSEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.STS,
            security_groups=[self.vpc_endpoint_sg],
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            private_dns_enabled=True,
        )
        Tags.of(sts_endpoint).add("Name", "zero2prod-sts-endpoint")
        Tags.of(sts_endpoint).add("Component", "Network")

        # SES Interface Endpoint
        ses_endpoint = self.vpc.add_interface_endpoint(
            "SESEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SES,
            security_groups=[self.vpc_endpoint_sg],
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            private_dns_enabled=True,
        )
        Tags.of(ses_endpoint).add("Name", "zero2prod-ses-endpoint")
        Tags.of(ses_endpoint).add("Component", "Network")

        # SQS Interface Endpoint
        sqs_endpoint = self.vpc.add_interface_endpoint(
            "SQSEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SQS,
            security_groups=[self.vpc_endpoint_sg],
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            private_dns_enabled=True,
        )
        Tags.of(sqs_endpoint).add("Name", "zero2prod-sqs-endpoint")
        Tags.of(sqs_endpoint).add("Component", "Network")

    def _create_outputs(self) -> None:
        """
        Create CloudFormation outputs for cross-stack references.

        Exports:
        - VPC ID
        - Public Subnet IDs (comma-separated)
        - Private Subnet IDs (comma-separated)
        - Security Group IDs (ALB, ECS, Aurora, ElastiCache, Lambda, VPC Endpoint)
        """
        CfnOutput(
            self,
            "VPCId",
            value=self.vpc.vpc_id,
            export_name="Zero2Prod-VPC-Id",
            description="VPC ID for Zero2Prod infrastructure"
        )

        public_subnet_ids = [subnet.subnet_id for subnet in self.vpc.public_subnets]
        CfnOutput(
            self,
            "PublicSubnetIds",
            value=",".join(public_subnet_ids),
            export_name="Zero2Prod-PublicSubnet-Ids",
            description="Public subnet IDs (comma-separated)"
        )

        private_subnet_ids = [subnet.subnet_id for subnet in self.vpc.isolated_subnets]
        CfnOutput(
            self,
            "PrivateSubnetIds",
            value=",".join(private_subnet_ids),
            export_name="Zero2Prod-PrivateSubnet-Ids",
            description="Private subnet IDs (comma-separated)"
        )

        CfnOutput(
            self,
            "ALBSecurityGroupId",
            value=self.alb_sg.security_group_id,
            export_name="Zero2Prod-ALB-SG-Id",
            description="ALB Security Group ID"
        )

        CfnOutput(
            self,
            "ECSSecurityGroupId",
            value=self.ecs_sg.security_group_id,
            export_name="Zero2Prod-ECS-SG-Id",
            description="ECS Security Group ID"
        )

        CfnOutput(
            self,
            "AuroraSecurityGroupId",
            value=self.aurora_sg.security_group_id,
            export_name="Zero2Prod-Aurora-SG-Id",
            description="Aurora Security Group ID"
        )

        CfnOutput(
            self,
            "ElastiCacheSecurityGroupId",
            value=self.elasticache_sg.security_group_id,
            export_name="Zero2Prod-ElastiCache-SG-Id",
            description="ElastiCache Security Group ID"
        )

        CfnOutput(
            self,
            "LambdaSecurityGroupId",
            value=self.lambda_sg.security_group_id,
            export_name="Zero2Prod-Lambda-SG-Id",
            description="Lambda Security Group ID"
        )

        CfnOutput(
            self,
            "VPCEndpointSecurityGroupId",
            value=self.vpc_endpoint_sg.security_group_id,
            export_name="Zero2Prod-VPCEndpoint-SG-Id",
            description="VPC Endpoint Security Group ID"
        )
