from aws_cdk import (
    Stack,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
    aws_ssm as ssm,
)
import aws_cdk as cdk
from constructs import Construct
from config import connection_arn, branch


class PipelineStackServerless(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        codebuild_role = iam.Role(self, f"CodeBuildRole-Front-{branch}",
                                  assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
                                  managed_policies=[
                                      iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMFullAccess"),
                                      iam.ManagedPolicy.from_aws_managed_policy_name("AWSCloudFormationFullAccess"),
                                      iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                                      iam.ManagedPolicy.from_aws_managed_policy_name("AWSLambda_FullAccess"),
                                      iam.ManagedPolicy.from_aws_managed_policy_name("AmazonAPIGatewayAdministrator"),
                                      iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess"),
                                  ])

        git_source_output = codepipeline.Artifact()
        source_action = codepipeline_actions.CodeStarConnectionsSourceAction(
            connection_arn=connection_arn,
            owner='fiesta-taco',
            repo='ovsrd-trainee-back-serverless',
            branch=branch,
            action_name=f'GitHub_Source_ovsrd-trainee-back-serverless-{branch}',
            output=git_source_output,
        )
        env_variables = {
            "STAGE": codebuild.BuildEnvironmentVariable(value=f"{branch}"),
        }
        build_action = codepipeline_actions.CodeBuildAction(
            action_name=f'CodeBuildServerless-{branch}',
            project=codebuild.PipelineProject(self, f"BuildProjectServerless-{branch}",
                                              build_spec=codebuild.BuildSpec.from_source_filename("buildspec.yml"),
                                              role=codebuild_role,
                                              environment=codebuild.BuildEnvironment(
                                                  build_image=codebuild.LinuxBuildImage.from_code_build_image_id(
                                                      "aws/codebuild/standard:7.0"),
                                              ),
                                              ),
            input=git_source_output,
            environment_variables=env_variables,
            outputs=[codepipeline.Artifact(artifact_name='output')]
        )

        list_table = dynamodb.Table(
            self, f"ListTable-{branch}",
            table_name=f"ListTable-{branch}",
            partition_key=dynamodb.Attribute(
                name="listId",
                type=dynamodb.AttributeType.STRING
            ),
            read_capacity=1,
            write_capacity=1,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        card_table = dynamodb.Table(
            self, f"CardTable-{branch}",
            table_name=f"CardTable-{branch}",
            partition_key=dynamodb.Attribute(
                name="cardId",
                type=dynamodb.AttributeType.STRING
            ),
            read_capacity=1,
            write_capacity=1,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        card_table.add_global_secondary_index(
            index_name="ListIdIndex",
            partition_key=dynamodb.Attribute(
                name="listId",
                type=dynamodb.AttributeType.STRING
            ),
            read_capacity=1,
            write_capacity=1,
            projection_type=dynamodb.ProjectionType.ALL
        )

        ssm.StringParameter(
            self, "ListTableNameParameter",
            parameter_name=f"/{branch}/list-table-name",
            string_value=list_table.table_name,
        )

        ssm.StringParameter(
            self, "CardTableNameParameter",
            parameter_name=f"/{branch}/card-table-name",
            string_value=card_table.table_name,
        )

        pipeline = codepipeline.Pipeline(self, f"ServerlessPipeline-{branch}", stages=[
            codepipeline.StageProps(
                stage_name=f'SourceGit-serverless-{branch}',
                actions=[source_action]
            ),
            codepipeline.StageProps(
                stage_name=f'Build-serverless-{branch}',
                actions=[build_action]
            ),
        ])

        self.list_table = list_table
        self.card_table = card_table
