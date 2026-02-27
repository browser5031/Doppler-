#!/bin/bash
# Quick Start Script - Get to 1M Faces FAST!

echo "🚀 DOPPELGANGER AUTO-SCRAPER"
echo "================================"
echo ""
echo "This script will continuously discover and scrape yearbooks"
echo "Target: 1,000,000 faces"
echo ""

# Check if backend is running
if ! curl -s http://localhost:8001/api/ > /dev/null; then
    echo "❌ Backend is not running!"
    echo "   Starting backend..."
    sudo supervisorctl start backend
    sleep 5
fi

# Check backend again
if curl -s http://localhost:8001/api/ > /dev/null; then
    echo "✅ Backend is running"
else
    echo "❌ Failed to start backend. Please check logs:"
    echo "   tail -f /var/log/supervisor/backend.err.log"
    exit 1
fi

echo ""
echo "Starting auto-scraper..."
echo "Press Ctrl+C to stop"
echo ""
echo "================================"
echo ""

# Run the auto-scraper
cd /app
python3 auto_scraper.py 50  # Run 50 cycles (about 10,000 yearbooks)
