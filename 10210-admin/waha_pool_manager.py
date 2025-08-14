#!/usr/bin/env python3
"""
WAHA Docker Instance Pool Manager
Manages multiple WAHA Docker containers with 100-session capacity each
"""

import docker
import requests
import logging
import sqlite3
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class WAHAPoolManager:
    def __init__(self, db_path: str = "data/wagent.db"):
        try:
            self.docker_client = docker.from_env()
            self.docker_available = True
        except Exception as e:
            logger.warning(f"Docker client not available: {e}")
            self.docker_client = None
            self.docker_available = False
        
        self.db_path = db_path
        self.max_sessions_per_instance = 100
        self.base_port = 4500
        self.network_name = "cuwhapp-network"
        self.free_instance_url = "http://localhost:4500"  # Instance 1 for free users
        
    def get_db_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def get_user_plan(self, user_id: str) -> Tuple[str, int]:
        """Get user's plan type and session limit"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check user subscription
            cursor.execute("""
                SELECT plan_type, max_sessions 
                FROM user_subscriptions 
                WHERE user_id = ? AND status = 'active'
            """, (user_id,))
            
            result = cursor.fetchone()
            if result:
                return result[0], result[1]
            
            # Default to free plan
            return 'free', 1
            
        finally:
            conn.close()
    
    def get_instance_session_count(self, instance_url: str) -> int:
        """Get current session count for an instance"""
        try:
            response = requests.get(f"{instance_url}/api/sessions", timeout=5)
            if response.status_code == 200:
                sessions = response.json()
                if isinstance(sessions, list):
                    return len(sessions)
                elif isinstance(sessions, dict) and 'sessions' in sessions:
                    return len(sessions['sessions'])
            return 0
        except Exception as e:
            logger.error(f"Failed to get session count from {instance_url}: {e}")
            return 0
    
    def get_or_create_instance_for_user(self, user_id: str, session_name: str) -> str:
        """Get WAHA instance URL for user based on their plan"""
        
        plan_type, max_sessions = self.get_user_plan(user_id)
        
        # Free users always use the default instance
        if plan_type.lower() == 'free':
            logger.info(f"Free user {user_id} assigned to default instance")
            return self.free_instance_url
        
        # Paid users get pooled instances
        return self.find_or_create_instance(max_sessions)
    
    def find_or_create_instance(self, sessions_needed: int) -> str:
        """Find available instance or create new one for paid users"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get all active instances (excluding free instance)
            cursor.execute("""
                SELECT instance_id, url, current_sessions 
                FROM waha_instances 
                WHERE is_active = 1 AND instance_id > 1
                ORDER BY current_sessions ASC
            """)
            
            instances = cursor.fetchall()
            
            # Find instance with enough space
            for instance_id, url, current_sessions in instances:
                # Update actual count
                actual_count = self.get_instance_session_count(url)
                
                # Update database
                cursor.execute("""
                    UPDATE waha_instances 
                    SET current_sessions = ?, last_health_check = ?
                    WHERE instance_id = ?
                """, (actual_count, datetime.now(), instance_id))
                
                available_space = self.max_sessions_per_instance - actual_count
                
                # Leave 5 session buffer
                if available_space >= sessions_needed + 5:
                    conn.commit()
                    logger.info(f"Using instance {instance_id} with {available_space} slots available")
                    return url
            
            # No available instance, create new one
            new_url = self.create_new_instance()
            conn.commit()
            return new_url
            
        except Exception as e:
            logger.error(f"Error finding instance: {e}")
            conn.rollback()
            # Fallback to creating new instance
            return self.create_new_instance()
        finally:
            conn.close()
    
    def create_new_instance(self) -> str:
        """Create a new WAHA Docker container"""
        if not self.docker_available:
            logger.error("Docker not available, cannot create new instance")
            return self.free_instance_url
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Find next available instance ID
            cursor.execute("SELECT MAX(instance_id) FROM waha_instances")
            max_id = cursor.fetchone()[0] or 1
            instance_id = max_id + 1
            
            port = self.base_port + instance_id
            container_name = f"cuwhapp-waha-{instance_id}"
            
            logger.info(f"Creating new WAHA instance {instance_id} on port {port}")
            
            # Create Docker container
            container = self.docker_client.containers.run(
                image="devlikeapro/waha-plus:latest",
                name=container_name,
                ports={'3000/tcp': port},
                environment={
                    'WAHA_PRINT_QR': 'true',
                    'WAHA_LOG_LEVEL': 'info',
                    'WAHA_SESSION_STORE_ENABLED': 'true',
                    'WAHA_SESSION_STORE_PATH': '/app/sessions',
                    'WAHA_FILES_MIMETYPES': 'audio,image,video,document',
                    'WAHA_FILES_LIFETIME': '180'
                },
                volumes={
                    f'waha_sessions_{instance_id}': {
                        'bind': '/app/sessions',
                        'mode': 'rw'
                    },
                    f'waha_files_{instance_id}': {
                        'bind': '/app/files',
                        'mode': 'rw'
                    }
                },
                labels={
                    'waha-pool': 'true',
                    'waha-instance-id': str(instance_id),
                    'waha-port': str(port)
                },
                network=self.network_name,
                detach=True,
                restart_policy={"Name": "unless-stopped"}
            )
            
            url = f"http://localhost:{port}"
            
            # Save to database
            cursor.execute("""
                INSERT INTO waha_instances 
                (instance_id, container_name, port, url, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (instance_id, container_name, port, url, datetime.now()))
            
            conn.commit()
            logger.info(f"Successfully created instance {instance_id}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to create instance: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def save_session_assignment(self, user_id: str, session_name: str, instance_url: str):
        """Save the WAHA instance assignment for a session"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Extract instance ID from URL
            port = int(instance_url.split(':')[-1])
            instance_id = port - self.base_port
            
            # Update session with instance assignment
            cursor.execute("""
                UPDATE warmer_sessions 
                SET waha_instance_url = ?, 
                    waha_instance_id = ?,
                    last_activity = ?
                WHERE user_id = ? AND session_name = ?
            """, (instance_url, instance_id, datetime.now(), user_id, session_name))
            
            conn.commit()
            logger.info(f"Assigned session {session_name} to instance {instance_id}")
            
        except Exception as e:
            logger.error(f"Failed to save assignment: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_session_instance(self, user_id: str, session_name: str) -> Optional[str]:
        """Get the WAHA instance URL for an existing session"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT waha_instance_url 
                FROM warmer_sessions 
                WHERE user_id = ? AND session_name = ? AND is_active = 1
            """, (user_id, session_name))
            
            result = cursor.fetchone()
            if result:
                return result[0]
            return None
            
        finally:
            conn.close()
    
    def get_pool_status(self) -> Dict:
        """Get status of all WAHA instances"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT instance_id, container_name, port, url, current_sessions 
                FROM waha_instances 
                WHERE is_active = 1
                ORDER BY instance_id
            """)
            
            instances = cursor.fetchall()
            
            status = {
                "total_instances": len(instances),
                "total_capacity": len(instances) * self.max_sessions_per_instance,
                "instances": []
            }
            
            total_sessions = 0
            
            for instance_id, name, port, url, db_sessions in instances:
                # Get actual count from WAHA
                actual_sessions = self.get_instance_session_count(url)
                total_sessions += actual_sessions
                
                # Check if container is running
                if self.docker_available:
                    try:
                        container = self.docker_client.containers.get(name)
                        container_status = container.status
                    except:
                        container_status = "not_found"
                else:
                    container_status = "docker_unavailable"
                
                instance_type = "free_users" if instance_id == 1 else "paid_pool"
                
                status["instances"].append({
                    "id": instance_id,
                    "type": instance_type,
                    "name": name,
                    "port": port,
                    "url": url,
                    "sessions": actual_sessions,
                    "capacity": self.max_sessions_per_instance,
                    "utilization": f"{(actual_sessions/self.max_sessions_per_instance)*100:.1f}%",
                    "status": container_status
                })
            
            status["total_sessions"] = total_sessions
            return status
            
        finally:
            conn.close()

# Global instance
try:
    waha_pool = WAHAPoolManager()
except Exception as e:
    logger.warning(f"Could not initialize WAHAPoolManager: {e}")
    waha_pool = None