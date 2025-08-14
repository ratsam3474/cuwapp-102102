"""
File management utilities for user-based file storage
"""

import os
import shutil
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class UserFileManager:
    """Manages user-specific file storage"""
    
    BASE_UPLOAD_DIR = "static/uploads"
    
    @classmethod
    def get_user_directory(cls, user_id: str, sub_dir: Optional[str] = None) -> str:
        """Get user-specific directory path"""
        if not user_id:
            # Fallback to shared directory for admin/system operations
            user_dir = os.path.join(cls.BASE_UPLOAD_DIR, "shared")
        else:
            # User-specific directory
            user_dir = os.path.join(cls.BASE_UPLOAD_DIR, "users", user_id)
        
        # Add subdirectory if specified (e.g., 'campaigns', 'exports', 'warmers')
        if sub_dir:
            user_dir = os.path.join(user_dir, sub_dir)
        
        # Create directory if it doesn't exist
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    @classmethod
    def save_campaign_file(cls, user_id: str, file_content: bytes, filename: str) -> str:
        """Save campaign file to user directory"""
        # Get user's campaign directory
        campaign_dir = cls.get_user_directory(user_id, "campaigns")
        
        # Add timestamp to filename to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name, ext = os.path.splitext(filename)
        unique_filename = f"{base_name}_{timestamp}{ext}"
        
        # Full path for the file
        file_path = os.path.join(campaign_dir, unique_filename)
        
        # Save the file
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"Saved campaign file for user {user_id}: {file_path}")
        return file_path
    
    @classmethod
    def save_export_file(cls, user_id: str, file_content: bytes, filename: str) -> str:
        """Save export file to user directory"""
        # Get user's export directory
        export_dir = cls.get_user_directory(user_id, "exports")
        
        # Add timestamp to filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name, ext = os.path.splitext(filename)
        unique_filename = f"{base_name}_{timestamp}{ext}"
        
        # Full path for the file
        file_path = os.path.join(export_dir, unique_filename)
        
        # Save the file
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"Saved export file for user {user_id}: {file_path}")
        return file_path
    
    @classmethod
    def get_user_files(cls, user_id: str, sub_dir: Optional[str] = None) -> list:
        """List all files in user directory"""
        user_dir = cls.get_user_directory(user_id, sub_dir)
        
        files = []
        for filename in os.listdir(user_dir):
            file_path = os.path.join(user_dir, filename)
            if os.path.isfile(file_path):
                files.append({
                    "filename": filename,
                    "path": file_path,
                    "size": os.path.getsize(file_path),
                    "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                })
        
        return files
    
    @classmethod
    def delete_user_file(cls, user_id: str, file_path: str) -> bool:
        """Delete a user file (only if it belongs to the user)"""
        # Verify the file is in the user's directory
        user_dir = cls.get_user_directory(user_id)
        
        # Ensure the file path is within user's directory (security check)
        abs_file_path = os.path.abspath(file_path)
        abs_user_dir = os.path.abspath(user_dir)
        
        if not abs_file_path.startswith(abs_user_dir):
            logger.warning(f"Attempted to delete file outside user directory: {file_path}")
            return False
        
        if os.path.exists(abs_file_path):
            os.remove(abs_file_path)
            logger.info(f"Deleted file for user {user_id}: {file_path}")
            return True
        
        return False
    
    @classmethod
    def cleanup_old_files(cls, user_id: str, days_old: int = 30) -> int:
        """Clean up old files from user directory"""
        user_dir = cls.get_user_directory(user_id)
        
        deleted_count = 0
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        
        for root, dirs, files in os.walk(user_dir):
            for filename in files:
                file_path = os.path.join(root, filename)
                if os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"Cleaned up old file: {file_path}")
        
        return deleted_count