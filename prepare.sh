#!/bin/bash

# Evil_Proxy Directory Setup Helper
# This script prepares the environment by creating necessary directories and setting permissions.

set -e

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Evil_Proxy environment preparation...${NC}"

# 1. Dependency Checks
echo -e "${YELLOW}Checking dependencies...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Warning: docker is not installed. You will need it to run the proxy.${NC}"
fi

if ! command -v docker compose &> /dev/null; then
    echo -e "${YELLOW}Warning: docker compose is not installed. You will need it to run the proxy.${NC}"
fi

# 2. Directory Creation
echo -e "${YELLOW}Creating directory structure...${NC}"
DIRECTORIES=(
    "Data/HAR_Out"
    "Data/Tokens"
    "Data/Other"
    "Certs"
)

for dir in "${DIRECTORIES[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "${GREEN}Created directory: $dir${NC}"
    else
        echo -e "Directory already exists: $dir"
        read -p "Do you want to remove the existing directory and create a new one? (y/n) " ans
        if [ "$ans" = "y" ]; then
            rm -rf "$dir"
            echo -e "${GREEN}Removed directory: $dir${NC}"
            mkdir -p "$dir"
            echo -e "${GREEN}Created directory: $dir${NC}"
        else
            exit 1
        fi
    fi
done

# 3. Initialize Required Files
echo -e "${YELLOW}Initializing data files...${NC}"
if [ ! -f "Data/Other/blocked_ips.json" ]; then
    echo "[]" > "Data/Other/blocked_ips.json"
    echo -e "${GREEN}Created empty blocked_ips.json${NC}"
fi

if [ ! -f "Data/Other/debug.log" ]; then
    touch "Data/Other/debug.log"
    echo -e "${GREEN}Created empty debug.log${NC}"
fi

# 4. Permission Management
echo -e "${YELLOW}Setting permissions...${NC}"

# Set ownership for Data directory (commonly 1000:1000 for Docker)
echo -e "${YELLOW}Setting ownership for Data directory...${NC}"
sudo chown -R 1000:1000 Data/ Certs/
echo -e "${GREEN}Set ownership for Data directory${NC}"

# Make user Scripts executable
if [ -d "ManageScripts" ]; then
    chmod +x ManageScripts/*.sh 2>/dev/null || true
    chmod +x ManageScripts/*.py 2>/dev/null || true
    chmod +x Evil_Proxy.sh 2>/dev/null || true
    echo -e "${GREEN}Set execution permissions for ManageScripts${NC}"
fi

# Make main scripts executable
if [ -d "Scripts" ]; then
    chmod +x Scripts/*.py 2>/dev/null || true
    echo -e "${GREEN}Set execution permissions for Scripts${NC}"
fi

echo -e "${YELLOW}Note: If you encounter permission issues in Docker, run:${NC}"

# Set directory permissions
chmod -R 755 Data/ Certs/
echo -e "${GREEN}Set directory permissions (755) for Data and Certs${NC}"

echo -e "${BLUE}Setup complete! You can now start the proxy using docker compose.${NC}"
echo -e "Usage: ${YELLOW}docker compose up -d${NC}"
