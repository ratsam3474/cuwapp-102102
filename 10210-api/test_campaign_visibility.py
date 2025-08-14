#!/usr/bin/env python3
"""
Test campaign visibility for nired user
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import get_db
from database.models import Campaign
from database.subscription_models import UserSubscription
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_ID = "user_3148o5aoIbt3PCENt4ZMHXfb2CO"  # nired user

def check_campaigns():
    """Check campaigns for the user"""
    try:
        with get_db() as db:
            # Get user info
            user = db.query(UserSubscription).filter(
                UserSubscription.user_id == USER_ID
            ).first()
            
            if user:
                logger.info(f"""
                User Info:
                - Email: {user.email}
                - Plan: {user.plan_type.value}
                - Total Campaigns Created: {user.total_campaigns}
                """)
            
            # Get all campaigns for this user
            campaigns = db.query(Campaign).filter(
                Campaign.user_id == USER_ID
            ).all()
            
            logger.info(f"\nFound {len(campaigns)} campaign(s) for this user:")
            
            for i, campaign in enumerate(campaigns, 1):
                logger.info(f"""
                Campaign {i}:
                - ID: {campaign.id}
                - Name: {campaign.name}
                - Status: {campaign.status}
                - Session: {campaign.session_name}
                - Messages Sent: {campaign.messages_sent if hasattr(campaign, 'messages_sent') else 'N/A'}
                - Created: {campaign.created_at}
                - User ID: {campaign.user_id}
                """)
            
            # Check campaigns without user_id (orphaned)
            orphaned = db.query(Campaign).filter(
                Campaign.user_id == None
            ).all()
            
            if orphaned:
                logger.warning(f"\n⚠️  Found {len(orphaned)} orphaned campaign(s) without user_id:")
                for campaign in orphaned[:5]:  # Show first 5
                    logger.warning(f"  - {campaign.name} (ID: {campaign.id})")
            
            return campaigns
            
    except Exception as e:
        logger.error(f"Error checking campaigns: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_api_endpoint():
    """Test the API endpoint directly"""
    import requests
    
    logger.info("\n" + "="*60)
    logger.info("Testing API Endpoint")
    logger.info("="*60)
    
    try:
        # Test getting campaigns via API
        response = requests.get(f"https://app.cuwapp.com/api/campaigns?user_id={USER_ID}")
        
        if response.status_code == 200:
            data = response.json()
            campaigns = data.get('data', [])
            logger.info(f"\nAPI returned {len(campaigns)} campaign(s)")
            
            for campaign in campaigns[:3]:  # Show first 3
                logger.info(f"""
                - {campaign.get('name')} (Status: {campaign.get('status')})
                  ID: {campaign.get('id')}
                  User ID: {campaign.get('user_id')}
                """)
        else:
            logger.error(f"API Error: {response.status_code}")
            logger.error(response.text[:500])
            
    except Exception as e:
        logger.error(f"Error testing API: {e}")

def main():
    """Main function"""
    logger.info("="*60)
    logger.info("Campaign Visibility Test for nired038@gmail.com")
    logger.info("="*60)
    
    # Check database directly
    campaigns = check_campaigns()
    
    # Test API endpoint
    test_api_endpoint()
    
    if not campaigns:
        logger.info("""
        ========================================
        No campaigns found for this user.
        
        Possible issues:
        1. Campaigns created without user_id
        2. Campaigns not being saved properly
        3. User_id not being passed during creation
        ========================================
        """)
    else:
        logger.info("""
        ========================================
        ✅ Campaigns found in database!
        
        If they're not showing in UI:
        1. Check if loadCampaigns() is being called
        2. Check browser console for errors
        3. Verify user_id is being sent in API calls
        ========================================
        """)

if __name__ == "__main__":
    main()