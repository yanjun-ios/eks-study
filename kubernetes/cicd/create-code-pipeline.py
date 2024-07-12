import boto3
import os
import re
import yaml

# Application Information
app_name = "flask"
port = 8080
namespace = "tenant1"
repo_prefix = "091063646508.dkr.ecr.us-west-2.amazonaws.com"
s3_bucket_name = "luffa-codepipeline-poc"
chart_template_location = f"s3://{s3_bucket_name}/chart-templates/webapplication/"
chart_app_s3_location = f"s3://{s3_bucket_name}/{namespace}/{app_name}/chart/"
app_code_location = f"s3://{s3_bucket_name}/{namespace}/{app_name}/code/code.zip"
# Create CodePipeline client
session = boto3.Session(profile_name='default', region_name='us-west-2')
codepipeline = session.client('codepipeline')
codebuild = session.client('codebuild')
events_client = boto3.client('events')
serviceRole = "arn:aws:iam::091063646508:role/codepipeline-role"



# create codebuild project function
def create_codebuild_project(project_name, buildspec_file, variables,**kwargs):
    envs = [{'name': k,'value': str(v),'type': 'PLAINTEXT'} for k,v in variables.items()]
    with open(buildspec_file) as f:
        buildspec = f.read()
    return codebuild.create_project(
        name=project_name,
        source={
            'type': 'CODEPIPELINE',
            'buildspec': buildspec
        },
        artifacts={
            'type': 'CODEPIPELINE'
        },
        environment={
            'type': 'LINUX_CONTAINER',
            'computeType': 'BUILD_GENERAL1_SMALL',
            'image': 'aws/codebuild/amazonlinux2-x86_64-standard:3.0',
            'privilegedMode': True,
            'environmentVariables':envs
        },
        serviceRole=serviceRole,
        **kwargs
    )
# create codebuild project to build code to docker image,and push to ecr
def build_step():
    print(f"create build project {namespace}-{app_name}-build-project...")
    envs = {
        'repo_prefix':repo_prefix,
        'namespace':namespace,
        'app_name':app_name
    }
    codebuild_project_name = f'{namespace}-{app_name}-build-project'
    buildspec_file = os.path.join(os.getcwd(), 'buildspec/buildspec_build.yml')
    return create_codebuild_project(codebuild_project_name, buildspec_file,envs)

# create codebuild project to deploy application to EKS clusters 
def deploy_to_aws_step(region,cluster_name,codebuild_project_name):
    print(f"create deploy project {codebuild_project_name}...")
    envs = {
        'cluster_name': cluster_name,
        'app_name': app_name,
        'repo_prefix': repo_prefix,
        'port': port,
        'namespace': namespace,
        'chart_template_location': chart_template_location,
        'chart_app_s3_location': chart_app_s3_location,
        'region':region
    }
    buildspec_file = os.path.join(os.getcwd(), 'buildspec/buildspec_deploy.yml')
    return create_codebuild_project(codebuild_project_name, buildspec_file,envs)

# create codepipeline steps for appliactions
def create_codepipeline():
    print(f"create code pipeline {namespace}-{app_name}-pipeline...")
    variables = {
        'namespace': namespace,
        'app_name': app_name,
        'serviceRole': serviceRole,
        's3_bucket_name': s3_bucket_name
    }

    with open('codepipeline/pipeline.yaml') as f:
        yaml_content = f.read()

    for var, value in variables.items():
        yaml_content = re.sub('{'+var+'}', str(value), yaml_content)

    pipeline_config = yaml.safe_load(yaml_content)
    pipeline = pipeline_config['pipeline']
    response = codepipeline.create_pipeline(
        pipeline=pipeline
    )

# create event rule to auto trigger codepipeline execution after code file upload to s3 bucket
def create_eventbridge_rule():
    
    rule_name = f'{namespace}-{app_name}-s3-trigger'
    rule_response = events_client.put_rule(
        Name=rule_name,
        EventPattern=f'{{"source": ["aws.s3"], "detail-type": ["Object Created"], "detail": {{"bucket": {{"name": ["{s3_bucket_name}"]}}, "object": {{"key": ["{namespace}/{app_name}/code/code.zip"]}}}}}}'
    )

    pipeline_response = codepipeline.get_pipeline(
        name=f'{namespace}-{app_name}-pipeline'
    )
    pipeline_arn = pipeline_response['metadata']['pipelineArn']    

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

if __name__ == "__main__":

    #1. create codebuild project to build code to docker image,and push it to ecr repo
    build_step()

    #2. create codebuild project to deploy application to EKS clusters
    aws_clusters=[
        {'region':'us-west-2','cluster_name':'eks-cluster','codebuild_project_name':f'{namespace}-{app_name}-us-aws-test'},
        {'region':'us-east-1','cluster_name':'eks-cluster-us-aws','codebuild_project_name':f'{namespace}-{app_name}-us-aws-prod'},
        {'region':'eu-central-1','cluster_name':'eks-cluster-eu-aws','codebuild_project_name':f'{namespace}-{app_name}-eu-aws-prod'},
        {'region':'ap-southeast-1','cluster_name':'eks-cluster-sea-aws','codebuild_project_name':f'{namespace}-{app_name}-sea-aws-prod'}
    ]
    aliyun_cluster=[]
    
    tencent_cluster=[]

    for item in aws_clusters:
        deploy_to_aws_step(item['region'],item['cluster_name'],item['codebuild_project_name'])

    #3. create codepipeline steps for appliactions
    response=create_codepipeline()

    #4. execute the pipeline
    # response = codepipeline.start_pipeline_execution(
    #     name=f'{namespace}-{app_name}-pipeline',
    #     variables=[
    #         {
    #             'name': 'version',
    #             'value': 'v1.0.2'
    #         },
    #     ]
    # )

    # 5. create event rule to auto trigger codepipeline execution after code file upload to s3 bucket
    # create_eventbridge_rule()