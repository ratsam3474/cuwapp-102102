"""
Database initialization script
Run this to set up the database for the first time
"""

import sys
import os
import logging

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.migrations import initialize_database
from database.connection import test_connection, get_database_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Initialize the database"""
    print("🚀 Initializing WhatsApp Agent Database...")
    
    try:
        # Initialize database
        success = initialize_database()
        
        if success:
            print("✅ Database initialized successfully!")
            
            # Test connection
            if test_connection():
                print("✅ Database connection test passed!")
                
                # Show database info
                info = get_database_info()
                print(f"📊 Database Info:")
                print(f"   Path: {info['database_path']}")
                print(f"   Size: {info['database_size_mb']} MB")
                print(f"   Tables: {info['tables']}")
                
            else:
                print("❌ Database connection test failed!")
                return False
        else:
            print("❌ Database initialization failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error during initialization: {str(e)}")
        return False
    
    print("\n🎉 Database setup complete! You can now start the application.")
    return True

if __name__ == "__main__":
    main()
