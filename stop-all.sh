#!/bin/bash
set -e

# List of ports used by API gateway and microservices
PORTS=(8000 8001 8002 8003 8004 8005)

for port in "${PORTS[@]}"; do
    echo "Checking for process on port $port..."
    pid=$(lsof -t -i:"$port")
    if [ -n "$pid" ]; then
        echo "Killing process $pid on port $port"
        kill "$pid"
    else
        echo "No process found on port $port"
    fi
done

echo "Shutdown complete."