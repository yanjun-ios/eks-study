#!/usr/bin/env bash

# 1. Create network flow mornitoring agent service account
# eksctl create iamserviceaccount \
#     --name aws-network-flow-monitoring-agent-sa \
#     --namespace kube-system \
#     --cluster $CLUSTER_NAME \
#     --attach-policy-arn arn:aws:iam::aws:policy/CloudWatchNetworkFlowMonitorAgentPublishPolicy \
#     --approve

role_name="aws-network-flow-monitoring-agent-role-$CLUSTER_NAME"
aws iam create-role --role-name $role_name --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "pods.eks.amazonaws.com"
                ]
            },
            "Action": [
                "sts:AssumeRole",
                "sts:TagSession"
            ]
        }
    ]
}' || true
aws iam attach-role-policy --role-name $role_name --policy-arn arn:aws:iam::aws:policy/CloudWatchNetworkFlowMonitorAgentPublishPolicy



# 2. Create network flow mornitoring agent add-on
role_arn=$(aws iam get-role --role-name $role_name --query 'Role.Arn' --output text)
aws eks create-addon --cluster-name $CLUSTER_NAME --addon-name aws-network-flow-monitoring-agent --pod-identity-associations serviceAccount=aws-network-flow-monitoring-agent-service-account,roleArn=$role_arn
# Delete network flow mornitoring agent add on
# eksctl delete addon --cluster $CLUSTER_NAME --name aws-network-flow-monitoring-agent --preserve
