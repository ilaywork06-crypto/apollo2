#!/bin/bash
echo "Updating Apollo..."
git pull
echo ""
echo "Rebuilding Docker images..."
cd docker
docker-compose down
docker-compose build --no-cache
echo ""
echo "Update complete! Run start.sh to start the app."
read -rp "Press Enter to continue..."
