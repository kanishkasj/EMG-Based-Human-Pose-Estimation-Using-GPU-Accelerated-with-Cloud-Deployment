#!/bin/bash
set -e  # Exit on any error

# Configuration
REGION="eu-north-1"
ACCOUNT_ID="418255731247"
PROJECT_ROOT="/mnt/e/HPC/codes/project"

echo "==================================="
echo "EMG Classifier AWS Deployment"
echo "==================================="
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo ""

# Step 1: Create ECR Repositories
echo "Step 1: Creating ECR repositories..."
aws ecr create-repository \
    --repository-name emg-api \
    --region $REGION \
    --image-scanning-configuration scanOnPush=true 2>/dev/null || echo "emg-api repo exists"

aws ecr create-repository \
    --repository-name emg-frontend \
    --region $REGION \
    --image-scanning-configuration scanOnPush=true 2>/dev/null || echo "emg-frontend repo exists"

echo "✓ ECR repositories ready"
echo ""

# Step 2: Login to ECR
echo "Step 2: Logging into ECR..."
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

if [ $? -ne 0 ]; then
    echo "✗ Failed to login to ECR"
    exit 1
fi
echo "✓ Logged into ECR"
echo ""

# Step 3: Build Docker images
echo "Step 3: Building Docker images..."
cd $PROJECT_ROOT

echo "Building API..."
docker build -t emg-api:latest ./backend

echo "Building Frontend..."
docker build -t emg-frontend:latest ./frontend

echo "✓ Images built"
echo ""

# Step 4: Tag images
echo "Step 4: Tagging images..."
docker tag emg-api:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/emg-api:latest
docker tag emg-frontend:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/emg-frontend:latest

echo "✓ Images tagged"
echo ""

# Step 5: Push to ECR
echo "Step 5: Pushing images to ECR..."
echo "Pushing API image..."
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/emg-api:latest

echo "Pushing Frontend image..."
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/emg-frontend:latest

echo "✓ Images pushed to ECR"
echo ""

# Step 6: Verify images
echo "Step 6: Verifying images in ECR..."
echo "API images:"
aws ecr list-images --repository-name emg-api --region $REGION

echo ""
echo "Frontend images:"
aws ecr list-images --repository-name emg-frontend --region $REGION

echo ""
echo "✓ Verification complete"
echo ""

# Step 7: Terraform deployment
echo "Step 7: Deploying with Terraform..."
cd $PROJECT_ROOT/terraform/environments/dev

echo "Initializing Terraform..."
terraform init

echo ""
echo "Validating Terraform configuration..."
terraform validate

echo ""
echo "Planning deployment..."
terraform plan -out=tfplan

echo ""
read -p "Apply this plan? (yes/no): " confirm
if [ "$confirm" = "yes" ]; then
    echo "Applying Terraform configuration..."
    terraform apply tfplan
    
    echo ""
    echo "==================================="
    echo "✓ Deployment Complete!"
    echo "==================================="
    echo ""
    echo "Getting deployment outputs..."
    terraform output
else
    echo "Deployment cancelled"
    exit 0
fi

echo ""
echo "To view logs:"
echo "  aws logs tail /ecs/emg-classifier-api --follow --region $REGION"
echo ""
echo "To check ECS service:"
echo "  aws ecs describe-services --cluster emg-classifier-dev-cluster --services emg-classifier-api-service --region $REGION"