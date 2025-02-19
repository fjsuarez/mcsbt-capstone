#!/bin/bash
set -e

# Start microservices in the background
echo "Starting admin-service..."
(cd services/admin-service && nohup uv run python main.py > admin-service.log 2>&1 &)

echo "Starting notification-service..."
(cd services/notification-service && nohup uv run python main.py > notification-service.log 2>&1 &)

echo "Starting review-service..."
(cd services/review-service && nohup uv run python main.py > review-service.log 2>&1 &)

echo "Starting ride-service..."
(cd services/ride-service && nohup uv run python main.py > ride-service.log 2>&1 &)

echo "Starting user-service..."
(cd services/user-service && nohup uv run python main.py > user-service.log 2>&1 &)

# Start the API gateway
echo "Starting API gateway..."
nohup uv run main.py > api-gateway.log 2>&1 &

echo "All services started! Use 'tail -f <logfile>' to check logs."