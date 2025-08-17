#!/bin/bash

# Script to run Celery workers and beat scheduler
# Usage: ./run_celery.sh [worker|beat|flower|all]

# Load environment variables from .env.production
if [ -f .env.production ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
    echo "Loaded environment from .env.production"
else
    echo "Warning: .env.production not found!"
    exit 1
fi

# Check if REDIS_URL is set
if [ -z "$REDIS_URL" ]; then
    echo "Error: REDIS_URL not set in .env.production"
    exit 1
fi

case "$1" in
    worker)
        echo "Starting Celery worker..."
        celery -A celery_app worker \
            --loglevel=info \
            --concurrency=4 \
            --queues=campaigns,warmers,general \
            --pool=threads
        ;;
    
    beat)
        echo "Starting Celery beat scheduler..."
        celery -A celery_app beat \
            --loglevel=info
        ;;
    
    flower)
        echo "Starting Flower monitoring..."
        celery -A celery_app flower \
            --port=5555 \
            --basic_auth=admin:password
        ;;
    
    all)
        echo "Starting all Celery services..."
        
        # Start worker in background
        celery -A celery_app worker \
            --loglevel=info \
            --concurrency=4 \
            --queues=campaigns,warmers,general \
            --pool=threads \
            --detach \
            --pidfile=celery_worker.pid
        
        # Start beat in background
        celery -A celery_app beat \
            --loglevel=info \
            --detach \
            --pidfile=celery_beat.pid
        
        # Start flower in foreground
        celery -A celery_app flower \
            --port=5555 \
            --basic_auth=admin:password
        ;;
    
    stop)
        echo "Stopping Celery services..."
        
        if [ -f celery_worker.pid ]; then
            kill $(cat celery_worker.pid)
            rm celery_worker.pid
            echo "Worker stopped"
        fi
        
        if [ -f celery_beat.pid ]; then
            kill $(cat celery_beat.pid)
            rm celery_beat.pid
            echo "Beat stopped"
        fi
        
        pkill -f "celery.*flower"
        echo "Flower stopped"
        ;;
    
    status)
        echo "Celery services status:"
        
        if [ -f celery_worker.pid ] && ps -p $(cat celery_worker.pid) > /dev/null; then
            echo "✓ Worker is running (PID: $(cat celery_worker.pid))"
        else
            echo "✗ Worker is not running"
        fi
        
        if [ -f celery_beat.pid ] && ps -p $(cat celery_beat.pid) > /dev/null; then
            echo "✓ Beat is running (PID: $(cat celery_beat.pid))"
        else
            echo "✗ Beat is not running"
        fi
        
        if pgrep -f "celery.*flower" > /dev/null; then
            echo "✓ Flower is running"
        else
            echo "✗ Flower is not running"
        fi
        ;;
    
    *)
        echo "Usage: $0 {worker|beat|flower|all|stop|status}"
        echo ""
        echo "  worker  - Start Celery worker"
        echo "  beat    - Start Celery beat scheduler"
        echo "  flower  - Start Flower monitoring UI"
        echo "  all     - Start all services"
        echo "  stop    - Stop all services"
        echo "  status  - Check services status"
        exit 1
        ;;
esac