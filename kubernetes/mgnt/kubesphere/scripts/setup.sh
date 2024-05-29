#!/bin/bash

# kubernetes version v3.4.1
# https://kubesphere.io/docs/v3.4/installing-on-kubernetes/hosted-kubernetes/install-kubesphere-on-eks/

# 1. Install KubeSphere using kubectl. The following commands are only for the default minimal installation
curl --location -o ../config/kubesphere-installer.yaml https://github.com/kubesphere/ks-installer/releases/download/v3.4.1/kubesphere-installer.yaml
curl --location -o ../config/cluster-configuration.yaml https://github.com/kubesphere/ks-installer/releases/download/v3.4.1/cluster-configuration.yaml

kubectl apply -f ../config/kubesphere-installer.yaml
kubectl apply -f ../config/cluster-configuration.yaml

# Inspect the logs of installation:
kubectl logs -n kubesphere-system $(kubectl get pod -n kubesphere-system -l 'app in (ks-install, ks-installer)' -o jsonpath='{.items[0].metadata.name}') -f

# Expost the service 
kubectl apply -f ../config/kubesphere-ingress.yaml

