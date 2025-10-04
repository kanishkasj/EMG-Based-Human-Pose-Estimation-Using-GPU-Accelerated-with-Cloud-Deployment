#!/bin/bash
set -e

echo "=========================================="
echo "EMG Pose Classifier - AWS Deployment"
echo "=========================================="

# Configuration
REGION="eu-north-1"
CLUSTER="emg-classifier-dev-cluster"
SERVICE="emg-classifier-api-service"
IMAGE_NAME="kanishkasj/emg-api:latest"

# Change to backend directory
cd /mnt/e/HPC/codes/project/backend

echo ""
echo "Step 1: Verifying files..."
echo "----------------------------------------"

# Check critical files
if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found!"
    exit 1
fi
echo "✓ main.py found"

if [ ! -f "models/emg_classifier.pkl" ]; then
    echo "ERROR: models/emg_classifier.pkl not found!"
    echo "Looking for models in: $(pwd)/models/"
    ls -la models/ 2>/dev/null || echo "models/ directory doesn't exist!"
    exit 1
fi
echo "✓ models/emg_classifier.pkl found"

if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found!"
    exit 1
fi
echo "✓ requirements.txt found"

if [ ! -f "Dockerfile" ]; then
    echo "ERROR: Dockerfile not found!"
    exit 1
fi
echo "✓ Dockerfile found"

echo ""
echo "Step 2: Building Docker image..."
echo "----------------------------------------"
docker build -t $IMAGE_NAME . || {
    echo "ERROR: Docker build failed!"
    exit 1
}
echo "✓ Docker build successful"

echo ""
echo "Step 3: Testing image locally (quick check)..."
echo "----------------------------------------"
# Quick test that model file is in the image
docker run --rm $IMAGE_NAME ls -la /app/models/ || {
    echo "ERROR: Model directory not accessible in image!"
    exit 1
}

docker run --rm $IMAGE_NAME test -f /app/models/emg_classifier.pkl && \
    echo "✓ Model file verified in image" || {
    echo "ERROR: Model file not in image!"
    exit 1
}

echo ""
echo "Step 4: Pushing to DockerHub..."
echo "----------------------------------------"
# Check if logged in to Docker
docker info > /dev/null 2>&1 || {
    echo "ERROR: Docker not running or not logged in"
    echo "Run: docker login"
    exit 1
}

docker push $IMAGE_NAME || {
    echo "ERROR: Docker push failed!"
    echo "Make sure you're logged in: docker login"
    exit 1
}
echo "✓ Image pushed to DockerHub"

echo ""
echo "Step 5: Forcing ECS service update..."
echo "----------------------------------------"
aws ecs update-service \
    --cluster $CLUSTER \
    --service $SERVICE \
    --force-new-deployment \
    --region $REGION || {
    echo "ERROR: ECS update failed!"
    exit 1
}
echo "✓ ECS service update initiated"

echo ""
echo "Step 6: Monitoring deployment..."
echo "----------------------------------------"
echo "Waiting for new deployment to start..."
sleep 15

# Check service status
echo ""
echo "Current service status:"
aws ecs describe-services \
    --cluster $CLUSTER \
    --services $SERVICE \
    --region $REGION \
    --query 'services[0].{Desired:desiredCount,Running:runningCount,Pending:pendingCount}' \
    --output table

echo ""
echo "=========================================="
echo "Deployment Initiated Successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Monitor logs:"
echo "   aws logs tail /ecs/emg-classifier-api --follow --region $REGION"
echo ""
echo "2. Wait 2-3 minutes for deployment to complete"
echo ""
echo "3. Test health endpoint:"
echo "   curl http://emg-classifier-dev-alb-867322076.eu-north-1.elb.amazonaws.com/health"
echo ""
echo "4. Test with your data file:"
echo "   curl -X POST -F 'file=@your_data.csv' \\"
echo "     http://emg-classifier-dev-alb-867322076.eu-north-1.elb.amazonaws.com/predict"
echo ""
echo "=========================================="