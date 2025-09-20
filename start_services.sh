#!/bin/bash

# Start Services Script
echo "🚀 Starting IoT Platform Services..."
echo "==================================="

# Check if virtual environment is activated, if not activate it
if [ -z "$VIRTUAL_ENV" ]; then
    echo "🐍 Virtual environment not active. Activating..."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        echo "❌ Virtual environment not found at venv/bin/activate"
        exit 1
    fi
fi

# Check if Gunicorn is already running
if pgrep -f "gunicorn" > /dev/null; then
    echo "⚠️  Gunicorn is already running. Stopping it first..."
    pkill -f "gunicorn"
    sleep 2
fi

# Start Gunicorn
echo "🔧 Starting Gunicorn on port 8000..."
cd /home/ubuntu/HeatExchanger_Only_IOT
nohup gunicorn --bind 0.0.0.0:8000 --workers 3 --access-logfile gunicorn_access.log --error-logfile gunicorn_error.log iot_platform.wsgi:application > gunicorn.log 2>&1 &
GUNICORN_PID=$!

# Wait for Gunicorn to start
sleep 3

# Check if Gunicorn started successfully
if ps -p $GUNICORN_PID > /dev/null; then
    echo "✅ Gunicorn started successfully (PID: $GUNICORN_PID)"
else
    echo "❌ Gunicorn failed to start. Check gunicorn_error.log"
    exit 1
fi

# Start Nginx
echo "🌐 Starting Nginx..."
if command -v nginx >/dev/null 2>&1; then
    sudo systemctl start nginx 2>/dev/null || sudo service nginx start 2>/dev/null
    sleep 2
    
    if sudo systemctl is-active --quiet nginx || sudo service nginx status >/dev/null 2>&1; then
        echo "✅ Nginx started successfully"
    else
        echo "❌ Nginx failed to start. Check status: sudo systemctl status nginx"
    fi
else
    echo "⚠️  Nginx not installed. Skipping Nginx startup."
fi

echo ""
echo "🎉 Services started successfully!"
echo "================================="
echo "Gunicorn PID: $GUNICORN_PID"
echo "Nginx status: $(if command -v nginx >/dev/null 2>&1; then sudo systemctl is-active nginx || echo 'unknown'; else echo 'not installed'; fi)"
echo ""
echo "🌐 Application URLs:"
echo "Direct Gunicorn: http://127.0.0.1:8000/admin"
echo "Through Nginx: http://$(curl -4 -s icanhazip.com || hostname -I | awk '{print $1}')/admin"
echo ""
echo "📋 Logs:"
echo "Gunicorn: tail -f gunicorn.log"
echo "Gunicorn Access: tail -f gunicorn_access.log"
echo "Gunicorn Error: tail -f gunicorn_error.log"
echo "Nginx: sudo tail -f /var/log/nginx/error.log"
