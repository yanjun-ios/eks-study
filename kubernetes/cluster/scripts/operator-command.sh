# kubectl manage mutiple clusters through alias
# 1. switch contexts
kubectl config get-contexts
kubectl config use-context
# 2. setuo alias
echo "alias kubeprd='kubectl --context=i-082f83ebf4c9e9fe0@eks-cluster-01.us-west-2.eksctl.io'" | tee -a ~/.bash_profile
echo "alias kubedev-older='kubectl --context=i-082f83ebf4c9e9fe0@eks-cluster.us-west-2.eksctl.io'" | tee -a ~/.bash_profile
