#!/bin/bash

# Restart Services Script
echo "🔄 Restarting IoT Platform Services..."
echo "======================================"

# Run stop script
/home/ubuntu/HeatExchanger_Only_IOT/stop_services.sh

# Wait a moment
sleep 3

# Run start script
/home/ubuntu/HeatExchanger_Only_IOT/start_services.sh

echo ""
echo "✅ Services restarted successfully!"
