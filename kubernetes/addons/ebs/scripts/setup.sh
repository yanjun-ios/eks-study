#!/usr/bin/env bash

# 1. Create EBS service account
eksctl create iamserviceaccount \
    --name ebs-csi-controller-sa \
    --namespace kube-system \
    --cluster $CLUSTER_NAME \
    --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
    --approve
    # --role-name AmazonEKS_EBS_CSI_DriverRole \
    # --role-only \

# 2. Create EBS add-on
role_arn=$(kubectl describe sa ebs-csi-controller-sa -n kube-system | grep role-arn | awk  '{print $3}')
eksctl create addon --name aws-ebs-csi-driver --cluster $CLUSTER_NAME --service-account-role-arn $role_arn  --force

# Delete EBSCSI
# eksctl delete addon --cluster $CLUSTER_NAME --name aws-ebs-csi-driver --preserve

# 3. Create gp3 "Storage Class"
kubectl apply -f ../config/ebs-sc-gp3.yaml