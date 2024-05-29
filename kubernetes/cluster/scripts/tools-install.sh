################################
## Install tools such as kubectl.
################################

# 1. Install kubectl - 1.29
#https://docs.aws.amazon.com/zh_cn/eks/latest/userguide/install-kubectl.html
echo "export KUBERNETES_VERSION=1.29" | tee -a ~/.bash_profile
echo "export CLUSTER_NAME=eks-cluster" | tee -a ~/.bash_profile
sudo curl https://s3.us-west-2.amazonaws.com/amazon-eks/1.29.3/2024-04-19/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl
sudo chmod +x /usr/local/bin/kubectl

# 2. Install awscli v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -fr ./aws && rm -f ./awscliv2.zip

# 3. jq, envsubst, bash-completion
sudo yum -y install jq gettext bash-completion moreutils

# 4. Install and verify yq
echo 'yq() {
  docker run --rm -i -v "${PWD}":/workdir mikefarah/yq "$@"
}' | tee -a ~/.bashrc && source ~/.bashrc

for command in kubectl jq envsubst aws
  do
    which $command &>/dev/null && echo "$command in path" || echo "$command NOT FOUND"
  done

# 5. kubectl bash_completion
kubectl completion bash >> ~/.bash_completion
. /etc/profile.d/bash_completion.sh
. ~/.bash_completion

# 6. shorthand alias
echo 'alias k=kubectl' >> ~/.bash_profile
echo 'complete -o default -F __start_kubectl k' >> ~/.bash_profile

# 7. AWS Load Balancer Controller version
echo 'export LBC_VERSION="v2.4.1"' >> ~/.bash_profile
echo 'export LBC_CHART_VERSION="1.4.1"' >> ~/.bash_profile
. ~/.bash_profile


# 8. Add ACCOUNT preference
export ACCOUNT_ID=$(aws sts get-caller-identity --output text --query Account)

export AWS_REGION=$(TOKEN=`curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"` \
&& curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/dynamic/instance-identity/document | jq -r '.region')
export AZS=($(aws ec2 describe-availability-zones --query 'AvailabilityZones[].ZoneName' --output text --region $AWS_REGION))

# 9. Check Preferences
test -n "$AWS_REGION" && echo AWS_REGION is "$AWS_REGION" || echo AWS_REGION is not set

# 10. Add settings to bash profile
echo "export ACCOUNT_ID=${ACCOUNT_ID}" | tee -a ~/.bash_profile
echo "export AWS_REGION=${AWS_REGION}" | tee -a ~/.bash_profile
echo "export AZS=(${AZS[@]})" | tee -a ~/.bash_profile
aws configure set default.region ${AWS_REGION}
aws configure get default.region

# 11. Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv -v /tmp/eksctl /usr/local/bin

# 12. Check the eksctl version
eksctl version

# 13. eksctl bash-completion
eksctl completion bash >> ~/.bash_completion
. /etc/profile.d/bash_completion.sh
. ~/.bash_completion

# 14. Install k9s
K9S_VERSION=v0.27.4
curl -sL https://github.com/derailed/k9s/releases/download/${K9S_VERSION}/k9s_Linux_amd64.tar.gz | sudo tar xfz - -C /usr/local/bin k9s

# 15. Install Helm
curl -sSL https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash
helm version --short
helm repo add stable https://charts.helm.sh/stable

# 16. helm bash-completion
helm completion bash >> ~/.bash_completion
. /etc/profile.d/bash_completion.sh
. ~/.bash_completion
source <(helm completion bash)
