"""
API endpoints for file upload and campaign processing
Handles CSV/Excel uploads, data validation, and campaign management
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional, Any
import json
import logging
import os

# Import Phase 2 components
try:
    from utils.file_handler import FileHandler
    from utils.validation import DataValidator, BusinessRuleValidator
    from jobs.processor import message_processor
    from jobs.scheduler import campaign_scheduler
    from jobs.models import CampaignCreate, MessageSample, MessageMode
    PHASE_2_AVAILABLE = True
except ImportError:
    PHASE_2_AVAILABLE = False

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

if PHASE_2_AVAILABLE:
    
    # Initialize components
    file_handler = FileHandler()
    data_validator = DataValidator()
    business_validator = BusinessRuleValidator()
    
    @router.post("/upload")
    async def upload_campaign_file(
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = None
    ):
        """Upload and validate campaign file (CSV/Excel)"""
        try:
            # Validate file
            if not file.filename:
                raise HTTPException(status_code=400, detail="No filename provided")
            
            # Check file extension
            allowed_extensions = {'.csv', '.xlsx', '.xls'}
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in allowed_extensions:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
                )
            
            # Read file content
            file_content = await file.read()
            
            # Check file size (50MB limit)
            if len(file_content) > 50 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="File too large. Maximum size: 50MB")
            
            # Save file
            file_path = file_handler.save_uploaded_file(file_content, file.filename)
            
            # Validate file
            validation_result = file_handler.validate_file(file_path)
            if not validation_result["valid"]:
                # Remove invalid file
                try:
                    os.remove(file_path)
                except:
                    pass
                raise HTTPException(status_code=400, detail=validation_result["error"])
            
            file_info = validation_result["file_info"]
            
            # Auto-detect column mapping
            from utils.file_handler import DataPreprocessor
            suggested_mapping = DataPreprocessor.detect_column_mapping(file_info["headers"])
            
            return {
                "success": True,
                "data": {
                    "file_path": file_path,
                    "filename": file.filename,
                    "file_size": validation_result["file_size"],
                    "total_rows": file_info["total_rows"],
                    "headers": file_info["headers"],
                    "sample_data": file_info["sample_data"],
                    "suggested_mapping": suggested_mapping,
                    "processor_type": validation_result["processor_type"]
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"File upload error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    @router.post("/validate")
    async def validate_campaign_data(
        file_path: str = Form(...),
        column_mapping: str = Form(...),  # JSON string
        start_row: int = Form(1),
        end_row: Optional[int] = Form(None)
    ):
        """Validate campaign data with column mapping"""
        try:
            # Parse column mapping
            try:
                mapping = json.loads(column_mapping)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in column_mapping")
            
            # Validate file exists
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="File not found")
            
            # Load data
            processor = file_handler.get_processor(file_path)
            data = processor.read_data(file_path, start_row, end_row)
            
            if not data:
                raise HTTPException(status_code=400, detail="No data found in specified range")
            
            # Validate data
            validation_result = data_validator.validate_campaign_data(data, mapping)
            
            # Generate preview
            from utils.file_handler import DataPreprocessor
            preview_data = DataPreprocessor.preview_processed_data(data, mapping, limit=10)
            
            return {
                "success": True,
                "data": {
                    "validation_result": validation_result,
                    "preview_data": preview_data,
                    "data_range": {
                        "start_row": start_row,
                        "end_row": end_row,
                        "total_rows": len(data)
                    }
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Data validation error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")
    
    @router.post("/create-campaign")
    async def create_campaign_with_file(
        campaign_name: str = Form(...),
        session_name: str = Form(...),
        file_path: str = Form(...),
        column_mapping: str = Form(...),
        message_mode: str = Form("single"),
        message_samples: str = Form("[]"),  # JSON array
        use_csv_samples: bool = Form(False),
        start_row: int = Form(1),
        end_row: Optional[int] = Form(None),
        delay_seconds: int = Form(5),
        retry_attempts: int = Form(3),
        max_daily_messages: int = Form(1000),
        exclude_my_contacts: bool = Form(False),
        exclude_previous_conversations: bool = Form(False)
    ):
        """Create campaign with uploaded file"""
        try:
            # Parse message samples
            try:
                samples_data = json.loads(message_samples)
                samples = [MessageSample(text=sample["text"]) for sample in samples_data]
            except (json.JSONDecodeError, KeyError) as e:
                raise HTTPException(status_code=400, detail=f"Invalid message samples: {str(e)}")
            
            # Parse column mapping
            try:
                mapping = json.loads(column_mapping)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in column_mapping")
            
            # Validate file and data
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="File not found")
            
            # Load data to get total rows
            processor = file_handler.get_processor(file_path)
            data = processor.read_data(file_path, start_row, end_row)
            total_rows = len(data)
            
            # Validate business rules
            campaign_data = {
                "total_rows": total_rows,
                "delay_seconds": delay_seconds,
                "max_daily_messages": max_daily_messages,
                "session_name": session_name
            }
            
            business_validation = business_validator.validate_campaign_settings(campaign_data)
            if not business_validation["valid"]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Business rule validation failed: {'; '.join(business_validation['errors'])}"
                )
            
            # Create campaign
            from jobs.manager import CampaignManager
            campaign_manager = CampaignManager()
            
            campaign_create = CampaignCreate(
                name=campaign_name,
                session_name=session_name,
                file_path=file_path,
                column_mapping=mapping,  # Add column mapping here
                start_row=start_row,
                end_row=end_row,
                message_mode=MessageMode(message_mode),
                message_samples=samples,
                use_csv_samples=use_csv_samples,
                delay_seconds=delay_seconds,
                retry_attempts=retry_attempts,
                max_daily_messages=max_daily_messages,
                exclude_my_contacts=exclude_my_contacts,
                exclude_previous_conversations=exclude_previous_conversations
            )
            
            campaign = campaign_manager.create_campaign(campaign_create)
            
            # Update total rows
            from jobs.models import CampaignUpdate
            update_data = CampaignUpdate(total_rows=total_rows)
            campaign_manager.update_campaign(campaign.id, update_data)
            
            return {
                "success": True,
                "data": campaign.dict(),
                "business_validation": business_validation
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Campaign creation error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Campaign creation failed: {str(e)}")
    
    @router.post("/campaigns/{campaign_id}/process")
    async def start_campaign_processing(campaign_id: int, background_tasks: BackgroundTasks):
        """Start campaign processing in background"""
        try:
            # Start processing
            success = await message_processor.start_campaign_processing(campaign_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"Campaign {campaign_id} processing started",
                    "campaign_id": campaign_id
                }
            else:
                raise HTTPException(status_code=400, detail="Failed to start campaign processing")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Campaign processing start error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Processing start failed: {str(e)}")
    
    @router.post("/campaigns/{campaign_id}/stop-processing")
    async def stop_campaign_processing(campaign_id: int):
        """Stop campaign processing"""
        try:
            success = await message_processor.stop_campaign_processing(campaign_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"Campaign {campaign_id} processing stopped"
                }
            else:
                raise HTTPException(status_code=400, detail="Campaign is not being processed")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Campaign processing stop error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Processing stop failed: {str(e)}")
    
    @router.get("/campaigns/{campaign_id}/deliveries")
    async def get_campaign_deliveries(
        campaign_id: int,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None
    ):
        """Get campaign delivery records"""
        try:
            from database.connection import get_db
            from database.models import Delivery
            
            with get_db() as db:
                query = db.query(Delivery).filter(Delivery.campaign_id == campaign_id)
                
                if status:
                    query = query.filter(Delivery.status == status)
                
                deliveries = query.offset(offset).limit(limit).all()
                
                return {
                    "success": True,
                    "data": [delivery.to_dict() for delivery in deliveries]
                }
                
        except Exception as e:
            logger.error(f"Error getting deliveries: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/campaigns/{campaign_id}/analytics")
    async def get_campaign_analytics(campaign_id: int):
        """Get campaign analytics and sample performance"""
        try:
            from database.connection import get_db
            from database.models import CampaignAnalytics
            
            with get_db() as db:
                analytics = db.query(CampaignAnalytics).filter(
                    CampaignAnalytics.campaign_id == campaign_id
                ).all()
                
                return {
                    "success": True,
                    "data": [analytic.to_dict() for analytic in analytics]
                }
                
        except Exception as e:
            logger.error(f"Error getting analytics: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/processing/status")
    async def get_processing_status():
        """Get current processing status"""
        try:
            processor_status = message_processor.get_processing_status()
            scheduler_status = campaign_scheduler.get_scheduler_status()
            
            return {
                "success": True,
                "data": {
                    "processor": processor_status,
                    "scheduler": scheduler_status
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting processing status: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/scheduler/start")
    async def start_scheduler():
        """Start the campaign scheduler"""
        try:
            await campaign_scheduler.start()
            return {
                "success": True,
                "message": "Scheduler started"
            }
        except Exception as e:
            logger.error(f"Error starting scheduler: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/scheduler/stop")
    async def stop_scheduler():
        """Stop the campaign scheduler"""
        try:
            await campaign_scheduler.stop()
            return {
                "success": True,
                "message": "Scheduler stopped"
            }
        except Exception as e:
            logger.error(f"Error stopping scheduler: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

else:
    # Phase 2 not available - provide error endpoints
    @router.post("/upload")
    async def upload_not_available():
        raise HTTPException(
            status_code=503,
            detail="File upload not available. Please install Phase 2 dependencies."
        )
