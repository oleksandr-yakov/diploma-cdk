from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_iam as iam,
    aws_route53 as route53,
    aws_certificatemanager as acm

)
import aws_cdk as cdk
from constructs import Construct
from config import connection_arn, branch, crt_aws_manager_arn_front


class PipelineStackFront(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        codebuild_role = iam.Role(self, f"CodeBuildRole-Front-{branch}",
                                  assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
                                  managed_policies=[
                                     iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                                     iam.ManagedPolicy.from_aws_managed_policy_name("CloudFrontFullAccess")
                                                    ]
                                  )

        source_bucket = s3.Bucket(self, "SourceBucket",
                                  removal_policy=cdk.RemovalPolicy.DESTROY,                       # delte s3 if stack had been deleted
                                  bucket_name=f"yakov-s3-front-{branch}-qesjdfh",
                                  #public_read_access=True,
                                  #access_control=s3.BucketAccessControl.PUBLIC_READ,
                                  )
        hosted_zone = route53.HostedZone.from_lookup(self, "HostedZone",
                                                     domain_name="devoops.click",
                                                     )
        certificate = acm.Certificate.from_certificate_arn(
            self, "MySSLCertificate",
            certificate_arn=crt_aws_manager_arn_front
        )

        distribution = cloudfront.CloudFrontWebDistribution(self, f"MyDistributionFront-{branch}",
                                                            origin_configs=[cloudfront.SourceConfiguration(
                                                                s3_origin_source=cloudfront.S3OriginConfig(
                                                                    s3_bucket_source=source_bucket),
                                                                behaviors=[
                                                                    cloudfront.Behavior(is_default_behavior=True,#use this configuration by deffault
                                                                                        compress=True,
                                                                                        allowed_methods=cloudfront.CloudFrontAllowedMethods.GET_HEAD,
                                                                                        )],
                                                            )],
                                                            viewer_certificate=cloudfront.ViewerCertificate.from_acm_certificate(
                                                                certificate=certificate,
                                                                aliases=[f"diploma.web.devoops.click"],
                                                                security_policy=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
                                                            ),

        )
        cname_record = route53.CnameRecord(self, "CnameRecord",
                                           zone=hosted_zone,
                                           record_name=f"diploma.web.devoops.click",
                                           domain_name=distribution.distribution_domain_name,
                                           )

        git_source_output = codepipeline.Artifact()
        source_action = codepipeline_actions.CodeStarConnectionsSourceAction(
            connection_arn=connection_arn,
            owner='fiesta-taco',
            repo='ovsrd-trainee-front',
            branch=branch,   # use global env var : DEV_ENV=dev && cdk deploy <name stack> --profile oyakovenko-trainee
            action_name=f'GitHub_Source_ovsrd-trainee-front-{branch}',
            output=git_source_output,
            trigger_on_push=True,
        )

        env_variables = {
            "DEV_ENV": codebuild.BuildEnvironmentVariable(value=f"{branch}"),
            "S3_NAME": codebuild.BuildEnvironmentVariable(value=source_bucket.bucket_name),
            "CL_FRONT_DIST_ID": codebuild.BuildEnvironmentVariable(value=distribution.distribution_id),
        }

        build_action = codepipeline_actions.CodeBuildAction(
            action_name=f'CodeBuildFront-{branch}',
            project=codebuild.PipelineProject(self, f"BuildProjectFront-{branch}",
                                              build_spec=codebuild.BuildSpec.from_source_filename("buildspec.yml"),
                                              role=codebuild_role,
                                              environment=codebuild.BuildEnvironment(
                                                  build_image=codebuild.LinuxBuildImage.from_code_build_image_id(
                                                      "aws/codebuild/standard:7.0"),
                                              ),),

                                                                      #codepipline роль не нужна
                                                                      #он ничего не делает
                                                                      #а запуск codebuild есть по дефолту
                                                                      #кажется раньше надо было - сейчас если роль не указать
                                                                      # то она какая то будет дефолтная
                                                                      #а вот codebuild делает работу
                                                                      #ему нужен full access к s3 и cloudfront
            environment_variables=env_variables,
            input=git_source_output,
            outputs=[codepipeline.Artifact(artifact_name='output')],
        )

        pipeline = codepipeline.Pipeline(self, f"FrontPipeline-{branch}",
                                        stages=[
                                            codepipeline.StageProps(
                                                stage_name=f'SourceGit-front-{branch}',
                                                actions=[source_action]
                                            ),
                                            codepipeline.StageProps(
                                                stage_name=f'Build-front-{branch}',
                                                actions=[build_action]
                                            ),
                                        ])
