#!/bin/bash

# Stop Services Script
echo "🛑 Stopping IoT Platform Services..."
echo "==================================="

# Stop Gunicorn
echo "🔧 Stopping Gunicorn..."
if pgrep -f "gunicorn" > /dev/null; then
    pkill -f "gunicorn"
    echo "✅ Gunicorn stopped"
else
    echo "ℹ️  Gunicorn was not running"
fi

# Stop Nginx
echo "🌐 Stopping Nginx..."
if command -v nginx >/dev/null 2>&1; then
    if sudo systemctl is-active --quiet nginx || sudo service nginx status >/dev/null 2>&1; then
        sudo systemctl stop nginx 2>/dev/null || sudo service nginx stop 2>/dev/null
        echo "✅ Nginx stopped"
    else
        echo "ℹ️  Nginx was not running"
    fi
else
    echo "ℹ️  Nginx not installed"
fi

# Clean up any remaining processes
echo "🧹 Cleaning up..."
pkill -f "gunicorn" 2>/dev/null || true

echo ""
echo "✅ All services stopped successfully!"
echo "====================================="
echo "Gunicorn: $(pgrep -f "gunicorn" > /dev/null && echo 'running' || echo 'stopped')"
echo "Nginx: $(if command -v nginx >/dev/null 2>&1; then sudo systemctl is-active nginx || echo 'stopped'; else echo 'not installed'; fi)"
