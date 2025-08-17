#!/usr/bin/env python3
"""
Fix production warmer tables issue
This script checks both databases and ensures warmer tables exist in the correct location
"""

import logging
import sqlite3
import os
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_and_fix_warmer_tables():
    """Check and fix warmer tables in production"""
    
    # Check both possible database locations
    wagent_db = os.path.join(os.path.dirname(__file__), "data", "wagent.db")
    whatsapp_db = os.path.join(os.path.dirname(__file__), "whatsapp_sessions.db")
    
    logger.info("=" * 60)
    logger.info("PRODUCTION WARMER DATABASE CHECK")
    logger.info("=" * 60)
    
    # 1. Check wagent.db (correct location)
    logger.info(f"\n1. Checking main database: {wagent_db}")
    if os.path.exists(wagent_db):
        logger.info(f"   ✓ File exists (size: {os.path.getsize(wagent_db)} bytes)")
        
        conn = sqlite3.connect(wagent_db)
        cursor = conn.cursor()
        
        # Check for warmer tables
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'warmer_%'
            ORDER BY name
        """)
        warmer_tables = cursor.fetchall()
        
        if warmer_tables:
            logger.info(f"   ✓ Found {len(warmer_tables)} warmer tables:")
            for table in warmer_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                logger.info(f"      - {table[0]}: {count} records")
            
            # Check if archive columns exist
            cursor.execute("PRAGMA table_info(warmer_sessions)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            has_archive = 'is_archived' in column_names and 'archived_at' in column_names
            if has_archive:
                logger.info("   ✓ Archive columns exist")
            else:
                logger.info("   ✗ Archive columns missing - run add_warmer_archive.py")
        else:
            logger.info("   ✗ No warmer tables found - need to create them")
            
        conn.close()
    else:
        logger.info(f"   ✗ File does not exist!")
        os.makedirs(os.path.dirname(wagent_db), exist_ok=True)
        logger.info(f"   ✓ Created directory: {os.path.dirname(wagent_db)}")
    
    # 2. Check whatsapp_sessions.db (incorrect location)
    logger.info(f"\n2. Checking legacy database: {whatsapp_db}")
    if os.path.exists(whatsapp_db):
        size = os.path.getsize(whatsapp_db)
        logger.info(f"   ✓ File exists (size: {size} bytes)")
        
        if size == 0:
            logger.info("   ℹ File is empty (this is OK - not used)")
        else:
            conn = sqlite3.connect(whatsapp_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table'
                ORDER BY name
            """)
            tables = cursor.fetchall()
            
            if tables:
                logger.info(f"   ⚠ Contains {len(tables)} tables (should be empty):")
                for table in tables:
                    logger.info(f"      - {table[0]}")
                logger.info("   ⚠ This database should not be used!")
            
            conn.close()
    else:
        logger.info("   ✓ File does not exist (this is OK)")
    
    # 3. Check database connection configuration
    logger.info("\n3. Checking database configuration:")
    
    connection_file = os.path.join(os.path.dirname(__file__), "database", "connection.py")
    if os.path.exists(connection_file):
        with open(connection_file, 'r') as f:
            content = f.read()
            if 'wagent.db' in content:
                logger.info("   ✓ Database connection correctly configured to use wagent.db")
            else:
                logger.info("   ✗ Database connection might be using wrong database!")
    
    # 4. Summary and recommendations
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY & RECOMMENDATIONS")
    logger.info("=" * 60)
    
    recommendations = []
    
    if not os.path.exists(wagent_db):
        recommendations.append("1. Create data/wagent.db database")
    elif not warmer_tables:
        recommendations.append("1. Run migration to create warmer tables in wagent.db")
    elif not has_archive:
        recommendations.append("1. Run add_warmer_archive.py to add archive columns")
    
    if os.path.exists(whatsapp_db) and os.path.getsize(whatsapp_db) > 0:
        recommendations.append("2. Remove or empty whatsapp_sessions.db (not used)")
    
    if recommendations:
        logger.info("\nActions needed:")
        for rec in recommendations:
            logger.info(f"   {rec}")
    else:
        logger.info("\n✓ Everything looks good! Warmer system should work.")
    
    return len(recommendations) == 0

if __name__ == "__main__":
    logger.info("Starting production warmer database check...")
    success = check_and_fix_warmer_tables()
    
    if success:
        logger.info("\n✅ All checks passed!")
        sys.exit(0)
    else:
        logger.info("\n⚠️  Some issues found - see recommendations above")
        sys.exit(1)