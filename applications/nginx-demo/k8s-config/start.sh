#!/bin/bash

# Install metrics-server for HPA
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# install nginx deployment，service and hpa
kubectl apply -f nginx.yaml

# install ingress for nginx service
kubectl apply -f nginx-albingress.yaml
