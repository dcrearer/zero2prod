"""
Integration tests for NetworkStack deployment

These tests verify that the deployed network infrastructure is functional.
They require:
- Deployed NetworkStack in AWS
- AWS credentials configured
- boto3 installed

Run with: pytest tests/integration/ -v
"""

import boto3
import pytest
from botocore.exceptions import ClientError


@pytest.fixture(scope="module")
def ec2_client():
    """Create EC2 client for testing"""
    return boto3.client('ec2', region_name='us-east-1')


@pytest.fixture(scope="module")
def cloudformation_client():
    """Create CloudFormation client for testing"""
    return boto3.client('cloudformation', region_name='us-east-1')


@pytest.fixture(scope="module")
def stack_outputs(cloudformation_client):
    """Get CloudFormation stack outputs"""
    try:
        response = cloudformation_client.describe_stacks(
            StackName='Zero2ProdNetworkStack'
        )
        outputs = {}
        for output in response['Stacks'][0]['Outputs']:
            outputs[output['OutputKey']] = output['OutputValue']
        return outputs
    except ClientError as e:
        pytest.skip(f"Stack not deployed: {e}")


def test_vpc_exists(ec2_client, stack_outputs):
    """Test that VPC exists and is available"""
    vpc_id = stack_outputs['VPCId']

    response = ec2_client.describe_vpcs(VpcIds=[vpc_id])
    assert len(response['Vpcs']) == 1

    vpc = response['Vpcs'][0]
    assert vpc['State'] == 'available'
    assert vpc['CidrBlock'] == '10.0.0.0/16'
    assert vpc['EnableDnsHostnames'] is True
    assert vpc['EnableDnsSupport'] is True


def test_public_subnets_exist(ec2_client, stack_outputs):
    """Test that public subnets exist and are in different AZs"""
    subnet_ids = stack_outputs['PublicSubnetIds'].split(',')
    assert len(subnet_ids) == 2

    response = ec2_client.describe_subnets(SubnetIds=subnet_ids)
    assert len(response['Subnets']) == 2

    azs = [subnet['AvailabilityZone'] for subnet in response['Subnets']]
    assert len(set(azs)) == 2, "Subnets should be in different AZs"

    for subnet in response['Subnets']:
        assert subnet['State'] == 'available'
        assert subnet['MapPublicIpOnLaunch'] is True


def test_private_subnets_exist(ec2_client, stack_outputs):
    """Test that private subnets exist and are in different AZs"""
    subnet_ids = stack_outputs['PrivateSubnetIds'].split(',')
    assert len(subnet_ids) == 2

    response = ec2_client.describe_subnets(SubnetIds=subnet_ids)
    assert len(response['Subnets']) == 2

    azs = [subnet['AvailabilityZone'] for subnet in response['Subnets']]
    assert len(set(azs)) == 2, "Subnets should be in different AZs"

    for subnet in response['Subnets']:
        assert subnet['State'] == 'available'
        assert subnet['MapPublicIpOnLaunch'] is False


def test_security_groups_exist(ec2_client, stack_outputs):
    """Test that all security groups exist"""
    sg_keys = [
        'ALBSecurityGroupId',
        'ECSSecurityGroupId',
        'AuroraSecurityGroupId',
        'ElastiCacheSecurityGroupId',
        'LambdaSecurityGroupId',
        'VPCEndpointSecurityGroupId',
    ]

    for sg_key in sg_keys:
        sg_id = stack_outputs[sg_key]
        response = ec2_client.describe_security_groups(GroupIds=[sg_id])
        assert len(response['SecurityGroups']) == 1
        assert response['SecurityGroups'][0]['GroupId'] == sg_id


def test_alb_security_group_rules(ec2_client, stack_outputs):
    """Test that ALB security group has correct ingress rules"""
    sg_id = stack_outputs['ALBSecurityGroupId']
    response = ec2_client.describe_security_groups(GroupIds=[sg_id])
    sg = response['SecurityGroups'][0]

    ingress_rules = sg['IpPermissions']
    assert len(ingress_rules) >= 2, "ALB should have at least 2 ingress rules (HTTP and HTTPS)"

    ports = [rule['FromPort'] for rule in ingress_rules if 'FromPort' in rule]
    assert 80 in ports, "ALB should allow HTTP (port 80)"
    assert 443 in ports, "ALB should allow HTTPS (port 443)"


