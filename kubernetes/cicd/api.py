from fastapi import FastAPI
from pydantic import BaseModel, Field
from create_code_pipeline import CodePipelineManager

app = FastAPI()

serviceRole = "arn:aws:iam::091063646508:role/codepipeline-role"
s3_bucket_name = "luffa-codepipeline-poc"
repo_prefix = "091063646508.dkr.ecr.us-west-2.amazonaws.com"
manager = CodePipelineManager(serviceRole=serviceRole,s3_bucket_name=s3_bucket_name,repo_prefix=repo_prefix)

# 配置常量
AWS_CLUSTERS = [
    {'region': 'us-west-2', 'cluster_name': 'eks-cluster', 'codebuild_project_name': '{namespace}-{app_name}-us-aws-test'},
    {'region': 'us-east-1', 'cluster_name': 'eks-cluster-us-aws', 'codebuild_project_name': '{namespace}-{app_name}-us-aws-prod'},
    {'region': 'eu-central-1', 'cluster_name': 'eks-cluster-eu-aws', 'codebuild_project_name': '{namespace}-{app_name}-eu-aws-prod'},
    {'region': 'ap-southeast-1', 'cluster_name': 'eks-cluster-sea-aws', 'codebuild_project_name': '{namespace}-{app_name}-sea-aws-prod'}
]

class PipelineConfig(BaseModel):
    app_name: str = Field(..., description="Application name")
    namespace: str = Field(..., description="Namespace for the application")
    port: str = Field(None, description="Port number for the application")
    version: str = Field(None, description="Version of the application")

@app.post("/create-pipeline")
def create_pipeline(config: PipelineConfig):
    app_name = config.app_name
    namespace = config.namespace
    port = config.port

    # 1. create codebuild project to build code to docker image and push it to ecr repo
    manager.build_step(app_name, namespace)

    # 2. create codebuild project to deploy application to EKS clusters
    for cluster in AWS_CLUSTERS:
        codebuild_project_name = cluster['codebuild_project_name'].format(namespace=namespace, app_name=app_name)
        manager.deploy_to_aws_step(app_name, namespace, port, cluster['region'], cluster['cluster_name'], codebuild_project_name)

    # 3. create codepipeline steps for applications
    manager.create_codepipeline(app_name, namespace)

    return {"message": "CodePipeline created successfully"}

@app.post("/start-pipeline")
def start_pipeline(config: PipelineConfig):
    app_name = config.app_name
    namespace = config.namespace
    version = config.version
    manager.start_pipeline_execution(app_name, namespace,version)

    return {"message": "CodePipeline execution started"}

@app.post("/create-event-rule")
def create_event_rule(config: PipelineConfig):
    app_name = config.app_name
    namespace = config.namespace

    # 5. create event rule to auto trigger codepipeline execution after code file upload to s3 bucket
    manager.create_eventbridge_rule(app_name, namespace)

    return {"message": "EventBridge rule created"}
