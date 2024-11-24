import aws_cdk as cdk
from config import account_id, region, branch
from cdk.front_stack import PipelineStackFront
from cdk.serverless_stack import PipelineStackServerless
from cdk.docker_ecr import PipelineStackDockerECR
from cdk.docker_stack import PipelineStackDocker


app = cdk.App()
StackFront = PipelineStackFront(app, "PipelineStackFront",
                                env=cdk.Environment(account=account_id, region=region),
                                stack_name=f'front-stack-{branch}'
                                )

StackServerless = PipelineStackServerless(app, "PipelineStackServerless",
                                env=cdk.Environment(account=account_id, region=region),
                                stack_name=f'serverless-stack-{branch}'
                                )

docker_ecr_stack = PipelineStackDockerECR(app, "PipelineStackDockerECR",
                               env=cdk.Environment(account=account_id, region=region),
                               stack_name=f'docker-ERC-stack-{branch}')

docker_stack = PipelineStackDocker(app, "PipelineStackDocker",
                    env=cdk.Environment(account=account_id, region=region),
                    stack_name=f'docker-stack-{branch}')


app.synth()
