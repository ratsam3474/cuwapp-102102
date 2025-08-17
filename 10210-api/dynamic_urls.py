"""
Dynamic URL Configuration and Container Provisioning System
Creates and manages user containers via DigitalOcean Functions
Allocates unique ports for each user's services
"""

import os
import logging
import random
import requests
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from database.connection import get_db
from sqlalchemy import text

logger = logging.getLogger(__name__)

class DynamicURLManager:
    """Manages user container provisioning and URL allocation via DO Functions"""
    
    def __init__(self):
        # Base configuration from environment
        self.base_url = os.getenv('BASE_URL', 'http://localhost')
        self.server_ip = os.getenv('NEW_SERVER_IP', '34.173.85.56')
        self.user_vm_ip = os.getenv('USER_VM_EXTERNAL_IP', '34.173.85.56')
        
        # Container Manager URL (Google Cloud Run)
        self.do_container_function_url = os.getenv('CONTAINER_MANAGER_URL', 
                                                   'https://container-manager-337193391523.us-central1.run.app')
        
        # Port ranges for services (aiming for 100,000 users)
        self.app_port_start = 40000
        self.app_port_end = 50000  # 10,000 possible app ports
        
        # Each user's container runs 3 services on consecutive ports
        # app_port, app_port+1 (warmer), app_port+2 (campaign)
        
        # Container timeout for free users (30 minutes)
        self.free_user_timeout_minutes = 30
    
    def get_next_available_port(self) -> int:
        """
        Find next available port for a new user container
        Returns base port (warmer = base+1, campaign = base+2)
        """
        try:
            with get_db() as db:
                # Get all allocated ports
                result = db.execute(text("""
                    SELECT app_port FROM user_infrastructure 
                    WHERE status = 'active'
                    ORDER BY app_port
                """))
                
                used_ports = set()
                for row in result:
                    port = row[0]
                    # Each user uses 3 consecutive ports
                    used_ports.add(port)
                    used_ports.add(port + 1)
                    used_ports.add(port + 2)
                
                # Find first available port (checking in blocks of 3)
                for port in range(self.app_port_start, self.app_port_end, 3):
                    if port not in used_ports and (port+1) not in used_ports and (port+2) not in used_ports:
                        return port
                
                # If all sequential ports used, find random available block
                for _ in range(100):  # Try 100 random positions
                    port = random.randrange(self.app_port_start, self.app_port_end - 2, 3)
                    if port not in used_ports and (port+1) not in used_ports and (port+2) not in used_ports:
                        return port
                
                raise Exception("No available ports found")
                
        except Exception as e:
            logger.error(f"Error finding available port: {e}")
            # Return random port as fallback
            return random.randrange(self.app_port_start, self.app_port_end - 2, 3)
    
    def create_user_container_via_do_function(self, user_id: str, plan_type: str) -> Dict[str, str]:
        """
        Create a new container for user via DigitalOcean Function
        Returns URLs for all services
        """
        if not self.do_container_function_url:
            logger.error("DO_CONTAINER_FUNCTION_URL not configured")
            # Return default URLs for development
            return {
                'api_url': f"{self.base_url}:8000",
                'warmer_url': f"{self.base_url}:20000",
                'campaign_url': f"{self.base_url}:30000",
                'status': 'function_not_configured'
            }
        
        try:
            logger.info(f"Creating container for user {user_id} via DO Function")
            
            # Call DO Function to create container on USER VM
            payload = {
                "action": "create",  # Routes to USER VM
                "user_id": user_id,
                "plan_type": plan_type,
                "environment": {
                    "REDIS_URL": os.getenv('REDIS_URL'),
                    "DATABASE_URL": os.getenv('DATABASE_URL'),
                    "CLERK_SECRET_KEY": os.getenv('CLERK_SECRET_KEY'),
                    "ENV": "production"
                }
            }
            
            response = requests.post(
                self.do_container_function_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                body = result.get("body", result)  # Handle DO Function response format
                if body.get("success"):
                    container_info = body.get("container", {})
                    
                    # Get URLs from DO Function response
                    urls = container_info.get('urls', {})
                    
                    # Build response
                    response_data = {
                        'api_url': urls.get('api'),
                        'warmer_url': urls.get('warmer'),
                        'campaign_url': urls.get('campaign'),
                        'container_id': container_info.get('id'),
                        'container_name': container_info.get('name'),
                        'status': 'running'
                    }
                    
                    # Save to database (extract port from URL)
                    if urls.get('api'):
                        app_port = int(urls['api'].split(':')[-1])
                        self.save_user_infrastructure(user_id, response_data, app_port, plan_type)
                    
                    logger.info(f"Successfully created container for user {user_id}")
                    return response_data
                else:
                    error = result.get("error", "Unknown error")
                    logger.error(f"DO Function failed: {error}")
                    raise Exception(f"Container creation failed: {error}")
            else:
                logger.error(f"DO Function returned status {response.status_code}: {response.text}")
                raise Exception(f"DO Function error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to create container for user {user_id}: {e}")
            # Return default URLs as fallback
            return {
                'api_url': f"{self.base_url}:8000",
                'warmer_url': f"{self.base_url}:20000",
                'campaign_url': f"{self.base_url}:30000",
                'status': 'error'
            }
    
    def save_user_infrastructure(self, user_id: str, urls: Dict, base_port: int, plan_type: str):
        """Save user infrastructure details to database"""
        try:
            with get_db() as db:
                # Check if table exists, create if not
                db.execute(text("""
                    CREATE TABLE IF NOT EXISTS user_infrastructure (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(255) UNIQUE NOT NULL,
                        container_id VARCHAR(255),
                        container_name VARCHAR(255),
                        api_url VARCHAR(255),
                        warmer_url VARCHAR(255),
                        campaign_url VARCHAR(255),
                        app_port INTEGER,
                        plan_type VARCHAR(50),
                        status VARCHAR(50) DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        auto_stop_at TIMESTAMP
                    )
                """))
                
                # Calculate auto-stop time for free users
                auto_stop_at = None
                if plan_type == 'free':
                    auto_stop_at = datetime.utcnow() + timedelta(minutes=self.free_user_timeout_minutes)
                
                # Insert or update user infrastructure
                db.execute(text("""
                    INSERT INTO user_infrastructure 
                    (user_id, container_id, container_name, api_url, warmer_url, campaign_url, 
                     app_port, plan_type, status, last_active, auto_stop_at)
                    VALUES (:user_id, :container_id, :container_name, :api_url, :warmer_url, 
                            :campaign_url, :app_port, :plan_type, 'active', :last_active, :auto_stop_at)
                    ON CONFLICT(user_id) DO UPDATE SET
                        container_id = :container_id,
                        container_name = :container_name,
                        api_url = :api_url,
                        warmer_url = :warmer_url,
                        campaign_url = :campaign_url,
                        app_port = :app_port,
                        plan_type = :plan_type,
                        status = 'active',
                        last_active = :last_active,
                        auto_stop_at = :auto_stop_at
                """), {
                    'user_id': user_id,
                    'container_id': urls.get('container_id'),
                    'container_name': urls.get('container_name'),
                    'api_url': urls['api_url'],
                    'warmer_url': urls['warmer_url'],
                    'campaign_url': urls['campaign_url'],
                    'app_port': base_port,
                    'plan_type': plan_type,
                    'last_active': datetime.utcnow(),
                    'auto_stop_at': auto_stop_at
                })
                
                db.commit()
                logger.info(f"Saved infrastructure for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error saving user infrastructure: {e}")
    
    def load_or_create_user_infrastructure(self, user_id: str) -> Dict[str, str]:
        """
        Load existing or create new infrastructure for user
        Called on sign-in and page refresh
        """
        try:
            with get_db() as db:
                # Get user's plan
                from database.subscription_models import UserSubscription
                subscription = db.query(UserSubscription).filter(
                    UserSubscription.user_id == user_id,
                    UserSubscription.status == 'active'
                ).first()
                
                plan_type = subscription.plan_type if subscription else 'free'
                
                # Check if user has existing infrastructure
                result = db.execute(text("""
                    SELECT container_id, container_name, api_url, warmer_url, campaign_url, 
                           status, auto_stop_at
                    FROM user_infrastructure
                    WHERE user_id = :user_id
                """), {'user_id': user_id}).first()
                
                if result:
                    # User has infrastructure record
                    container_id, container_name, api_url, warmer_url, campaign_url, status, auto_stop_at = result
                    
                    # Check if container needs to be restarted
                    needs_restart = False
                    if status == 'stopped':
                        needs_restart = True
                    elif plan_type == 'free' and auto_stop_at:
                        # Check if free user's container has timed out
                        if datetime.utcnow() > auto_stop_at:
                            needs_restart = True
                            logger.info(f"Free user {user_id} container timed out")
                    
                    if needs_restart:
                        logger.info(f"Container for user {user_id} needs restart")
                        return self.restart_user_container_via_do_function(user_id, container_name, plan_type)
                    
                    # Update last active time
                    new_auto_stop_at = None
                    if plan_type == 'free':
                        new_auto_stop_at = datetime.utcnow() + timedelta(minutes=self.free_user_timeout_minutes)
                    
                    db.execute(text("""
                        UPDATE user_infrastructure 
                        SET last_active = :last_active,
                            auto_stop_at = :auto_stop_at
                        WHERE user_id = :user_id
                    """), {
                        'last_active': datetime.utcnow(),
                        'auto_stop_at': new_auto_stop_at,
                        'user_id': user_id
                    })
                    db.commit()
                    
                    return {
                        'api_url': api_url,
                        'warmer_url': warmer_url,
                        'campaign_url': campaign_url,
                        'status': 'existing'
                    }
                else:
                    # No infrastructure exists, create new
                    logger.info(f"No infrastructure found for user {user_id}, creating new container...")
                    return self.create_user_container_via_do_function(user_id, plan_type)
                    
        except Exception as e:
            logger.error(f"Error loading/creating infrastructure for user {user_id}: {e}")
            # Return default URLs on error
            return {
                'api_url': f"{self.base_url}:8000",
                'warmer_url': f"{self.base_url}:20000",
                'campaign_url': f"{self.base_url}:30000",
                'status': 'error'
            }
    
    def restart_user_container_via_do_function(self, user_id: str, container_name: str, plan_type: str) -> Dict[str, str]:
        """Restart a stopped user container via DO Function"""
        if not self.do_container_function_url:
            logger.error("DO_CONTAINER_FUNCTION_URL not configured")
            return self.load_existing_urls(user_id)
        
        try:
            # Call DO Function to restart container
            payload = {
                "action": "restart",
                "docker_host": self.server_ip,
                "container_name": container_name,
                "user_id": user_id
            }
            
            response = requests.post(
                self.do_container_function_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    logger.info(f"Successfully restarted container {container_name}")
                    
                    # Update database status
                    with get_db() as db:
                        auto_stop_at = None
                        if plan_type == 'free':
                            auto_stop_at = datetime.utcnow() + timedelta(minutes=self.free_user_timeout_minutes)
                        
                        db.execute(text("""
                            UPDATE user_infrastructure 
                            SET status = 'active', 
                                last_active = :last_active,
                                auto_stop_at = :auto_stop_at
                            WHERE user_id = :user_id
                        """), {
                            'last_active': datetime.utcnow(),
                            'auto_stop_at': auto_stop_at,
                            'user_id': user_id
                        })
                        db.commit()
                    
                    return self.load_existing_urls(user_id)
                else:
                    # Container might not exist, create new one
                    logger.info(f"Container {container_name} not found, creating new one")
                    return self.create_user_container_via_do_function(user_id, plan_type)
            else:
                logger.error(f"DO Function restart failed: {response.status_code}")
                # Try to create new container as fallback
                return self.create_user_container_via_do_function(user_id, plan_type)
                
        except Exception as e:
            logger.error(f"Error restarting container for user {user_id}: {e}")
            return self.load_existing_urls(user_id)
    
    def stop_user_container_via_do_function(self, user_id: str) -> bool:
        """Stop a user's container (for free users after timeout)"""
        if not self.do_container_function_url:
            return False
        
        try:
            with get_db() as db:
                # Get container name
                result = db.execute(text("""
                    SELECT container_name FROM user_infrastructure
                    WHERE user_id = :user_id
                """), {'user_id': user_id}).first()
                
                if not result:
                    return False
                
                container_name = result[0]
                
                # Call DO Function to stop container
                payload = {
                    "action": "stop",
                    "docker_host": self.server_ip,
                    "container_name": container_name,
                    "user_id": user_id
                }
                
                response = requests.post(
                    self.do_container_function_url,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    # Update database status
                    db.execute(text("""
                        UPDATE user_infrastructure 
                        SET status = 'stopped'
                        WHERE user_id = :user_id
                    """), {'user_id': user_id})
                    db.commit()
                    
                    logger.info(f"Stopped container for user {user_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error stopping container for user {user_id}: {e}")
        
        return False
    
    def load_existing_urls(self, user_id: str) -> Dict[str, str]:
        """Load existing URLs from database"""
        try:
            with get_db() as db:
                result = db.execute(text("""
                    SELECT api_url, warmer_url, campaign_url
                    FROM user_infrastructure
                    WHERE user_id = :user_id
                """), {'user_id': user_id}).first()
                
                if result:
                    return {
                        'api_url': result[0],
                        'warmer_url': result[1],
                        'campaign_url': result[2],
                        'status': 'loaded'
                    }
                    
        except Exception as e:
            logger.error(f"Error loading URLs for user {user_id}: {e}")
        
        # Return defaults
        return {
            'api_url': f"{self.base_url}:8000",
            'warmer_url': f"{self.base_url}:20000",
            'campaign_url': f"{self.base_url}:30000",
            'status': 'default'
        }

# Global instance
url_manager = DynamicURLManager()