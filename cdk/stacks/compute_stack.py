"""
Unit 4: Compute Infrastructure Stack

This stack deploys the ECS Fargate compute infrastructure for the Zero2Prod
web application, including:
- Application Load Balancer (ALB) with HTTP→HTTPS redirect
- ECS Fargate cluster and service
- Auto-scaling (2-10 tasks, 70% CPU target)
- ECR repository for container images
- IAM roles (task execution, task runtime)
- CloudWatch Logs for container logging
- Secrets Manager for HMAC secret

Dependencies:
- NetworkStack (Unit 1): VPC, subnets, security groups
- DatabaseStack (Unit 2): Database secret ARN
- CacheStack (Unit 3): Cache secret ARN

Exports:
- ECS cluster name (for Unit 5 - Worker)
- ALB DNS name (for DNS configuration)
- ECR repository URI (for GitHub Actions CI/CD)
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    aws_ecr as ecr,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
    aws_applicationautoscaling as appscaling,
)
from constructs import Construct
import json


class ComputeStack(Stack):
    """
    Compute infrastructure stack for Zero2Prod newsletter service.

    Deploys ECS Fargate with Application Load Balancer, auto-scaling,
    and supporting infrastructure.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        public_subnets: list,
        private_subnets: list,
        alb_sg: ec2.ISecurityGroup,
        ecs_sg: ec2.ISecurityGroup,
        database_secret: secretsmanager.ISecret,
        cache_secret: secretsmanager.ISecret,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # =====================================================================
        # Step 5: Import Dependencies from Previous Stacks
        # =====================================================================
        # VPC, subnets, and security groups passed as constructor parameters
        self.vpc = vpc
        self.public_subnets = public_subnets
        self.private_subnets = private_subnets
        self.alb_sg = alb_sg
        self.ecs_sg = ecs_sg
        self.database_secret = database_secret
        self.cache_secret = cache_secret

        # =====================================================================
        # Step 13: Create CloudWatch Log Group
        # =====================================================================
        self.log_group = logs.LogGroup(
            self,
            "LogGroup",
            log_group_name="/ecs/zero2prod-web",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY
        )

        # =====================================================================
        # Step 14: Create ECR Repository
        # =====================================================================
        self.ecr_repository = ecr.Repository(
            self,
            "Repository",
            repository_name="zero2prod",
            image_tag_mutability=ecr.TagMutability.IMMUTABLE,
            image_scan_on_push=True,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep last 10 images",
                    max_image_count=10
                )
            ],
            removal_policy=RemovalPolicy.DESTROY
        )

        # =====================================================================
        # Step 15: Create HMAC Secret
        # =====================================================================
        self.hmac_secret = secretsmanager.Secret(
            self,
            "HmacSecret",
            secret_name="zero2prod/hmac/secret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({}),
                generate_string_key="secret",
                exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/@\"\\"
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        # =====================================================================
        # Step 11: Create Task Execution IAM Role
        # =====================================================================
        self.task_execution_role = iam.Role(
            self,
            "TaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                )
            ],
            description="ECS task execution role for Zero2Prod web application"
        )

        # Grant Secrets Manager read access for task execution role
        self.database_secret.grant_read(self.task_execution_role)
        self.cache_secret.grant_read(self.task_execution_role)
        self.hmac_secret.grant_read(self.task_execution_role)

        # =====================================================================
        # Step 12: Create Task Runtime IAM Role
        # =====================================================================
        self.task_role = iam.Role(
            self,
            "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="ECS task runtime role for Zero2Prod web application"
        )

        # Grant X-Ray tracing permissions
        self.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords"
                ],
                resources=["*"]
            )
        )

        # =====================================================================
        # Step 10: Create ECS Cluster
        # =====================================================================
        self.cluster = ecs.Cluster(
            self,
            "Cluster",
            cluster_name="zero2prod-cluster",
            vpc=self.vpc,
            container_insights=True,
            enable_fargate_capacity_providers=True
        )

        # =====================================================================
        # Step 16: Create Fargate Task Definition
        # =====================================================================
        self.task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDefinition",
            family="zero2prod-web",
            cpu=1024,  # 1 vCPU
            memory_limit_mib=2048,  # 2 GB
            execution_role=self.task_execution_role,
            task_role=self.task_role
        )

        # =====================================================================
        # Step 17: Add Container to Task Definition
        # =====================================================================
        self.container = self.task_definition.add_container(
            "AppContainer",
            image=ecs.ContainerImage.from_ecr_repository(
                self.ecr_repository,
                tag="latest"
            ),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="zero2prod-web",
                log_group=self.log_group
            ),
            environment={
                "APP_ENVIRONMENT": "production",
                "APP_LOG_LEVEL": "info",
                "APP_APPLICATION__PORT": "8000",
                "APP_APPLICATION__HOST": "0.0.0.0",
                "AWS_XRAY_DAEMON_ADDRESS": "xray-daemon:2000",
                "AWS_XRAY_TRACING_NAME": "zero2prod-web",
                "AWS_REGION": self.region
            },
            secrets={
                "DATABASE_URL": ecs.Secret.from_secrets_manager(
                    self.database_secret,
                    field="connection_string"
                ),
                "REDIS_URI": ecs.Secret.from_secrets_manager(
                    self.cache_secret,
                    field="connection_string"
                ),
                "HMAC_SECRET": ecs.Secret.from_secrets_manager(
                    self.hmac_secret,
                    field="secret"
                )
            }
        )

        self.container.add_port_mappings(
            ecs.PortMapping(container_port=8000)
        )

        # =====================================================================
        # Step 7: Create Target Group
        # =====================================================================
        self.target_group = elbv2.ApplicationTargetGroup(
            self,
            "TargetGroup",
            vpc=self.vpc,
            port=8000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,  # Required for Fargate
            target_group_name="zero2prod-tg",
            health_check=elbv2.HealthCheck(
                path="/health_check",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=3,
                port="8000"
            ),
            deregistration_delay=Duration.seconds(300)  # Connection draining
        )

        # =====================================================================
        # Step 6: Create Application Load Balancer
        # =====================================================================
        self.alb = elbv2.ApplicationLoadBalancer(
            self,
            "ALB",
            vpc=self.vpc,
            internet_facing=True,
            load_balancer_name="zero2prod-alb",
            security_group=self.alb_sg,
            vpc_subnets=ec2.SubnetSelection(subnets=self.public_subnets)
        )

        # =====================================================================
        # Step 8: Create HTTP Listener (Redirect)
        # =====================================================================
        self.http_listener = self.alb.add_listener(
            "HttpListener",
            port=80,
            default_action=elbv2.ListenerAction.redirect(
                protocol="HTTPS",
                port="443",
                permanent=True  # 301 redirect
            )
        )

        # =====================================================================
        # Step 9: Create HTTPS Listener
        # =====================================================================
        # Note: Certificate ARN should be provided via CDK context
        # For now, we'll create the listener without a certificate
        # In production, add: certificates=[elbv2.ListenerCertificate.from_arn(cert_arn)]

        # Get certificate ARN from context (optional)
        certificate_arn = self.node.try_get_context("certificate_arn")

        if certificate_arn:
            self.https_listener = self.alb.add_listener(
                "HttpsListener",
                port=443,
                certificates=[elbv2.ListenerCertificate.from_arn(certificate_arn)],
                ssl_policy=elbv2.SslPolicy.TLS13_RES,  # TLS 1.3 + 1.2
                default_action=elbv2.ListenerAction.forward([self.target_group])
            )
        else:
            # If no certificate provided, create HTTPS listener that will need certificate later
            # This allows the stack to be deployed before certificate is ready
            CfnOutput(
                self,
                "CertificateNote",
                value="HTTPS listener requires ACM certificate ARN in CDK context",
                description="Add certificate_arn to cdk.context.json or pass via --context"
            )

        # =====================================================================
        # Step 18: Create Fargate Service
        # =====================================================================
        self.service = ecs.FargateService(
            self,
            "Service",
            cluster=self.cluster,
            task_definition=self.task_definition,
            service_name="zero2prod-web-service",
            desired_count=2,
            min_healthy_percent=100,
            max_healthy_percent=200,
            health_check_grace_period=Duration.seconds(60),
            vpc_subnets=ec2.SubnetSelection(subnets=self.private_subnets),
            security_groups=[self.ecs_sg]
        )

        # =====================================================================
        # Step 19: Attach Service to Target Group
        # =====================================================================
        self.service.attach_to_application_target_group(self.target_group)

        # =====================================================================
        # Step 20: Configure Auto-Scaling
        # =====================================================================
        self.scaling = self.service.auto_scale_task_count(
            min_capacity=2,
            max_capacity=10
        )

        self.scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.seconds(300),
            scale_out_cooldown=Duration.seconds(60)
        )

        # =====================================================================
        # Step 21: Create CloudFormation Outputs
        # =====================================================================
        CfnOutput(
            self,
            "AlbDnsName",
            value=self.alb.load_balancer_dns_name,
            description="ALB DNS name",
            export_name="Zero2Prod-ALB-DNS-Name"
        )

        CfnOutput(
            self,
            "ClusterName",
            value=self.cluster.cluster_name,
            description="ECS cluster name",
            export_name="Zero2Prod-ECS-Cluster-Name"
        )

        CfnOutput(
            self,
            "EcrRepositoryUri",
            value=self.ecr_repository.repository_uri,
            description="ECR repository URI",
            export_name="Zero2Prod-ECR-Repository-Uri"
        )

        CfnOutput(
            self,
            "EcrRepositoryName",
            value=self.ecr_repository.repository_name,
            description="ECR repository name"
        )

        CfnOutput(
            self,
            "ServiceName",
            value=self.service.service_name,
            description="ECS service name"
        )
