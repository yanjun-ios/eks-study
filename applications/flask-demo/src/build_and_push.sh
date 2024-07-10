
# sudo yum install docker -y
# sudo systemctl start docker
# sudo groupadd docker
# sudo usermod -aG docker ${USER}
# sudo chmod 666 /var/run/docker.sock
# sudo systemctl restart docker


# Get the account number associated with the current IAM credentials
account=$(aws sts get-caller-identity --query Account --output text)

region=us-west-2
application_name=flask
version=v1.0
image_fullname=${account}.dkr.ecr.${region}.amazonaws.com/${application_name}:$version

if [ $? -ne 0 ]
then
    exit 255
fi

# If the repository doesn't exist in ECR, create it.
aws ecr describe-repositories --repository-names "${application_name}" --region ${region} || aws ecr create-repository --repository-name "${application_name}" --region ${region}

if [ $? -ne 0 ]
then
    aws ecr create-repository --repository-name "${application_name}" --region ${region}
fi

# Get the login command from ECR and execute it directly
aws ecr get-login-password --region $region | docker login --username AWS --password-stdin $account.dkr.ecr.$region.amazonaws.com

# Build the docker image locally with the image name and then push it to ECR
# with the full name.

DOCKER_BUILDKIT=0 docker build -t ${application_name} -f Dockerfile . 

docker tag ${application_name} ${image_fullname}

docker push ${image_fullname}

echo ${image_fullname}
