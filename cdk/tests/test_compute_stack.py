"""
Unit tests for ComputeStack (Unit 4: Compute Infrastructure)

Tests verify:
- Application Load Balancer configuration
- ECS Cluster, Service, and Task Definition
- Auto-scaling policies
- IAM roles and policies
- CloudWatch Logs
- ECR repository
- CloudFormation outputs
"""

import aws_cdk as cdk
from aws_cdk.assertions import Template, Match
import pytest
from stacks.network_stack import NetworkStack
from stacks.database_stack import DatabaseStack
from stacks.cache_stack import CacheStack
from stacks.compute_stack import ComputeStack


@pytest.fixture
def compute_template():
    """Create a CDK app with all stacks and return ComputeStack template"""
    app = cdk.App()

    # Create prerequisite stacks
    network_stack = NetworkStack(app, "TestNetworkStack")
    database_stack = DatabaseStack(
        app,
        "TestDatabaseStack",
        vpc=network_stack.vpc,
        private_subnets=network_stack.vpc.isolated_subnets,
        aurora_sg=network_stack.aurora_sg
    )
    cache_stack = CacheStack(
        app,
        "TestCacheStack",
        vpc=network_stack.vpc,
        private_subnets=network_stack.vpc.isolated_subnets,
        elasticache_sg=network_stack.elasticache_sg,
        alarm_topic=database_stack.alarm_topic
    )

    # Create ComputeStack
    compute_stack = ComputeStack(
        app,
        "TestComputeStack",
        vpc=network_stack.vpc,
        public_subnets=network_stack.vpc.public_subnets,
        private_subnets=network_stack.vpc.isolated_subnets,
        alb_sg=network_stack.alb_sg,
        ecs_sg=network_stack.ecs_sg,
        database_secret=database_stack.database_secret,
        cache_secret=cache_stack.cache_secret
    )

    return Template.from_stack(compute_stack)


class TestApplicationLoadBalancer:
    """Test ALB configuration"""

    def test_alb_created(self, compute_template):
        """Test ALB is created with correct properties"""
        compute_template.resource_count_is(
            "AWS::ElasticLoadBalancingV2::LoadBalancer", 1
        )

        compute_template.has_resource_properties(
            "AWS::ElasticLoadBalancingV2::LoadBalancer",
            {
                "Name": "zero2prod-alb",
                "Scheme": "internet-facing",
                "Type": "application"
            }
        )

    def test_http_listener_redirects(self, compute_template):
        """Test HTTP listener redirects to HTTPS"""
        compute_template.has_resource_properties(
            "AWS::ElasticLoadBalancingV2::Listener",
            {
                "Port": 80,
                "Protocol": "HTTP",
                "DefaultActions": [
                    {
                        "Type": "redirect",
                        "RedirectConfig": {
                            "Protocol": "HTTPS",
                            "Port": "443",
                            "StatusCode": "HTTP_301"
                        }
                    }
                ]
            }
        )

    def test_target_group_created(self, compute_template):
        """Test target group is created with correct health check"""
        compute_template.has_resource_properties(
            "AWS::ElasticLoadBalancingV2::TargetGroup",
            {
                "Name": "zero2prod-tg",
                "Port": 8000,
                "Protocol": "HTTP",
                "TargetType": "ip",
                "HealthCheckPath": "/health_check",
                "HealthCheckIntervalSeconds": 30,
                "HealthCheckTimeoutSeconds": 5,
                "HealthyThresholdCount": 2,
                "UnhealthyThresholdCount": 3,
                "DeregistrationDelay": 300
            }
        )


class TestECSCluster:
    """Test ECS Cluster configuration"""

    def test_cluster_created(self, compute_template):
        """Test ECS cluster is created"""
        compute_template.resource_count_is("AWS::ECS::Cluster", 1)

        compute_template.has_resource_properties(
            "AWS::ECS::Cluster",
            {
                "ClusterName": "zero2prod-cluster",
                "ClusterSettings": [
                    {
                        "Name": "containerInsights",
                        "Value": "enabled"
                    }
                ]
            }
        )


class TestTaskDefinition:
    """Test ECS Task Definition configuration"""

    def test_task_definition_created(self, compute_template):
        """Test task definition is created with correct resources"""
        compute_template.has_resource_properties(
            "AWS::ECS::TaskDefinition",
            {
                "Family": "zero2prod-web",
                "Cpu": "1024",  # 1 vCPU
                "Memory": "2048",  # 2 GB
                "NetworkMode": "awsvpc",
                "RequiresCompatibilities": ["FARGATE"]
            }
        )

    def test_container_definition(self, compute_template):
        """Test container is configured correctly"""
        compute_template.has_resource_properties(
            "AWS::ECS::TaskDefinition",
            {
                "ContainerDefinitions": Match.array_with([
                    Match.object_like({
                        "Name": "AppContainer",
                        "PortMappings": [
                            {
                                "ContainerPort": 8000,
                                "Protocol": "tcp"
                            }
                        ],
                        "Environment": Match.array_with([
                            {"Name": "APP_ENVIRONMENT", "Value": "production"},
                            {"Name": "APP_LOG_LEVEL", "Value": "info"},
                            {"Name": "APP_APPLICATION__PORT", "Value": "8000"},
                            {"Name": "APP_APPLICATION__HOST", "Value": "0.0.0.0"}
                        ]),
                        "Secrets": Match.array_with([
                            Match.object_like({"Name": "DATABASE_URL"}),
                            Match.object_like({"Name": "REDIS_URI"}),
                            Match.object_like({"Name": "HMAC_SECRET"})
                        ])
                    })
                ])
            }
        )


