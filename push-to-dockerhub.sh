#!/bin/bash

# Script to build and push Docker images to Docker Hub
# Usage: ./push-to-dockerhub.sh <dockerhub-username>

set -e

# Check if Docker Hub username is provided
if [ -z "$1" ]; then
    echo "Error: Docker Hub username is required"
    echo "Usage: ./push-to-dockerhub.sh <dockerhub-username>"
    echo "Example: ./push-to-dockerhub.sh tanmayranaware"
    exit 1
fi

DOCKERHUB_USERNAME=$1
BACKEND_IMAGE="rca-backend"
FRONTEND_IMAGE="rca-frontend"
BACKEND_TAG="${DOCKERHUB_USERNAME}/${BACKEND_IMAGE}:latest"
FRONTEND_TAG="${DOCKERHUB_USERNAME}/${FRONTEND_IMAGE}:latest"

echo "=========================================="
echo "Building and Pushing Images to Docker Hub"
echo "=========================================="
echo "Docker Hub Username: ${DOCKERHUB_USERNAME}"
echo ""

# Check if user is logged in to Docker Hub
echo "Checking Docker Hub login status..."
if ! docker info | grep -q "Username"; then
    echo "Please login to Docker Hub first:"
    echo "  docker login"
    exit 1
fi

echo "✓ Logged in to Docker Hub"
echo ""

# Build backend image
echo "Building backend image..."
cd backend
docker build -t ${BACKEND_IMAGE}:latest -t ${BACKEND_TAG} .
cd ..
echo "✓ Backend image built"
echo ""

# Build frontend image
echo "Building frontend image..."
cd frontend
docker build -t ${FRONTEND_IMAGE}:latest -t ${FRONTEND_TAG} .
cd ..
echo "✓ Frontend image built"
echo ""

# Push backend image
echo "Pushing backend image to Docker Hub..."
docker push ${BACKEND_TAG}
echo "✓ Backend image pushed"
echo ""

# Push frontend image
echo "Pushing frontend image to Docker Hub..."
docker push ${FRONTEND_TAG}
echo "✓ Frontend image pushed"
echo ""

echo "=========================================="
echo "Success! Images pushed to Docker Hub"
echo "=========================================="
echo "Backend:  ${BACKEND_TAG}"
echo "Frontend: ${FRONTEND_TAG}"
echo ""
echo "You can now pull these images using:"
echo "  docker pull ${BACKEND_TAG}"
echo "  docker pull ${FRONTEND_TAG}"
echo ""

