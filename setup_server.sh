#!/bin/bash

# setup_server.sh
# Script to install Docker and prepare the environment on a fresh VPS.

echo "Step 0: Installing Docker and dependencies..."

# Check if Docker is already installed
if command -v docker &> /dev/null; then
    echo "Docker is already installed."
else
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo "Docker installed successfully."
fi

# Ensure the script is executable
chmod +x deploy.sh

echo "Setup complete! You can now run ./deploy.sh"