def test_ecs_security_group_rules(ec2_client, stack_outputs):
    """Test that ECS security group has correct ingress from ALB"""
    ecs_sg_id = stack_outputs['ECSSecurityGroupId']
    alb_sg_id = stack_outputs['ALBSecurityGroupId']

    response = ec2_client.describe_security_groups(GroupIds=[ecs_sg_id])
    sg = response['SecurityGroups'][0]

    ingress_rules = sg['IpPermissions']
    assert len(ingress_rules) >= 1, "ECS should have at least 1 ingress rule from ALB"

    # Check that ALB security group is allowed
    alb_rule_found = False
    for rule in ingress_rules:
        if 'UserIdGroupPairs' in rule:
            for pair in rule['UserIdGroupPairs']:
                if pair['GroupId'] == alb_sg_id and rule.get('FromPort') == 8000:
                    alb_rule_found = True
                    break

    assert alb_rule_found, "ECS should allow port 8000 from ALB security group"


def test_vpc_endpoints_exist(ec2_client, stack_outputs):
    """Test that VPC endpoints exist and are available"""
    vpc_id = stack_outputs['VPCId']

    response = ec2_client.describe_vpc_endpoints(
        Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
    )

    endpoints = response['VpcEndpoints']
    assert len(endpoints) == 8, "Should have 8 VPC endpoints (1 Gateway + 7 Interface)"

    gateway_endpoints = [e for e in endpoints if e['VpcEndpointType'] == 'Gateway']
    interface_endpoints = [e for e in endpoints if e['VpcEndpointType'] == 'Interface']

    assert len(gateway_endpoints) == 1, "Should have 1 Gateway endpoint (S3)"
    assert len(interface_endpoints) == 7, "Should have 7 Interface endpoints"

    for endpoint in endpoints:
        assert endpoint['State'] == 'available', f"Endpoint {endpoint['VpcEndpointId']} is not available"


def test_s3_gateway_endpoint_functional(ec2_client, stack_outputs):
    """Test that S3 Gateway endpoint is functional"""
    vpc_id = stack_outputs['VPCId']

    response = ec2_client.describe_vpc_endpoints(
        Filters=[
            {'Name': 'vpc-id', 'Values': [vpc_id]},
            {'Name': 'vpc-endpoint-type', 'Values': ['Gateway']},
        ]
    )

    assert len(response['VpcEndpoints']) == 1
    endpoint = response['VpcEndpoints'][0]

    assert 's3' in endpoint['ServiceName'].lower()
    assert endpoint['State'] == 'available'


def test_interface_endpoints_have_private_dns(ec2_client, stack_outputs):
    """Test that Interface endpoints have private DNS enabled"""
    vpc_id = stack_outputs['VPCId']

    response = ec2_client.describe_vpc_endpoints(
        Filters=[
            {'Name': 'vpc-id', 'Values': [vpc_id]},
            {'Name': 'vpc-endpoint-type', 'Values': ['Interface']},
        ]
    )

    for endpoint in response['VpcEndpoints']:
        assert endpoint['PrivateDnsEnabled'] is True, \
            f"Endpoint {endpoint['VpcEndpointId']} should have private DNS enabled"


def test_stack_tags(cloudformation_client):
    """Test that stack has required tags"""
    try:
        response = cloudformation_client.describe_stacks(
            StackName='Zero2ProdNetworkStack'
        )
        stack = response['Stacks'][0]
        tags = {tag['Key']: tag['Value'] for tag in stack.get('Tags', [])}

        assert 'Environment' in tags
        assert 'Project' in tags
        assert tags['Project'] == 'Zero2Prod'

    except ClientError as e:
        pytest.skip(f"Stack not deployed: {e}")
