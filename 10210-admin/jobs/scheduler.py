"""
Campaign Scheduler - Background task management and automation
Handles campaign scheduling, monitoring, and automated operations
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from database.connection import get_db
from database.models import Campaign, Delivery
from jobs.models import CampaignStatus
from jobs.processor import message_processor
import json

logger = logging.getLogger(__name__)

class CampaignScheduler:
    """Background scheduler for campaign management"""
    
    def __init__(self):
        self.running = False
        self.scheduler_task = None
        self.check_interval = 30  # seconds
        
    async def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("🕒 Campaign scheduler started")
    
    async def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return
        
        self.running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 Campaign scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        try:
            while self.running:
                try:
                    # Check for scheduled campaigns to start
                    await self._check_scheduled_campaigns()
                    
                    # Check for campaigns to start
                    await self._check_pending_campaigns()
                    
                    # Check for queued campaigns (sequential execution)
                    await self._check_queued_campaigns()
                    
                    # Monitor active campaigns
                    await self._monitor_active_campaigns()
                    
                    # Cleanup completed campaigns
                    await self._cleanup_old_data()
                    
                    # Health checks
                    await self._perform_health_checks()
                    
                except Exception as e:
                    logger.error(f"Scheduler loop error: {str(e)}")
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
        except Exception as e:
            logger.error(f"Scheduler loop crashed: {str(e)}")
    
    async def _check_scheduled_campaigns(self):
        """Check for scheduled campaigns that should start now"""
        try:
            with get_db() as db:
                # Find scheduled campaigns that should start
                now = datetime.utcnow()
                scheduled_campaigns = db.query(Campaign).filter(
                    Campaign.is_scheduled == True,
                    Campaign.scheduled_start_time <= now,
                    Campaign.status.in_([CampaignStatus.CREATED.value, CampaignStatus.SCHEDULED.value])
                ).all()
                
                # Check if any campaigns are currently running
                running_campaigns = db.query(Campaign).filter(
                    Campaign.status == CampaignStatus.RUNNING.value
                ).count()
                
                for i, campaign in enumerate(scheduled_campaigns):
                    logger.info(f"Processing scheduled campaign: {campaign.id} - {campaign.name}")
                    
                    # Clear scheduled flag since time has arrived
                    campaign.is_scheduled = False
                    campaign.scheduled_start_time = None
                    
                    if running_campaigns == 0 and i == 0:
                        # No campaigns running, start the first scheduled one
                        logger.info(f"Starting scheduled campaign: {campaign.id} - {campaign.name}")
                        
                        # DISABLED: Warmer pausing - better to keep warmers running for natural activity
                        # await self._pause_warmers_for_campaign(campaign)
                        logger.info(f"Starting scheduled campaign {campaign.id} - warmers continue running")
                        
                        # Update campaign status to running
                        campaign.status = CampaignStatus.RUNNING.value
                        campaign.started_at = datetime.utcnow()
                        db.commit()
                        
                        # Start processing
                        await message_processor.start_campaign_processing(campaign.id)
                        
                        # Mark that we now have a running campaign
                        running_campaigns = 1
                    else:
                        # Campaign is running or this is not the first scheduled campaign, queue this one
                        logger.info(f"Queueing scheduled campaign: {campaign.id} - {campaign.name}")
                        
                        # Calculate queue position
                        queued_count = db.query(Campaign).filter(
                            Campaign.status == CampaignStatus.QUEUED.value
                        ).count()
                        
                        campaign.status = CampaignStatus.QUEUED.value
                        campaign.queue_position = queued_count + 1
                        db.commit()
                    
        except Exception as e:
            logger.error(f"Error checking scheduled campaigns: {str(e)}")
    
    async def _check_queued_campaigns(self):
        """Check for queued campaigns to start after current one completes"""
        try:
            with get_db() as db:
                # Check if any campaigns are currently running
                running_campaigns = db.query(Campaign).filter(
                    Campaign.status == CampaignStatus.RUNNING.value
                ).count()
                
                # If no campaigns running, start the next queued one
                if running_campaigns == 0:
                    next_campaign = db.query(Campaign).filter(
                        Campaign.status == CampaignStatus.QUEUED.value
                    ).order_by(Campaign.queue_position, Campaign.id).first()  # Process by queue position, then ID
                    
                    if next_campaign:
                        logger.info(f"Starting queued campaign: {next_campaign.id} - {next_campaign.name}")
                        
                        # DISABLED: Warmer pausing - better to keep warmers running for natural activity
                        # await self._pause_warmers_for_campaign(next_campaign)
                        logger.info(f"Starting queued campaign {next_campaign.id} - warmers continue running")
                        
                        # Update campaign status
                        next_campaign.status = CampaignStatus.RUNNING.value
                        next_campaign.started_at = datetime.utcnow()
                        next_campaign.queue_position = None  # Clear queue position
                        db.commit()
                        
                        # Start processing
                        await message_processor.start_campaign_processing(next_campaign.id)
                        
                        # Update queue positions for remaining queued campaigns
                        remaining_queued = db.query(Campaign).filter(
                            Campaign.status == CampaignStatus.QUEUED.value
                        ).order_by(Campaign.queue_position, Campaign.id).all()
                        
                        for i, campaign in enumerate(remaining_queued, 1):
                            campaign.queue_position = i
                        db.commit()
                        
        except Exception as e:
            logger.error(f"Error checking queued campaigns: {str(e)}")
    
    async def _pause_warmers_for_campaign(self, campaign: Campaign):
        """Pause all active warmers before starting a campaign"""
        try:
            logger.info(f"=== PAUSING WARMERS FOR CAMPAIGN {campaign.id} ===")
            # Import warmer models only if available
            try:
                from warmer.models import WarmerSession
                from warmer.orchestrator import warmer_orchestrator
                
                with get_db() as db:
                    # Find all active warmers for this user
                    active_warmers = db.query(WarmerSession).filter(
                        WarmerSession.user_id == campaign.user_id,  # Only pause user's warmers
                        WarmerSession.status.in_(['warming', 'active'])
                    ).all()
                    
                    logger.info(f"Found {len(active_warmers)} active warmers to pause")
                    
                    paused_warmer_ids = []
                    for warmer in active_warmers:
                        logger.info(f"Pausing warmer {warmer.id} for campaign {campaign.id}")
                        
                        # Pause the warmer
                        warmer.status = 'paused_for_campaign'
                        warmer.paused_reason = f"Paused for campaign: {campaign.name}"
                        paused_warmer_ids.append(warmer.id)
                        
                        # Stop the warmer processing
                        if hasattr(warmer_orchestrator, 'pause_warmer'):
                            await warmer_orchestrator.pause_warmer(warmer.id)
                    
                    # Store paused warmer IDs in campaign metadata
                    if paused_warmer_ids:
                        campaign.auto_paused_warmers = json.dumps(paused_warmer_ids)
                    
                    db.commit()
                    logger.info(f"Paused {len(paused_warmer_ids)} warmers for campaign {campaign.id}")
                    
            except ImportError:
                logger.debug("Warmer module not available, skipping warmer pause")
                
        except Exception as e:
            logger.error(f"Error pausing warmers for campaign {campaign.id}: {str(e)}")
    
    async def _resume_warmers_after_campaign(self, campaign: Campaign):
        """Resume warmers that were paused for a campaign"""
        try:
            if not campaign.auto_paused_warmers:
                return
                
            # Check if there are other queued or running campaigns
            with get_db() as db:
                # Check for any campaigns that are running or queued
                active_campaigns = db.query(Campaign).filter(
                    Campaign.id != campaign.id,
                    Campaign.status.in_([
                        CampaignStatus.RUNNING.value,
                        CampaignStatus.QUEUED.value
                    ])
                ).count()
                
                if active_campaigns > 0:
                    logger.info(f"Not resuming warmers - {active_campaigns} campaigns still active/queued")
                    return
                
            # Import warmer models only if available
            try:
                from warmer.models import WarmerSession
                from warmer.orchestrator import warmer_orchestrator
                
                paused_warmer_ids = json.loads(campaign.auto_paused_warmers)
                
                with get_db() as db:
                    resumed_count = 0
                    for warmer_id in paused_warmer_ids:
                        warmer = db.query(WarmerSession).filter(
                            WarmerSession.id == warmer_id
                        ).first()
                        
                        if warmer and warmer.status == 'paused_for_campaign':
                            logger.info(f"Resuming warmer {warmer.id} after campaign {campaign.id}")
                            
                            # Resume the warmer
                            warmer.status = 'warming'
                            warmer.paused_reason = None
                            resumed_count += 1
                            
                            # Restart the warmer processing
                            if hasattr(warmer_orchestrator, 'resume_warmer'):
                                await warmer_orchestrator.resume_warmer(warmer.id)
                    
                    # Clear the paused warmers list
                    campaign.auto_paused_warmers = None
                    db.commit()
                    
                    logger.info(f"Resumed {resumed_count} warmers after campaign {campaign.id}")
                    
            except ImportError:
                logger.debug("Warmer module not available, skipping warmer resume")
                
        except Exception as e:
            logger.error(f"Error resuming warmers after campaign {campaign.id}: {str(e)}")
    
    async def _check_pending_campaigns(self):
        """Check for campaigns that should be started"""
        try:
            with get_db() as db:
                # Find campaigns in RUNNING status that aren't being processed
                pending_campaigns = db.query(Campaign).filter(
                    Campaign.status == CampaignStatus.RUNNING.value
                ).all()
                
                for campaign in pending_campaigns:
                    # Check if already being processed
                    if campaign.id not in message_processor.active_campaigns:
                        logger.info(f"Starting pending campaign: {campaign.id}")
                        
                        # Start processing
                        success = await message_processor.start_campaign_processing(campaign.id)
                        if not success:
                            # Mark as failed if can't start
                            campaign.status = CampaignStatus.FAILED.value
                            campaign.completed_at = datetime.utcnow()
                            db.commit()
                            
        except Exception as e:
            logger.error(f"Error checking pending campaigns: {str(e)}")
    
    async def _monitor_active_campaigns(self):
        """Monitor active campaigns for issues"""
        try:
            active_campaign_ids = list(message_processor.active_campaigns.keys())
            
            with get_db() as db:
                for campaign_id in active_campaign_ids:
                    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                    if not campaign:
                        continue
                    
                    # Check if campaign should be paused (e.g., too many errors)
                    await self._check_campaign_health(campaign)
                    
                    # Check for stuck campaigns
                    await self._check_campaign_progress(campaign)
                    
        except Exception as e:
            logger.error(f"Error monitoring active campaigns: {str(e)}")
    
    async def _check_campaign_health(self, campaign: Campaign):
        """Check individual campaign health"""
        try:
            with get_db() as db:
                # Check error rate
                if campaign.processed_rows > 10:  # Only check after processing some rows
                    error_rate = (campaign.error_count / campaign.processed_rows) * 100
                    
                    if error_rate > 50:  # More than 50% errors
                        logger.warning(f"Campaign {campaign.id} has high error rate: {error_rate:.1f}%")
                        
                        # Pause campaign
                        campaign.status = CampaignStatus.PAUSED.value
                        db.commit()
                        
                        # Stop processing
                        await message_processor.stop_campaign_processing(campaign.id)
                        
                        logger.info(f"Campaign {campaign.id} paused due to high error rate")
                        
                        # Resume warmers if campaign was auto-paused
                        await self._resume_warmers_after_campaign(campaign)
                
                # Check if session is still working
                # TODO: Implement session health check
                
        except Exception as e:
            logger.error(f"Error checking campaign health {campaign.id}: {str(e)}")
    
    async def _check_campaign_progress(self, campaign: Campaign):
        """Check if campaign is making progress"""
        try:
            # Check if campaign has been running for too long without progress
            if campaign.started_at:
                running_time = datetime.utcnow() - campaign.started_at
                
                # If running for more than 1 hour with no progress
                if running_time > timedelta(hours=1) and campaign.processed_rows == 0:
                    logger.warning(f"Campaign {campaign.id} stuck - no progress in {running_time}")
                    
                    with get_db() as db:
                        campaign.status = CampaignStatus.FAILED.value
                        campaign.completed_at = datetime.utcnow()
                        db.commit()
                    
                    await message_processor.stop_campaign_processing(campaign.id)
                    
                    # Resume warmers after campaign failure
                    await self._resume_warmers_after_campaign(campaign)
                    
        except Exception as e:
            logger.error(f"Error checking campaign progress {campaign.id}: {str(e)}")
    
    async def _cleanup_old_data(self):
        """Cleanup old completed campaigns and data"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=7)  # Keep data for 7 days
            
            with get_db() as db:
                # Find old completed campaigns
                old_campaigns = db.query(Campaign).filter(
                    Campaign.status.in_([CampaignStatus.COMPLETED.value, CampaignStatus.FAILED.value]),
                    Campaign.completed_at < cutoff_date
                ).all()
                
                for campaign in old_campaigns:
                    # Delete old delivery records (keep campaign for stats)
                    old_deliveries = db.query(Delivery).filter(
                        Delivery.campaign_id == campaign.id,
                        Delivery.created_at < cutoff_date
                    ).delete()
                    
                    if old_deliveries > 0:
                        logger.info(f"Cleaned up {old_deliveries} old delivery records from campaign {campaign.id}")
                
                db.commit()
                
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    async def _perform_health_checks(self):
        """Perform system health checks"""
        try:
            # Check database health
            with get_db() as db:
                db.execute(text("SELECT 1")).fetchone()
            
            # Check message processor health
            processor_status = message_processor.get_processing_status()
            
            # Log health status periodically
            if datetime.utcnow().minute % 10 == 0:  # Every 10 minutes
                logger.info(f"Health check: DB ✅, Processor ✅ ({processor_status['total_active']} active)")
                
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            "running": self.running,
            "check_interval": self.check_interval,
            "active_campaigns": len(message_processor.active_campaigns),
            "processor_status": message_processor.get_processing_status()
        }

# Global scheduler instance
campaign_scheduler = CampaignScheduler()
