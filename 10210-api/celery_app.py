"""
Celery configuration for WhatsApp Agent
Handles background tasks for campaigns, warmers, and general operations
"""

import os
from celery import Celery
from celery.schedules import crontab
import logging

logger = logging.getLogger(__name__)

# Load environment variables from .env.production
from dotenv import load_dotenv
load_dotenv('.env.production')

# Get Redis URL from environment - should be your Upstash Redis URL
REDIS_URL = os.getenv('REDIS_URL')

if not REDIS_URL:
    logger.error("REDIS_URL environment variable not set!")
    logger.info("Please add REDIS_URL to your .env.production file")
    raise ValueError("REDIS_URL is required for Celery")

# Create Celery app
app = Celery(
    'whatsapp_agent',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        'celery_tasks.campaign_tasks',
        'celery_tasks.warmer_tasks',
        'celery_tasks.general_tasks'
    ]
)

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Each worker only fetches 1 task at a time
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks to prevent memory leaks
    
    # Task execution settings
    task_acks_late=True,  # Tasks are acknowledged after they have been executed
    task_reject_on_worker_lost=True,  # Reject tasks when worker is lost
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Retry settings
    task_default_retry_delay=60,  # 60 seconds
    task_max_retries=3,
    
    # Rate limiting (adjust based on WhatsApp limits)
    task_default_rate_limit='100/m',  # 100 tasks per minute globally
    
    # Beat schedule for periodic tasks
    beat_schedule={
        # Check warmer time limits every 5 minutes
        'check-warmer-limits': {
            'task': 'celery_tasks.warmer_tasks.check_warmer_time_limits',
            'schedule': crontab(minute='*/5'),
        },
        # Process campaign queue every minute
        'process-campaign-queue': {
            'task': 'celery_tasks.campaign_tasks.process_campaign_queue',
            'schedule': crontab(minute='*'),
        },
        # Clean up old sessions every hour
        'cleanup-sessions': {
            'task': 'celery_tasks.general_tasks.cleanup_old_sessions',
            'schedule': crontab(minute=0),  # Every hour at minute 0
        },
        # Update usage metrics every 15 minutes
        'update-metrics': {
            'task': 'celery_tasks.general_tasks.update_usage_metrics',
            'schedule': crontab(minute='*/15'),
        },
    },
)

# Task routing - send tasks to specific queues
app.conf.task_routes = {
    'celery_tasks.campaign_tasks.*': {'queue': 'campaigns'},
    'celery_tasks.warmer_tasks.*': {'queue': 'warmers'},
    'celery_tasks.general_tasks.*': {'queue': 'general'},
}

# Queue configuration
app.conf.task_queues = {
    'campaigns': {
        'routing_key': 'campaigns',
        'priority': 5,
    },
    'warmers': {
        'routing_key': 'warmers',
        'priority': 3,
    },
    'general': {
        'routing_key': 'general',
        'priority': 1,
    },
}

if __name__ == '__main__':
    app.start()