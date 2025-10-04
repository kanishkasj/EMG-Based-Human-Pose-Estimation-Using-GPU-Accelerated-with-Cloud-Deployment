#!/bin/bash
# Complete EMG Classifier Rebuild Script
# Save as: E:\HPC\codes\project\rebuild.sh

set -e  # Exit on any error

# Configuration
PROJECT_NAME="emg-classifier"
AWS_REGION="eu-north-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "=================================================="
echo "EMG CLASSIFIER COMPLETE REBUILD"
echo "=================================================="
echo "Project: ${PROJECT_NAME}"
echo "Region: ${AWS_REGION}"
echo "Account: ${AWS_ACCOUNT_ID}"
echo "=================================================="
echo ""

# Step 1: Clean up existing infrastructure
echo "Step 1: Destroying existing infrastructure..."
cd /mnt/e/HPC/codes/project/terraform
terraform destroy -auto-approve || true
echo "✓ Infrastructure destroyed"
echo ""

# Step 2: Create/update ECR repositories if they don't exist
echo "Step 2: Setting up ECR repositories..."
aws ecr describe-repositories --repository-names ${PROJECT_NAME}-api --region ${AWS_REGION} 2>/dev/null || \
    aws ecr create-repository --repository-name ${PROJECT_NAME}-api --region ${AWS_REGION}
echo "✓ ECR repositories ready"
echo ""

# Step 3: Rebuild Docker images
echo "Step 3: Building and pushing Docker images..."

# Login to ECR
echo "Logging into ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${ECR_REPO}

# Build and push API image
echo "Building API image..."
cd /mnt/e/HPC/codes/project/backend

# CRITICAL: Verify model file exists
if [ ! -f "models/emg_classifier.pkl" ]; then
    echo "ERROR: models/emg_classifier.pkl not found!"
    echo "Please ensure your trained model is in backend/models/"
    echo "Current directory contents:"
    ls -la models/ || echo "models/ directory not found!"
    exit 1
fi

echo "✓ Model file verified: $(ls -lh models/emg_classifier.pkl)"

docker build -t ${PROJECT_NAME}-api:latest .
docker tag ${PROJECT_NAME}-api:latest ${ECR_REPO}/${PROJECT_NAME}-api:latest
docker push ${ECR_REPO}/${PROJECT_NAME}-api:latest

API_IMAGE_URL="${ECR_REPO}/${PROJECT_NAME}-api:latest"
echo "✓ API image pushed: ${API_IMAGE_URL}"
echo ""

# Step 4: Deploy infrastructure
echo "Step 4: Deploying infrastructure with Terraform..."
cd /mnt/e/HPC/codes/project/terraform

# Initialize Terraform
echo "Initializing Terraform..."
terraform init

# Create terraform.tfvars with image URL
cat > terraform.tfvars <<EOF
project_name       = "${PROJECT_NAME}"
environment        = "dev"
aws_region         = "${AWS_REGION}"
api_image_url      = "${API_IMAGE_URL}"
frontend_image_url = "${API_IMAGE_URL}"
EOF

echo "✓ terraform.tfvars created"

# Apply infrastructure
echo "Applying Terraform configuration..."
terraform apply -auto-approve

echo "✓ Infrastructure deployed"
echo ""

# Step 5: Get outputs
echo "Step 5: Retrieving deployment information..."
ALB_DNS=$(terraform output -raw alb_dns_name)
API_URL="http://${ALB_DNS}"

echo "=================================================="
echo "DEPLOYMENT COMPLETE!"
echo "=================================================="
echo "ALB DNS: ${ALB_DNS}"
echo "API URL: ${API_URL}"
echo "Health Check: ${API_URL}/health"
echo "API Docs: ${API_URL}/docs"
echo "=================================================="
echo ""

# Step 6: Wait for service to be healthy
echo "Step 6: Waiting for service to become healthy..."
echo "This typically takes 2-3 minutes for:"
echo "  - Container to start"
echo "  - Health checks to pass"
echo "  - ALB to register target"
echo ""

sleep 90  # Initial wait for task to start

MAX_ATTEMPTS=20
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    echo "[Attempt $ATTEMPT/$MAX_ATTEMPTS] Testing health endpoint..."
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health" || echo "000")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✓ Service is healthy!"
        break
    else
        echo "  Response code: ${HTTP_CODE} (waiting for 200...)"
        if [ $ATTEMPT -lt $MAX_ATTEMPTS ]; then
            echo "  Waiting 15 seconds..."
            sleep 15
        fi
    fi
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo ""
    echo "=================================================="
    echo "WARNING: Service did not become healthy in time"
    echo "=================================================="
    echo "Troubleshooting steps:"
    echo ""
    echo "1. Check ECS task status:"
    echo "   aws ecs list-tasks --cluster ${PROJECT_NAME}-dev-cluster --region ${AWS_REGION}"
    echo ""
    echo "2. Check CloudWatch logs:"
    echo "   aws logs tail /ecs/${PROJECT_NAME}-api --follow --region ${AWS_REGION}"
    echo ""
    echo "3. Check target group health:"
    echo "   aws elbv2 describe-target-health --target-group-arn \$(terraform output -raw api_target_group_arn) --region ${AWS_REGION}"
    echo ""
    echo "4. Check security groups allow traffic:"
    echo "   - ALB security group: port 80 from 0.0.0.0/0"
    echo "   - ECS security group: port 8000 from ALB"
    echo "=================================================="
    exit 1
fi

# Step 7: Verify deployment
echo ""
echo "Step 7: Verifying all endpoints..."
echo ""

echo "Testing root endpoint (/):"
curl -s "${API_URL}/" | jq '.' || echo "Failed to parse JSON response"
echo ""

echo "Testing health endpoint (/health):"
curl -s "${API_URL}/health" | jq '.' || echo "Failed to parse JSON response"
echo ""

echo "Testing model info (/model-info):"
curl -s "${API_URL}/model-info" | jq '.' || echo "Failed to parse JSON response"
echo ""

echo "Testing API test endpoint (/test):"
curl -s "${API_URL}/test" | jq '.' || echo "Failed to parse JSON response"
echo ""

echo "=================================================="
echo "DEPLOYMENT VERIFIED SUCCESSFULLY!"
echo "=================================================="
echo ""
echo "Your EMG Classifier API is now live at:"
echo "  ${API_URL}"
echo ""
echo "Available endpoints:"
echo "  GET  /           - API status"
echo "  GET  /health     - Health check"
echo "  GET  /test       - Test endpoint"
echo "  GET  /model-info - Model details"
echo "  GET  /docs       - Interactive API docs"
echo "  POST /predict    - Make predictions"
echo ""
echo "Example prediction request:"
echo "  curl -X POST -F 'file=@your_data.csv' ${API_URL}/predict"
echo ""
echo "View real-time logs:"
echo "  aws logs tail /ecs/${PROJECT_NAME}-api --follow --region ${AWS_REGION}"
echo ""
echo "Update your frontend .env file:"
echo "  REACT_APP_API_URL=${API_URL}"
echo "=================================================="