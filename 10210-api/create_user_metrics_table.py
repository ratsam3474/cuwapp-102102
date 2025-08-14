#!/usr/bin/env python3
"""
Create the missing user_metrics table
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from database.user_metrics import UserMetrics
from database.connection import Base

def main():
    # Create engine directly
    db_path = "data/wagent.db"
    engine = create_engine(f"sqlite:///{db_path}")
    
    # Create only the user_metrics table
    UserMetrics.__table__.create(engine, checkfirst=True)
    print("✅ user_metrics table created successfully!")

if __name__ == "__main__":
    main()