class TestIAMRoles:
    """Test IAM roles configuration"""

    def test_task_execution_role_created(self, compute_template):
        """Test task execution role has correct policies"""
        compute_template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "AssumeRolePolicyDocument": Match.object_like({
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Principal": {"Service": "ecs-tasks.amazonaws.com"}
                        })
                    ])
                }),
                "ManagedPolicyArns": Match.array_with([
                    Match.string_like_regexp(
                        ".*AmazonECSTaskExecutionRolePolicy"
                    )
                ])
            }
        )

    def test_task_role_created(self, compute_template):
        """Test task runtime role has X-Ray permissions"""
        # Find the task role (has X-Ray policy)
        compute_template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Action": [
                                "xray:PutTraceSegments",
                                "xray:PutTelemetryRecords"
                            ],
                            "Effect": "Allow",
                            "Resource": "*"
                        })
                    ])
                }
            }
        )


class TestECSService:
    """Test ECS Service configuration"""

    def test_service_created(self, compute_template):
        """Test ECS service is created with correct properties"""
        compute_template.has_resource_properties(
            "AWS::ECS::Service",
            {
                "ServiceName": "zero2prod-web-service",
                "DesiredCount": 2,
                "DeploymentConfiguration": {
                    "MinimumHealthyPercent": 100,
                    "MaximumPercent": 200
                },
                "HealthCheckGracePeriodSeconds": 60,
                "LaunchType": "FARGATE"
            }
        )


class TestAutoScaling:
    """Test auto-scaling configuration"""

    def test_scalable_target_created(self, compute_template):
        """Test scalable target is created with min/max capacity"""
        compute_template.has_resource_properties(
            "AWS::ApplicationAutoScaling::ScalableTarget",
            {
                "MinCapacity": 2,
                "MaxCapacity": 10,
                "ServiceNamespace": "ecs",
                "ScalableDimension": "ecs:service:DesiredCount"
            }
        )

    def test_scaling_policy_created(self, compute_template):
        """Test CPU-based scaling policy is created"""
        compute_template.has_resource_properties(
            "AWS::ApplicationAutoScaling::ScalingPolicy",
            {
                "PolicyType": "TargetTrackingScaling",
                "TargetTrackingScalingPolicyConfiguration": {
                    "TargetValue": 70.0,
                    "ScaleInCooldown": 300,
                    "ScaleOutCooldown": 60,
                    "PredefinedMetricSpecification": {
                        "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
                    }
                }
            }
        )


class TestECRRepository:
    """Test ECR repository configuration"""

    def test_repository_created(self, compute_template):
        """Test ECR repository is created with correct properties"""
        compute_template.has_resource_properties(
            "AWS::ECR::Repository",
            {
                "RepositoryName": "zero2prod",
                "ImageTagMutability": "IMMUTABLE",
                "ImageScanningConfiguration": {
                    "ScanOnPush": True
                }
            }
        )


class TestCloudWatchLogs:
    """Test CloudWatch Logs configuration"""

    def test_log_group_created(self, compute_template):
        """Test log group is created with correct retention"""
        compute_template.has_resource_properties(
            "AWS::Logs::LogGroup",
            {
                "LogGroupName": "/ecs/zero2prod-web",
                "RetentionInDays": 30
            }
        )


class TestSecretsManager:
    """Test Secrets Manager configuration"""

    def test_hmac_secret_created(self, compute_template):
        """Test HMAC secret is created"""
        compute_template.has_resource_properties(
            "AWS::SecretsManager::Secret",
            {
                "Name": "zero2prod/hmac/secret",
                "GenerateSecretString": Match.object_like({
                    "GenerateStringKey": "secret"
                })
            }
        )


class TestCloudFormationOutputs:
    """Test CloudFormation outputs"""

    def test_required_outputs_exist(self, compute_template):
        """Test required outputs are exported"""
        # ALB DNS name export
        compute_template.has_output(
            "AlbDnsName",
            {"Export": {"Name": "Zero2Prod-ALB-DNS-Name"}}
        )

        # ECS cluster name export
        compute_template.has_output(
            "ClusterName",
            {"Export": {"Name": "Zero2Prod-ECS-Cluster-Name"}}
        )

        # ECR repository URI export
        compute_template.has_output(
            "EcrRepositoryUri",
            {"Export": {"Name": "Zero2Prod-ECR-Repository-Uri"}}
        )
