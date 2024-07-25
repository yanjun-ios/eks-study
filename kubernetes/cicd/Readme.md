# 1. 控制台创建 code pipeline role
## 1.1 创建信任策略文件
echo '{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "codepipeline.amazonaws.com",
                    "codebuild.amazonaws.com",
                    "events.amazonaws.com"
                ]
            },
            "Action": "sts:AssumeRole"
        }
    ]
}' > trust-policy.json

## 1.2 创建 IAM 角色
aws iam create-role \
    --role-name codepipeline-role \
    --assume-role-policy-document file://trust-policy.json

## 1.3 附加 AdministratorAccess 权限策略
aws iam attach-role-policy \
    --role-name codepipeline-role \
    --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

ROLE_ARN=$(aws iam get-role --role-name codepipeline-role --query 'Role.Arn' --output text)

# 2. 添加 eks 权限
eksctl create iamidentitymapping --cluster eks-cluster --arn $ROLE_ARN --group system:masters --username admin

# 3. 创建和 codepipeline 同 region 的 S3 存储桶，更新脚本
s3_bucket_name="luffa-codepipeline-poc"
aws s3 mb s3://${s3_bucket_name} --region us-west-2

# 4. 上传 chart 模板到 S3 上, S3 需要开启版本控制

chart_template_location = "s3://${s3_bucket_name}/chart/webapplication/"
cd /home/ec2-user/infra/eks-study/kubernetes/cicd/templates
aws s3 sync ./web-application/ s3://${s3_bucket_name}/chart-templates/webapplication/

# 5. 上传代码压缩包到 S3 目标位置
cd /home/ec2-user/infra/eks-study/applications/flask-demo/src
zip -r code.zip .
aws s3 cp code.zip s3://${s3_bucket_name}/tenant1/flask/code/code.zip

# 6. 执行脚本，创建 pipeline
kubectl create namespace tenant1
python3 create_code_pipeline.py

## 6.1 运行 api 服务（可选）
#pip install uvicorn fastapi boto3
uvicorn api:app -h 0.0.0.0 --host 0.0.0.0 --reload


#start pipeline
curl -XPOST -H "Content-Type: application/json" http://172.31.26.111:8000/start-pipeline -d'{"namespace":"tenant1","app_name":"flask","version":"v1.1.1"}'


#create pipeline 
curl -XPOST -H "Content-Type: application/json" http://172.31.26.111:8000/create-pipeline -d'{"namespace":"tenant1","app_name":"flask","port":"8080","version":"v1.1.1"}'


#create event 
curl -XPOST -H "Content-Type: application/json" http://172.31.26.111:8000/create-event-rule -d'{"namespace":"tenant1","app_name":"flask"}'

# 7. 删除 pipeline 资源
kubectl create namespace tenant1
## 7.1 删除 pipeline
aws codepipeline list-pipelines --query 'pipelines[?contains(name, `tenant1`)].name' --output text | xargs -I {} aws codepipeline delete-pipeline --name {}
## 7.2 删除 codebuild project
aws codebuild delete-project --name tenant1-flask-sea-aws-prod
aws codebuild delete-project --name tenant1-flask-eu-aws-prod
aws codebuild delete-project --name tenant1-flask-us-aws-prod
aws codebuild delete-project --name tenant1-flask-us-aws-test
aws codebuild delete-project --name tenant1-flask-build-project
## 7.3 删除 event rule
RULE_NAME='tenant1-flask-s3-trigger'
aws events remove-targets --rule $RULE_NAME --ids $(aws events list-targets-by-rule --rule $RULE_NAME --query 'Targets[*].Id' --output text)
aws events delete-rule --name $RULE_NAME