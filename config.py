import os

connection_arn = "arn:aws:codeconnections:eu-central-1:905418051827:connection/b69b24d2-7b3a-4174-bd86-8d3d780a75c7"
account_id = '905418051827'
region = 'eu-central-1' #main
#region = 'us-east-1' #dev
branch = os.environ.get('DEV_ENV')
crt_aws_manager_arn_docker = "arn:aws:acm:eu-central-1:905418051827:certificate/861235e7-b01b-4651-95de-536c43f67937"
crt_aws_manager_arn_front = "arn:aws:acm:us-east-1:905418051827:certificate/b8687cc9-546c-4417-92db-a6f0e32d07ee"


