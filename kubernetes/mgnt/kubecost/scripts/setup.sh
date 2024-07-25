#!/usr/bin/env bash
# https://docs.kubecost.com/install-and-configure/install/provider-installations/aws-eks-cost-monitoring

VERSION=2.2.5

curl --location -o ../config/values-eks-cost-monitoring.yaml https://raw.githubusercontent.com/kubecost/cost-analyzer-helm-chart/v$VERSION/cost-analyzer/values-eks-cost-monitoring.yaml

helm upgrade -i kubecost oci://public.ecr.aws/kubecost/cost-analyzer --version $VERSION \
--namespace kubecost --create-namespace \
-f ../config/values-eks-cost-monitoring.yaml

# 3. Expose the service
kubectl apply -f ../config/kubecost-ingress.yaml