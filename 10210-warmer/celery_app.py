"""
Celery configuration for Warmer Service
"""
from celery import Celery
import os

# Create Celery instance with Upstash Redis
# Get Upstash credentials from environment
import os
UPSTASH_REDIS_URL = os.getenv('UPSTASH_REDIS_URL', 'redis://default:YOUR_PASSWORD@YOUR_ENDPOINT.upstash.io:PORT')

celery_app = Celery(
    'warmer',
    broker=UPSTASH_REDIS_URL,
    backend=UPSTASH_REDIS_URL,
    include=['warmer_tasks']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # Soft limit at 55 minutes
    worker_prefetch_multiplier=1,  # Only fetch 1 task at a time per worker
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (prevent memory leaks)
)

# Task routing - can route specific tasks to specific queues
celery_app.conf.task_routes = {
    'warmer_tasks.warm_session': {'queue': 'warmer'},
    'warmer_tasks.process_warmer_batch': {'queue': 'warmer'},
}

if __name__ == '__main__':
    celery_app.start()