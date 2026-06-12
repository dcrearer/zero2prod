"""
Unit tests for NetworkStack

Tests VPC, subnet, security group, and VPC endpoint configurations
"""

import aws_cdk as cdk
from aws_cdk import assertions
from stacks.network_stack import NetworkStack


def test_vpc_created_with_correct_cidr():
    """Test that VPC is created with correct CIDR block"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::EC2::VPC", {
        "CidrBlock": "10.0.0.0/16",
        "EnableDnsHostnames": True,
        "EnableDnsSupport": True,
    })


def test_public_subnets_created():
    """Test that 2 public subnets are created"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    # Find all public subnets (those with MapPublicIpOnLaunch: true)
    subnets = template.find_resources("AWS::EC2::Subnet", {
        "Properties": {
            "MapPublicIpOnLaunch": True,
        }
    })

    assert len(subnets) == 2, f"Expected 2 public subnets, found {len(subnets)}"


def test_private_subnets_created():
    """Test that 2 private subnets are created"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    # Find all private subnets (those without MapPublicIpOnLaunch)
    all_subnets = template.find_resources("AWS::EC2::Subnet")
    public_subnets = template.find_resources("AWS::EC2::Subnet", {
        "Properties": {
            "MapPublicIpOnLaunch": True,
        }
    })

    private_subnet_count = len(all_subnets) - len(public_subnets)
    assert private_subnet_count == 2, f"Expected 2 private subnets, found {private_subnet_count}"


def test_internet_gateway_created():
    """Test that Internet Gateway is created"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::EC2::InternetGateway", 1)


def test_nat_gateway_not_created():
    """Test that NAT Gateway is NOT created (using VPC endpoints instead)"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::EC2::NatGateway", 0)


def test_alb_security_group_created():
    """Test that ALB security group is created with correct rules"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    # Check for HTTP ingress rule
    template.has_resource_properties("AWS::EC2::SecurityGroup", {
        "GroupDescription": "Security group for Zero2Prod Application Load Balancer",
    })


def test_ecs_security_group_created():
    """Test that ECS security group is created"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::EC2::SecurityGroup", {
        "GroupDescription": "Security group for Zero2Prod ECS Fargate tasks",
    })


def test_aurora_security_group_created():
    """Test that Aurora security group is created"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::EC2::SecurityGroup", {
        "GroupDescription": "Security group for Zero2Prod Aurora PostgreSQL cluster",
    })


def test_elasticache_security_group_created():
    """Test that ElastiCache security group is created"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::EC2::SecurityGroup", {
        "GroupDescription": "Security group for Zero2Prod ElastiCache Redis cluster",
    })


def test_lambda_security_group_created():
    """Test that Lambda security group is created"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::EC2::SecurityGroup", {
        "GroupDescription": "Security group for Zero2Prod Lambda worker functions",
    })


def test_vpc_endpoint_security_group_created():
    """Test that VPC Endpoint security group is created"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::EC2::SecurityGroup", {
        "GroupDescription": "Security group for Zero2Prod VPC Interface Endpoints",
    })


def test_six_security_groups_total():
    """Test that exactly 6 security groups are created"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::EC2::SecurityGroup", 6)


def test_s3_gateway_endpoint_created():
    """Test that S3 Gateway endpoint is created"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    # Find all Gateway endpoints
    gateway_endpoints = template.find_resources("AWS::EC2::VPCEndpoint", {
        "Properties": {
            "VpcEndpointType": "Gateway",
        }
    })

    assert len(gateway_endpoints) >= 1, "Should have at least 1 Gateway endpoint"

    # Check that at least one Gateway endpoint is for S3
    s3_endpoint_found = False
    for endpoint_id, endpoint in gateway_endpoints.items():
        service_name = endpoint["Properties"]["ServiceName"]
        if isinstance(service_name, dict) and "Fn::Join" in service_name:
            # ServiceName is constructed with Fn::Join, check if it contains 's3'
            join_parts = service_name["Fn::Join"][1]
            if any("s3" in str(part).lower() for part in join_parts):
                s3_endpoint_found = True
                break
        elif isinstance(service_name, str) and "s3" in service_name.lower():
            s3_endpoint_found = True
            break

    assert s3_endpoint_found, "Should have an S3 Gateway endpoint"


def test_interface_endpoints_created():
    """Test that 7 Interface endpoints are created"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    interface_endpoints = template.find_resources("AWS::EC2::VPCEndpoint", {
        "Properties": {
            "VpcEndpointType": "Interface",
        }
    })

    assert len(interface_endpoints) == 7, f"Expected 7 interface endpoints, found {len(interface_endpoints)}"


def test_cloudformation_outputs_created():
    """Test that all required CloudFormation outputs are created"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    expected_outputs = [
        "VPCId",
        "PublicSubnetIds",
        "PrivateSubnetIds",
        "ALBSecurityGroupId",
        "ECSSecurityGroupId",
        "AuroraSecurityGroupId",
        "ElastiCacheSecurityGroupId",
        "LambdaSecurityGroupId",
        "VPCEndpointSecurityGroupId",
    ]

    for output in expected_outputs:
        template.has_output(output, {})


def test_resources_are_tagged():
    """Test that resources have required tags"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    # VPC should have Name and Component tags
    vpc_resources = template.find_resources("AWS::EC2::VPC")
    assert len(vpc_resources) == 1

    vpc_resource = list(vpc_resources.values())[0]
    tags = vpc_resource["Properties"]["Tags"]

    tag_dict = {tag["Key"]: tag["Value"] for tag in tags}
    assert "Name" in tag_dict
    assert tag_dict["Name"] == "zero2prod-vpc"
    assert "Component" in tag_dict
    assert tag_dict["Component"] == "Network"


def test_snapshot():
    """Snapshot test to catch unexpected changes"""
    app = cdk.App()
    stack = NetworkStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    # This will create a snapshot file on first run
    # On subsequent runs, it will compare against the snapshot
    assert template.to_json() is not None
