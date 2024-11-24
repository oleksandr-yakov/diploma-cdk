from aws_cdk import (
    Stack,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_s3 as s3,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_ecs_patterns as ecs_patterns,
    aws_route53 as route53,
)
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from constructs import Construct
from config import connection_arn, branch, crt_aws_manager_arn_docker
from cdk.docker_ecr import PipelineStackDockerECR
import aws_cdk as cdk


class PipelineStackDocker(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ecr_stack_instance = PipelineStackDockerECR(self, "PipelineStackDockerECRInstance")  # from ecr docker pipieline
        repo_from_ecr = ecr_stack_instance.ecr_repo

        git_source_output = codepipeline.Artifact()
        source_action = codepipeline_actions.CodeStarConnectionsSourceAction(
            connection_arn=connection_arn,
            owner='fiesta-taco',
            repo='ovsrd-trainee-back-docker',
            branch=branch,
            action_name=f'GitHub_Source-ovsrd-trainee-back-docker-{branch}',
            output=git_source_output,
        )

        codebuild_role = iam.Role(self, f"CodeBuildRole-Front-{branch}",
                                  assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
                                  managed_policies=[
                                      iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                                      iam.ManagedPolicy.from_aws_managed_policy_name("AmazonECS_FullAccess"),
                                  ])

        source_bucket = s3.Bucket(self, "SourceBucketDocker",
                                  removal_policy=cdk.RemovalPolicy.DESTROY,  # delte s3 if stack had been deleted
                                  bucket_name=f"yakov-s3-docker-{branch}-qefh312u",
                                  # access_control=s3.BucketAccessControl("PUBLIC_READ"),
                                  cors=[
                                      s3.CorsRule(
                                          allowed_headers=["*"],
                                          allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT],
                                          allowed_origins=["*"],
                                          exposed_headers=[],
                                          max_age=3000,
                                      )]
                                  )

        ecs_cluster = ecs.Cluster(self, "MyECSCluster",
                                  cluster_name=f"yakov-docker-cluster-{branch}")

        ecs_cluster.add_capacity("DefaultAutoScalingGroupCapacity",
                                 instance_type=ec2.InstanceType("t2.micro"),
                                 desired_capacity=1,
                                 )

        task_role = iam.Role(
            self, "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
            ]
        )

        execution_role = iam.Role(
            self, "ExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
            ]
        )

        task_definition = ecs.Ec2TaskDefinition(self, "TaskDef",
                                                task_role=task_role,
                                                execution_role=execution_role,
                                                )

        container = task_definition.add_container("DefaultContainer",
                                                  image=ecs.ContainerImage.from_ecr_repository(repo_from_ecr, "latest"),
                                                  memory_limit_mib=250,
                                                  )

        container.add_port_mappings(ecs.PortMapping(container_port=3003))
        certificate = acm.Certificate.from_certificate_arn(self, "Certificate", crt_aws_manager_arn_docker)
        ecs_service = ecs_patterns.ApplicationLoadBalancedEc2Service(self, "Service",
                                                                     service_name=f"yakov-docker-service-{branch}",
                                                                     cluster=ecs_cluster,
                                                                     task_definition=task_definition,
                                                                     desired_count=1,
                                                                     public_load_balancer=True,
                                                                     listener_port=443,
                                                                     protocol=elbv2.ApplicationProtocol.HTTPS,
                                                                     certificate=certificate
                                                                     )
        hosted_zone = route53.HostedZone.from_lookup(self, "HostedZone",
                                                     domain_name="devoops.click",
                                                     )

        cname_record = route53.CnameRecord(self, "CnameRecord",
                                           zone=hosted_zone,
                                           record_name=f"api-{branch}.docker",
                                           domain_name=ecs_service.load_balancer.load_balancer_dns_name,
                                           )

        build_project = codebuild.PipelineProject(
            self,
            f"BuildProjectDocker-{branch}",
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "build": {
                        "commands": [
                            "echo $ECS_CLUSTER_NAME",
                            "echo $ECS_SERVICE_NAME",
                            "aws ecs update-service --cluster $ECS_CLUSTER_NAME --service $ECS_SERVICE_NAME --force-new-deployment",
                        ]
                    }
                },
            }),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.from_code_build_image_id("aws/codebuild/standard:7.0"),
                # privileged=True
            ),
            role=codebuild_role,
        )

        env_variables = {
            "ECS_CLUSTER_NAME": codebuild.BuildEnvironmentVariable(value=ecs_cluster.cluster_name),
            "ECS_SERVICE_NAME": codebuild.BuildEnvironmentVariable(value=f"yakov-docker-service-{branch}"),
        }

        build_action = codepipeline_actions.CodeBuildAction(
            action_name=f'CodeBuildDocker-{branch}',
            project=build_project,
            input=git_source_output,
            outputs=[codepipeline.Artifact(artifact_name='output')],
            environment_variables=env_variables,
        )

        pipeline_infra = codepipeline.Pipeline(self, f"DockerPipeline-{branch}", stages=[
                                        codepipeline.StageProps(
                                            stage_name=f'SourceGit-docker-{branch}',
                                            actions=[source_action]
                                        ),
                                        codepipeline.StageProps(
                                            stage_name=f'Build-docker-{branch}',
                                            actions=[build_action],
                                        )],
                                        pipeline_name=f"Pipeliene-Docker-infra-{branch}",
        )

        # For testing
        self.ecr_stack_instance = ecr_stack_instance
        self.source_bucket = source_bucket
        self.ecs_cluster = ecs_cluster
        self.task_role = task_role






