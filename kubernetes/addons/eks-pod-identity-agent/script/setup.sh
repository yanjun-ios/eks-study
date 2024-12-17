#!/usr/bin/env bash

aws eks create-addon --cluster-name $CLUSTER_NAME --addon-name eks-pod-identity-agent
