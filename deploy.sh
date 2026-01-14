#!/bin/bash

# Default mode
CLEAN_MODE=false

# Check arguments
if [[ "$1" == "--clean" ]]; then
    CLEAN_MODE=true
    echo "WARNING: CLEAN MODE ACTIVATED. ALL DATA WILL BE WIPED."
    echo "Waiting 5 seconds before proceeding... (Ctrl+C to cancel)"
    sleep 5
fi

# Ensure we are in the script's directory
cd "$(dirname "$0")"

echo "Step 1: Pulling latest changes from git..."
git pull
if [ $? -ne 0 ]; then
    echo "Error: git pull failed. Please check your manual intervention."
    exit 1
fi

echo "Step 2: Managing Docker services..."

if [ "$CLEAN_MODE" = true ]; then
    echo "Stopping and removing EVERYTHING (containers, networks, volumes)..."
    docker compose down -v
    
    echo "Pruning unused images/systems to ensure fresh start..."
    docker system prune -f
else
    echo "Stopping containers (preserving volumes)..."
    docker compose down
fi

echo "Step 3: Building and Starting services..."
docker compose up -d --build

echo "Step 4: Checking status..."
sleep 5
if docker compose ps | grep -q "Up"; then
    echo "Deployment Successful!"
    echo "App should be running on port 8000"
    docker compose ps
else
    echo "Warning: Services might not be up. Check logs with 'docker compose logs -f'"
fi
