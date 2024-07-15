import boto3
import os
import re
import yaml
import json

class CodePipelineManager:
    def __init__(self,serviceRole,s3_bucket_name, repo_prefix,profile_name='default', region_name='us-west-2'):
        self.session = boto3.Session(profile_name=profile_name, region_name=region_name)
        self.codepipeline_client = self.session.client('codepipeline')
        self.codebuild_client = self.session.client('codebuild')
        self.events_client = boto3.client('events')
        self.serviceRole = serviceRole
        self.s3_bucket_name = s3_bucket_name
        self.repo_prefix = repo_prefix

    # create codebuild project function
    def create_codebuild_project(self,project_name, buildspec_file, variables,**kwargs):
        envs = [{'name': k,'value': str(v),'type': 'PLAINTEXT'} for k,v in variables.items()]
        with open(buildspec_file) as f:
            buildspec = f.read()
        return self.codebuild_client.create_project(
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
            serviceRole=self.serviceRole,
            **kwargs
        )
    # create codebuild project to build code to docker image,and push to ecr
    def build_step(self, app_name, namespace):
        print(f"create build project {namespace}-{app_name}-build-project...")
        envs = {
            'repo_prefix':self.repo_prefix,
            'namespace':namespace,
            'app_name':app_name
        }
        codebuild_project_name = f'{namespace}-{app_name}-build-project'
        buildspec_file = os.path.join(os.getcwd(), 'buildspec/buildspec_build.yml')
        return self.create_codebuild_project(codebuild_project_name, buildspec_file,envs)

    # create codebuild project to deploy application to EKS clusters 
    def deploy_to_aws_step(self,app_name, namespace, port,region,cluster_name,codebuild_project_name):
        print(f"create deploy project {codebuild_project_name}...")
        chart_template_location = f"s3://{self.s3_bucket_name}/chart-templates/webapplication/"
        chart_app_s3_location = f"s3://{self.s3_bucket_name}/{namespace}/{app_name}/chart/"
        app_code_location = f"s3://{self.s3_bucket_name}/{namespace}/{app_name}/code/code.zip"
        envs = {
            'cluster_name': cluster_name,
            'app_name': app_name,
            'repo_prefix': self.repo_prefix,
            'port': port,
            'namespace': namespace,
            'chart_template_location': chart_template_location,
            'chart_app_s3_location': chart_app_s3_location,
            'region':region
        }
        buildspec_file = os.path.join(os.getcwd(), 'buildspec/buildspec_deploy.yml')
        return self.create_codebuild_project(codebuild_project_name, buildspec_file,envs)

    # create codepipeline steps for appliactions
    def create_codepipeline(self,app_name,namespace):
        print(f"create code pipeline {namespace}-{app_name}-pipeline...")
        variables = {
            'namespace': namespace,
            'app_name': app_name,
            'serviceRole': self.serviceRole,
            's3_bucket_name': self.s3_bucket_name
        }

        with open('codepipeline/pipeline.yaml') as f:
            yaml_content = f.read()

        for var, value in variables.items():
            yaml_content = re.sub('{'+var+'}', str(value), yaml_content)

        pipeline_config = yaml.safe_load(yaml_content)
        pipeline = pipeline_config['pipeline']
        response = self.codepipeline_client.create_pipeline(
            pipeline=pipeline
        )

    # execute the codepipeline
    def start_pipeline_execution(self, app_name, namespace,version):
        response = self.codepipeline_client.start_pipeline_execution(
            name=f'{namespace}-{app_name}-pipeline',
            variables=[
                {
                    'name': 'version',
                    'value': version
                },
            ]
        )
    

    # create event rule to auto trigger codepipeline execution after code file upload to s3 bucket
    def create_eventbridge_rule(self, app_name, namespace):
        
        rule_name = f'{namespace}-{app_name}-s3-trigger'
        event_pattern = {
            "source": ["aws.s3"],
            "detail-type": ["AWS API Call via CloudTrail"],
            "detail": {
                "eventSource": ["s3.amazonaws.com"],
                "eventName": ["PutObject", "CompleteMultipartUpload", "CopyObject"],
                "requestParameters": {
                    "bucketName": [self.s3_bucket_name],
                    "key": [f"{namespace}/{app_name}/code/code.zip"]
                }
            }
        }
        rule_response = self.events_client.put_rule(
            Name=rule_name,
            EventPattern=json.dumps(event_pattern)
        )
        pipeline_response = self.codepipeline_client.get_pipeline(
            name=f'{namespace}-{app_name}-pipeline'
        )
        pipeline_arn = pipeline_response['metadata']['pipelineArn']    

        target_response = self.events_client.put_targets(
            Rule=rule_name,
            Targets=[
                {
                    'Arn': pipeline_arn,
                    'RoleArn': self.serviceRole,
                    'Id': 'CodePipelineTarget'
                }
            ]
        )
        
        print(f'EventBridge规则 {rule_name} 已创建,并将在指定的S3对象被上传时触发CodePipeline')

if __name__ == "__main__":

    #0. Application information
    app_name = "flask"
    port = 8080
    namespace = "tenant1"

    #1. Init CodePipelineManager
    serviceRole = "arn:aws:iam::091063646508:role/codepipeline-role"
    s3_bucket_name = "luffa-codepipeline-poc"
    repo_prefix = "091063646508.dkr.ecr.us-west-2.amazonaws.com"
    manager = CodePipelineManager(serviceRole=serviceRole,s3_bucket_name=s3_bucket_name,repo_prefix=repo_prefix)

    #2. create codebuild project to build code to docker image,and push it to ecr repo
    manager.build_step(app_name,namespace)

    #3. create codebuild project to deploy application to EKS clusters
    aws_clusters=[
        {'region':'us-west-2','cluster_name':'eks-cluster','codebuild_project_name':f'{namespace}-{app_name}-us-aws-test'},
        {'region':'us-east-1','cluster_name':'eks-cluster-us-aws','codebuild_project_name':f'{namespace}-{app_name}-us-aws-prod'},
        {'region':'eu-central-1','cluster_name':'eks-cluster-eu-aws','codebuild_project_name':f'{namespace}-{app_name}-eu-aws-prod'},
        {'region':'ap-southeast-1','cluster_name':'eks-cluster-sea-aws','codebuild_project_name':f'{namespace}-{app_name}-sea-aws-prod'}
    ]
    aliyun_cluster=[]
    
    tencent_cluster=[]

    for item in aws_clusters:
        manager.deploy_to_aws_step(app_name, namespace, port,item['region'],item['cluster_name'],item['codebuild_project_name'])

    #4. create codepipeline steps for appliactions
    manager.create_codepipeline(app_name, namespace)

    #5. create event rule to auto trigger codepipeline execution after code file upload to s3 bucket
    manager.create_eventbridge_rule(app_name, namespace)

    #6. execute the pipeline
    response = manager.start_pipeline_execution(app_name, namespace,"v1.0.0")


