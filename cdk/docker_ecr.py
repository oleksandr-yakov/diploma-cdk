from aws_cdk import (
    Stack,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_ecr as ecr,
    aws_iam as iam,
)
from constructs import Construct
from config import connection_arn, branch, region, account_id

ecr_name = f"yakov-docker-repo-{branch}"


class PipelineStackDockerECR(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

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
                                      iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryFullAccess"),
                                      iam.ManagedPolicy.from_aws_managed_policy_name("AWSBatchFullAccess")
                                  ])

        self.ecr_repo = ecr.Repository(self, "MyECRRepository",
                                  repository_name=ecr_name)

        build_project = codebuild.PipelineProject(
            self,
            f"BuildProjectDocker-{branch}",
            build_spec=codebuild.BuildSpec.from_source_filename("buildspec.yml"),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.from_code_build_image_id("aws/codebuild/standard:7.0"),
                privileged=True
            ),
            role=codebuild_role,
        )

        env_variables = {
            "DEV_ENV": codebuild.BuildEnvironmentVariable(value=branch),
            "AWS_REGION": codebuild.BuildEnvironmentVariable(value=region),
            "REPO": codebuild.BuildEnvironmentVariable(value=self.ecr_repo.repository_name),
            "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=account_id),
        }

        build_action = codepipeline_actions.CodeBuildAction(
            action_name=f'CodeBuildDocker-{branch}',
            project=build_project,
            input=git_source_output,
            outputs=[codepipeline.Artifact(artifact_name='output')],
            environment_variables=env_variables,
        )

        pipeline_ecr = codepipeline.Pipeline(self, f"DockerPipeline-{branch}", stages=[
                                        codepipeline.StageProps(
                                            stage_name=f'SourceGit-docker-{branch}',
                                            actions=[source_action]
                                        ),
                                        codepipeline.StageProps(
                                            stage_name=f'Build-docker-{branch}',
                                            actions=[build_action],

                                        )],
                                        pipeline_name=f"Pipeliene-Docker-ECR-{branch}",
                                        )
