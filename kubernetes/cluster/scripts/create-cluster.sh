#!/bin/bash

# 1. Create EKS Cluster
sed -i "s/{CLUSTER_NAME}/${CLUSTER_NAME}/g" ../config/eks-cluster.yaml
sed -i "s/{KUBERNETES_VERSION}/\'${KUBERNETES_VERSION}\'/g" ../config/eks-cluster.yaml
sed -i "s/{AWS_REGION}/${AWS_REGION}/g" ../config/eks-cluster.yaml

eksctl create cluster -f ../config/eks-cluster.yaml

# 2. Add OIDC
oidc_id=$(aws eks describe-cluster --name $CLUSTER_NAME --query "cluster.identity.oidc.issuer" --output text | cut -d '/' -f 5)
eksctl utils associate-iam-oidc-provider --cluster $CLUSTER_NAME --approve

# 3. Install LoadBancer Controller
# https://docs.aws.amazon.com/zh_cn/eks/latest/userguide/lbc-helm.html
curl --location -o ../config/iam-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/refs/heads/main/docs/install/iam_policy.json

aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy-${CLUSTER_NAME} \
    --policy-document file://../config/iam-policy.json \
    || true

eksctl create iamserviceaccount \
  --cluster=${CLUSTER_NAME} \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::${ACCOUNT_ID}:policy/AWSLoadBalancerControllerIAMPolicy-${CLUSTER_NAME} \
  --override-existing-serviceaccounts \
  --region ${AWS_REGION} \
  --approve

helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=${CLUSTER_NAME} \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

kubectl get deployment -n kube-system aws-load-balancer-controller

# 4.Install metrics-server for HPA
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
