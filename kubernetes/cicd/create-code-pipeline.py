import boto3
from datetime import datetime
# Application Information
app_name = "flask"
port = 8080
namespace = "tenant1"
repo_prefix = "091063646508.dkr.ecr.us-west-2.amazonaws.com"
cluster_name = "eks-cluster"
version = "v1.1.0"

# Create CodePipeline client
session = boto3.Session(profile_name='default', region_name='us-west-2')
codepipeline = session.client('codepipeline')
codebuild = session.client('codebuild')
events_client = boto3.client('events')

serviceRole = "arn:aws:iam::091063646508:role/codepipeline-role"
s3_bucket_name = "luffa-codepipeline-poc"
chart_template_location = f"s3://{s3_bucket_name}/chart-templates/webapplication/"

# Get current date and time
now = datetime.now()
date_time_str = now.strftime("%Y-%m-%d-%H-%M")
chart_app_s3_location = f"s3://{s3_bucket_name}/{namespace}/{app_name}/chart/"
app_code_location = f"s3://{s3_bucket_name}/{namespace}/{app_name}/code/code.zip"

# defined build step
def build_step():
    print("create build project...")
    codebuild_project_name = f'{namespace}-{app_name}-build-project'
    rs = codebuild.create_project(
        name = codebuild_project_name,
        source = {
            'type': 'CODEPIPELINE',
            'buildspec': f"""
version: 0.2
phases:
    install:
        commands:
        - echo "Installing dependencies..."
    pre_build:
        commands:
        - echo "Running pre-build commands..."
    build:
        commands:
        - echo "Running build commands..."
        - aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin {repo_prefix}
        - docker build -t {repo_prefix}/{app_name}:$version .
        - docker push {repo_prefix}/{app_name}:$version
    post_build:
        commands:
        - echo "Running post-build commands..."
        """
        },
        artifacts = {
            'type': 'CODEPIPELINE'
        },
        environment = {
            'type': 'LINUX_CONTAINER',
            'computeType': 'BUILD_GENERAL1_SMALL',
            'image': 'aws/codebuild/amazonlinux2-x86_64-standard:3.0',
            'privilegedMode': True
        },
        serviceRole = serviceRole
        #buildspec = ''
    )
    return rs

# defined deployment step
def deploy_step():
    print("create deploy project...")
    codebuild_project_name = f'{namespace}-{app_name}-deploy-project'
    rs = codebuild.create_project(
        name = codebuild_project_name,
        source = {
            'type': 'CODEPIPELINE',
            'buildspec': f"""
version: 0.2
phases:
    install:
        commands:
        - echo "Installing helm"
        - curl -sSL https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash
        - helm repo add stable https://charts.helm.sh/stable
        - curl https://s3.us-west-2.amazonaws.com/amazon-eks/1.29.3/2024-04-19/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl
        - chmod +x /usr/local/bin/kubectl
    pre_build:
        commands:
        - echo "Update kubeconfig..."
        - aws eks update-kubeconfig --name {cluster_name}
        - echo "add helm template..."
        - mkdir web-application && aws s3 sync {chart_template_location} ./web-application/
        - echo "replace the template veriables..."
        - sed -i -e "s/@app-name@/{app_name}/g" -e "s/@image-url@/{repo_prefix}\/{app_name}:$version/g" -e "s/@port@/{port}/g" -e "s/@namespace@/{namespace}/g" ./web-application/values.yaml
        - echo "upload chart file to s3 ..."
        - aws s3 sync ./web-application/ {chart_app_s3_location}
    build:
        commands:
        - echo "Running deploy commands..."
        - helm upgrade --install --force {app_name} web-application 
    post_build:
        commands:
        - echo "Running post-build commands..."
        """
        },
        artifacts = {
            'type': 'CODEPIPELINE'
        },
        environment = {
            'type': 'LINUX_CONTAINER',
            'computeType': 'BUILD_GENERAL1_SMALL',
            'image': 'aws/codebuild/amazonlinux2-x86_64-standard:3.0',
            'privilegedMode': True
        },
        serviceRole = serviceRole
    )
    return rs

