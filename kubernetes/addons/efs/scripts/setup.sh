#!/usr/bin/env bash

# 1. Create EFS Service Account

eksctl create iamserviceaccount \
    --cluster $CLUSTER_NAME \
    --namespace kube-system \
    --name efs-csi-controller-sa \
    --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy \
    --approve 
    # --role-name AmazonEKS_EFS_CSI_DriverRole_$CLUSTER_NAME \
    # --role-only \

role_arn=$(kubectl describe sa efs-csi-controller-sa -n kube-system | grep role-arn | awk  '{print $3}')
eksctl create addon --name aws-efs-csi-driver --cluster $CLUSTER_NAME --service-account-role-arn $role_arn  --force
