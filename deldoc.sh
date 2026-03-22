#!/bin/bash

# scawy
echo "Stopping all containers..."
docker stop $(docker ps -aq) 2>/dev/null
echo "Pruning all images, containers, volumes, and build cache..."
docker system prune -a --volumes -f
echo "Cleanup complete."