# defined codepipeline step
def create_codepipeline():
    print("create pipeline ...")
    # Define the pipeline structure
    pipeline = {
        'pipeline': {
            'name': f'{namespace}-{app_name}-pipeline',
            'roleArn': serviceRole,
            'artifactStore': {
                'type': 'S3',
                'location': s3_bucket_name
            },
            'pipelineType': 'V2',
            'variables': [
                {
                    'name': 'version',
                    'defaultValue': 'v1.0.0',
                    'description': 'application version'
                },
            ],
            'stages': [
                {
                    'name': 'source',
                    'actions': [
                        {
                            'name': 'SourceAction',
                            'actionTypeId': {
                                'category': 'Source',
                                'owner': 'AWS',
                                'version': '1',
                                'provider': 'S3'
                            },
                            'outputArtifacts': [
                                {
                                    'name': 'SourceOutput'
                                }
                            ],
                            'configuration': {
                                'S3Bucket': s3_bucket_name,
                                'S3ObjectKey': f'{namespace}/{app_name}/code/code.zip',
                                'PollForSourceChanges': 'false'
                            },
                            'runOrder': 1
                        }
                    ]
                },
                {
                    'name': 'build',
                    'actions': [
                        {
                            'name': 'BuildAction',
                            'actionTypeId': {
                                'category': 'Build',
                                'owner': 'AWS',
                                'version': '1',
                                'provider': 'CodeBuild'
                            },
                            'inputArtifacts': [
                                {
                                    'name': 'SourceOutput'
                                }
                            ],
                            'outputArtifacts': [
                                {
                                    'name': 'BuildOutput'
                                }
                            ],
                            'configuration': {
                                "EnvironmentVariables": "[{\"name\":\"version\",\"value\":\"#{variables.version}\",\"type\":\"PLAINTEXT\"}]",
                                'ProjectName': f'{namespace}-{app_name}-build-project'
                            },
                            'runOrder': 1
                        }
                    ]
                },
                {
                    'name': 'deploy-to-test',
                    'actions': [
                        {
                            'name': 'BuildAction',
                            'actionTypeId': {
                                'category': 'Build',
                                'owner': 'AWS',
                                'version': '1',
                                'provider': 'CodeBuild'
                            },
                            'inputArtifacts': [
                                {
                                    'name': 'SourceOutput'
                                }
                            ],
                            'outputArtifacts': [
                                {
                                    'name': 'DeployTestOutput'
                                }
                            ],
                            'configuration': {
                                "EnvironmentVariables": "[{\"name\":\"version\",\"value\":\"#{variables.version}\",\"type\":\"PLAINTEXT\"}]",
                                'ProjectName': f'{namespace}-{app_name}-deploy-project'
                            },
                            'runOrder': 1
                        }
                    ]
                }
            ]
        }
    }

    response = codepipeline.create_pipeline(
        pipeline=pipeline['pipeline']
    )
    return response

def create_eventbridge_rule():
    
    # 创建EventBridge规则
    rule_name = f'{namespace}-{app_name}-s3-trigger'
    rule_response = events_client.put_rule(
        Name=rule_name,
        EventPattern=f'{{"source": ["aws.s3"], "detail-type": ["Object Created"], "detail": {{"bucket": {{"name": ["{s3_bucket_name}"]}}, "object": {{"key": ["{namespace}/{app_name}/code/code.zip"]}}}}}}'
    )

    # 获取CodePipeline ARN
    pipeline_response = codepipeline.get_pipeline(
        name=f'{namespace}-{app_name}-pipeline'
    )
    pipeline_arn = pipeline_response['metadata']['pipelineArn']
    
    # 创建EventBridge目标
    target_response = events_client.put_targets(
        Rule=rule_name,
        Targets=[
            {
                'Arn': pipeline_arn,
                'RoleArn': serviceRole,
                'Id': 'CodePipelineTarget'
            }
        ]
    )
    
    print(f'EventBridge规则 {rule_name} 已创建,并将在指定的S3对象被上传时触发CodePipeline')

#1. 创建build
# build_step()
#2. 创建deploy
# deploy_step()
#3. 创建pipeline
# response=create_codepipeline()

#4.执行pipeline
response = codepipeline.start_pipeline_execution(
    name=f'{namespace}-{app_name}-pipeline',
    variables=[
        {
            'name': 'version',
            'value': 'v1.0.2'
        },
    ]
)
# 5.创建Event Rule规则，自动执行Pipeline
# create_eventbridge_rule()