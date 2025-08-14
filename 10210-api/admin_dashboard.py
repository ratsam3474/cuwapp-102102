#!/usr/bin/env python3
"""
Admin Dashboard for CuWhapp
Runs on port 8001 for internal admin management
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta, timezone
import httpx
import os
import docker
from typing import List, Dict, Optional
from pydantic import BaseModel
import logging
from database.connection import get_db_dependency, init_database
from database.subscription_models import UserSubscription, PlanType, SubscriptionStatus
from database.models import Campaign
from warmer.models import WarmerContact, WarmerSession
from sqlalchemy import func, and_, desc
from sqlalchemy.orm import Session
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database on startup using lifespan
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database connection on startup"""
    init_database()
    logger.info("Admin dashboard started - database initialized")
    yield
    logger.info("Admin dashboard shutting down")

# FastAPI app initialization with lifespan
app = FastAPI(title="CuWhapp Admin Dashboard", version="1.0.0", lifespan=lifespan)

# Mount static files for AdminLTE assets
app.mount("/static", StaticFiles(directory="admin_static"), name="static")

# Templates directory for AdminLTE views
templates = Jinja2Templates(directory="admin_templates")

# Clerk API configuration
CLERK_API_KEY = os.getenv("CLERK_API_KEY", "sk_test_dummy_key")
CLERK_API_URL = "https://api.clerk.dev/v1"

# Docker client for container management
try:
    docker_client = docker.from_env()
except:
    docker_client = None
    logger.warning("Docker client could not be initialized")

# Admin authentication (simple token for now)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "admin_secret_token_2024")

def verify_admin_token(request: Request):
    """Verify admin authentication token"""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    return True

# Pydantic models
class UserStats(BaseModel):
    user_id: str
    email: str
    username: str
    plan_type: str
    status: str
    messages_sent: int
    campaigns_count: int
    contacts_count: int
    current_sessions: int
    max_sessions: int
    last_activity: Optional[datetime]

class ContainerInfo(BaseModel):
    container_id: str
    user_id: str
    name: str
    status: str
    cpu_usage: float
    memory_usage: float
    created_at: datetime

class SystemStats(BaseModel):
    total_users: int
    active_users: int
    total_campaigns: int
    active_campaigns: int
    total_messages_sent: int
    total_revenue: float
    docker_containers: int
    total_warmer_minutes: float
    active_warmer_sessions: int
    total_warmer_sessions: int
    system_cpu: float
    system_memory: float

@app.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Main admin dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "CuWhapp Admin Dashboard"
    })

@app.get("/api/stats/overview")
async def get_overview_stats(db: Session = Depends(get_db_dependency)):
    """Get system overview statistics"""
    try:
        # Get user statistics
        total_users = db.query(UserSubscription).count()
        active_users = db.query(UserSubscription).filter(
            UserSubscription.status == SubscriptionStatus.ACTIVE
        ).count()
        
        # Get campaign statistics
        total_campaigns = db.query(Campaign).count()
        active_campaigns = db.query(Campaign).filter(
            Campaign.status.in_(['running', 'queued', 'scheduled'])
        ).count()
        
        # Get message statistics (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        total_messages = db.query(func.sum(UserSubscription.messages_sent_this_month)).scalar() or 0
        
        # Get WhatsApp Warmer statistics
        total_warmer_minutes = db.query(func.sum(WarmerSession.total_duration_minutes)).scalar() or 0.0
        active_warmer_sessions = db.query(WarmerSession).filter(
            WarmerSession.status == 'warming'
        ).count()
        total_warmer_sessions = db.query(WarmerSession).count()
        
        # Calculate revenue
        revenue_by_plan = {
            PlanType.STARTER: 7,
            PlanType.HOBBY: 20,
            PlanType.PRO: 45,
            PlanType.PREMIUM: 99
        }
        
        total_revenue = 0
        for plan_type, price in revenue_by_plan.items():
            count = db.query(UserSubscription).filter(
                UserSubscription.plan_type == plan_type,
                UserSubscription.status == SubscriptionStatus.ACTIVE
            ).count()
            total_revenue += count * price
        
        # Get Docker container stats
        container_count = 0
        if docker_client:
            containers = docker_client.containers.list(all=True)
            container_count = len([c for c in containers if 'cuwhapp' in c.name.lower()])
        
        return SystemStats(
            total_users=total_users,
            active_users=active_users,
            total_campaigns=total_campaigns,
            active_campaigns=active_campaigns,
            total_messages_sent=int(total_messages),
            total_revenue=total_revenue,
            docker_containers=container_count,
            total_warmer_minutes=round(total_warmer_minutes, 2),
            active_warmer_sessions=active_warmer_sessions,
            total_warmer_sessions=total_warmer_sessions,
            system_cpu=0.0,  # Will be populated by system monitoring
            system_memory=0.0  # Will be populated by system monitoring
        )
    except Exception as e:
        logger.error(f"Error getting overview stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users", response_model=List[UserStats])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    plan_filter: Optional[str] = None,
    db: Session = Depends(get_db_dependency)
):
    """Get all users with their statistics"""
    try:
        query = db.query(UserSubscription)
        
        if plan_filter:
            query = query.filter(UserSubscription.plan_type == PlanType(plan_filter))
        
        users = query.offset(skip).limit(limit).all()
        
        user_stats = []
        for user in users:
            # Get campaign count for user
            campaign_count = db.query(Campaign).filter(
                Campaign.user_id == user.user_id
            ).count()
            
            # Get contact count for user
            contact_count = db.query(WarmerContact).filter(
                WarmerContact.user_id == user.user_id
            ).count()
            
            # Get last activity
            last_campaign = db.query(Campaign).filter(
                Campaign.user_id == user.user_id
            ).order_by(desc(Campaign.updated_at)).first()
            
            last_activity = last_campaign.updated_at if last_campaign else user.updated_at
            
            user_stats.append(UserStats(
                user_id=user.user_id,
                email=user.email,
                username=user.username,
                plan_type=user.plan_type.value,
                status=user.status.value,
                messages_sent=user.messages_sent_this_month,
                campaigns_count=campaign_count,
                contacts_count=contact_count,
                current_sessions=user.current_sessions,
                max_sessions=user.max_sessions,
                last_activity=last_activity
            ))
        
        return user_stats
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/{user_id}")
async def get_user_details(user_id: str, db: Session = Depends(get_db_dependency)):
    """Get detailed information about a specific user"""
    try:
        user = db.query(UserSubscription).filter(
            UserSubscription.user_id == user_id
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get all campaigns
        campaigns = db.query(Campaign).filter(
            Campaign.user_id == user_id
        ).order_by(desc(Campaign.created_at)).limit(10).all()
        
        # Get warmer sessions
        warmer_sessions = db.query(WarmerSession).filter(
            WarmerSession.user_id == user_id
        ).order_by(desc(WarmerSession.created_at)).limit(10).all()
        
        # Get Clerk user data if available
        clerk_data = None
        if CLERK_API_KEY != "sk_test_dummy_key":
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{CLERK_API_URL}/users/{user_id}",
                        headers={"Authorization": f"Bearer {CLERK_API_KEY}"}
                    )
                    if response.status_code == 200:
                        clerk_data = response.json()
            except:
                pass
        
        return {
            "subscription": user,
            "campaigns": campaigns,
            "warmer_sessions": warmer_sessions,
            "clerk_data": clerk_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/{user_id}/update-plan")
async def update_user_plan(
    user_id: str,
    new_plan: str,
    db: Session = Depends(get_db_dependency),
    _: bool = Depends(verify_admin_token)
):
    """Update a user's subscription plan"""
    try:
        user = db.query(UserSubscription).filter(
            UserSubscription.user_id == user_id
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update plan
        user.plan_type = PlanType(new_plan)
        user.updated_at = datetime.now(timezone.utc)
        
        # Update limits based on new plan
        from database.subscription_models import plan_limits
        limits = plan_limits.get(PlanType(new_plan))
        if limits:
            user.max_sessions = limits[0] if limits[0] != -1 else 999999
            user.max_messages_per_month = limits[1] if limits[1] != -1 else 999999
            user.max_contacts_export = limits[2] if limits[2] != -1 else 999999
            user.max_campaigns = limits[3] if limits[3] != -1 else 999999
            user.warmer_duration_hours = limits[4] if limits[4] != -1 else 999999
        
        db.commit()
        
        return {"message": f"User plan updated to {new_plan}"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/containers", response_model=List[ContainerInfo])
async def get_docker_containers():
    """Get information about Docker containers"""
    if not docker_client:
        return []
    
    try:
        containers = docker_client.containers.list(all=True)
        container_info = []
        
        for container in containers:
            if 'cuwhapp' in container.name.lower() or 'waha' in container.name.lower():
                # Get container stats
                try:
                    stats = container.stats(stream=False)
                    
                    # Calculate CPU usage
                    cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                               stats['precpu_stats']['cpu_usage']['total_usage']
                    system_delta = stats['cpu_stats'].get('system_cpu_usage', 0) - \
                                  stats['precpu_stats'].get('system_cpu_usage', 0)
                    cpu_usage = (cpu_delta / system_delta) * 100 if system_delta > 0 else 0
                    
                    # Calculate memory usage
                    memory_usage = stats['memory_stats'].get('usage', 0) / (1024 * 1024)  # Convert to MB
                except Exception as e:
                    logger.warning(f"Could not get stats for container {container.name}: {e}")
                    cpu_usage = 0
                    memory_usage = 0
                
                # Extract user_id from container labels or name
                user_id = container.labels.get('user_id', 'unknown')
                if user_id == 'unknown':
                    # Try to extract from container name
                    parts = container.name.split('_')
                    if len(parts) > 1:
                        user_id = parts[1]
                
                container_info.append(ContainerInfo(
                    container_id=container.id[:12],
                    user_id=user_id,
                    name=container.name,
                    status=container.status,
                    cpu_usage=round(cpu_usage, 2),
                    memory_usage=round(memory_usage, 2),
                    created_at=datetime.fromisoformat(
                        container.attrs['Created'].replace('Z', '+00:00')
                    )
                ))
        
        return container_info
    except Exception as e:
        logger.error(f"Error getting container info: {e}")
        return []

@app.post("/api/containers/{container_id}/restart")
async def restart_container(
    container_id: str,
    _: bool = Depends(verify_admin_token)
):
    """Restart a Docker container"""
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker not available")
    
    try:
        container = docker_client.containers.get(container_id)
        container.restart()
        return {"message": f"Container {container_id} restarted successfully"}
    except Exception as e:
        logger.error(f"Error restarting container: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/revenue")
async def get_revenue_analytics(
    period: str = "month",  # day, week, month, year
    db: Session = Depends(get_db_dependency)
):
    """Get revenue analytics data"""
    try:
        # Define period
        if period == "day":
            start_date = datetime.now(timezone.utc) - timedelta(days=1)
        elif period == "week":
            start_date = datetime.now(timezone.utc) - timedelta(weeks=1)
        elif period == "year":
            start_date = datetime.now(timezone.utc) - timedelta(days=365)
        else:  # month
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Get subscriptions by plan
        revenue_by_plan = {
            "starter": {"count": 0, "revenue": 0, "price": 7},
            "hobby": {"count": 0, "revenue": 0, "price": 20},
            "pro": {"count": 0, "revenue": 0, "price": 45},
            "premium": {"count": 0, "revenue": 0, "price": 99}
        }
        
        active_subs = db.query(UserSubscription).filter(
            UserSubscription.status == SubscriptionStatus.ACTIVE,
            UserSubscription.updated_at >= start_date
        ).all()
        
        for sub in active_subs:
            plan_name = sub.plan_type.value
            if plan_name in revenue_by_plan:
                revenue_by_plan[plan_name]["count"] += 1
                revenue_by_plan[plan_name]["revenue"] = \
                    revenue_by_plan[plan_name]["count"] * revenue_by_plan[plan_name]["price"]
        
        total_revenue = sum(p["revenue"] for p in revenue_by_plan.values())
        
        return {
            "period": period,
            "total_revenue": total_revenue,
            "revenue_by_plan": revenue_by_plan,
            "subscriber_count": len(active_subs)
        }
    except Exception as e:
        logger.error(f"Error getting revenue analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/usage")
async def get_usage_analytics(db: Session = Depends(get_db_dependency)):
    """Get system usage analytics"""
    try:
        # Messages sent by plan
        messages_by_plan = db.query(
            UserSubscription.plan_type,
            func.sum(UserSubscription.messages_sent_this_month)
        ).group_by(UserSubscription.plan_type).all()
        
        # Campaigns by status
        campaigns_by_status = db.query(
            Campaign.status,
            func.count(Campaign.id)
        ).group_by(Campaign.status).all()
        
        # Session usage
        session_usage = db.query(
            func.sum(UserSubscription.current_sessions),
            func.sum(UserSubscription.max_sessions)
        ).first()
        
        # Warmer usage statistics
        warmer_stats = db.query(
            func.count(WarmerSession.id),
            func.sum(WarmerSession.total_duration_minutes),
            func.sum(WarmerSession.total_messages_sent),
            func.sum(WarmerSession.total_groups_created)
        ).first()
        
        # Warmer usage by user
        warmer_by_user = db.query(
            WarmerSession.user_id,
            func.sum(WarmerSession.total_duration_minutes)
        ).group_by(WarmerSession.user_id).all()
        
        return {
            "messages_by_plan": {str(plan): count or 0 for plan, count in messages_by_plan},
            "campaigns_by_status": {status: count for status, count in campaigns_by_status},
            "session_usage": {
                "current": session_usage[0] or 0,
                "maximum": session_usage[1] or 0,
                "percentage": round((session_usage[0] or 0) / (session_usage[1] or 1) * 100, 2)
            },
            "warmer_usage": {
                "total_sessions": warmer_stats[0] or 0,
                "total_minutes": round(warmer_stats[1] or 0, 2),
                "total_messages": warmer_stats[2] or 0,
                "total_groups": warmer_stats[3] or 0,
                "minutes_by_user": {user: round(minutes or 0, 2) for user, minutes in warmer_by_user if user}
            }
        }
    except Exception as e:
        logger.error(f"Error getting usage analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/warmer")
async def get_warmer_analytics(db: Session = Depends(get_db_dependency)):
    """Get detailed WhatsApp Warmer analytics"""
    try:
        # Overall warmer statistics
        total_warmer_sessions = db.query(WarmerSession).count()
        active_warmers = db.query(WarmerSession).filter(
            WarmerSession.status == 'warming'
        ).count()
        
        # Total minutes across all users
        total_minutes = db.query(func.sum(WarmerSession.total_duration_minutes)).scalar() or 0.0
        
        # Messages and groups created
        total_messages = db.query(func.sum(WarmerSession.total_messages_sent)).scalar() or 0
        total_groups = db.query(func.sum(WarmerSession.total_groups_created)).scalar() or 0
        
        # Warmer usage by plan
        warmer_by_plan = db.query(
            UserSubscription.plan_type,
            func.count(WarmerSession.id),
            func.sum(WarmerSession.total_duration_minutes)
        ).join(
            WarmerSession, UserSubscription.user_id == WarmerSession.user_id
        ).group_by(UserSubscription.plan_type).all()
        
        # Top warmer users
        top_users = db.query(
            WarmerSession.user_id,
            UserSubscription.email,
            func.sum(WarmerSession.total_duration_minutes).label('total_minutes'),
            func.count(WarmerSession.id).label('session_count')
        ).join(
            UserSubscription, WarmerSession.user_id == UserSubscription.user_id
        ).group_by(
            WarmerSession.user_id, UserSubscription.email
        ).order_by(
            func.sum(WarmerSession.total_duration_minutes).desc()
        ).limit(10).all()
        
        # Calculate cost (assuming $0.001 per minute for example)
        cost_per_minute = 0.001  # $0.001 per minute
        total_cost = total_minutes * cost_per_minute
        
        return {
            "overview": {
                "total_sessions": total_warmer_sessions,
                "active_sessions": active_warmers,
                "total_minutes": round(total_minutes, 2),
                "total_hours": round(total_minutes / 60, 2),
                "total_messages": total_messages,
                "total_groups": total_groups,
                "estimated_cost": round(total_cost, 2)
            },
            "by_plan": [
                {
                    "plan": plan.value if plan else "unknown",
                    "sessions": count,
                    "total_minutes": round(minutes or 0, 2)
                }
                for plan, count, minutes in warmer_by_plan
            ],
            "top_users": [
                {
                    "user_id": user_id,
                    "email": email,
                    "total_minutes": round(total_minutes, 2),
                    "total_hours": round(total_minutes / 60, 2),
                    "session_count": session_count,
                    "cost": round(total_minutes * cost_per_minute, 2)
                }
                for user_id, email, total_minutes, session_count in top_users
            ]
        }
    except Exception as e:
        logger.error(f"Error getting warmer analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Email Template Management
from email_service.templates import template_manager
from email_service.service import email_service

class EmailTemplateConfig(BaseModel):
    template_name: str
    enabled: bool = True
    subject: str = "Welcome to CuWhapp!"
    send_delay_minutes: int = 0
    
class WelcomeEmailRequest(BaseModel):
    email: str
    name: str
    template_name: str = "welcome_default"
    test_mode: bool = False

@app.get("/api/email/templates")
async def get_email_templates():
    """Get all available email templates"""
    return template_manager.list_templates()

@app.get("/api/email/templates/{template_name}")
async def get_email_template(template_name: str):
    """Get a specific email template"""
    template = template_manager.get_template(template_name)
    return {
        "name": template_name,
        "html": template,
        "preview_url": f"/api/email/templates/{template_name}/preview"
    }

@app.get("/api/email/templates/{template_name}/preview", response_class=HTMLResponse)
async def preview_email_template(template_name: str):
    """Preview an email template"""
    template = template_manager.get_template(template_name)
    import re
    template = re.sub(r'\{\{name\}\}', 'John Doe', template)
    template = re.sub(r'\{\{current_year\}\}', str(datetime.now().year), template)
    return HTMLResponse(content=template)

@app.post("/api/email/send-welcome")
async def send_welcome_email(
    request: WelcomeEmailRequest,
    _: bool = Depends(verify_admin_token)
):
    """Send a welcome email to a user"""
    try:
        template = template_manager.get_template(request.template_name)
        import re
        template = re.sub(r'\{\{name\}\}', request.name, template)
        template = re.sub(r'\{\{current_year\}\}', str(datetime.now().year), template)
        
        result = email_service._send_email(
            to_email=request.email,
            to_name=request.name,
            subject=f"{'[TEST] ' if request.test_mode else ''}Welcome to CuWhapp!",
            html_content=template
        )
        
        return {
            "success": result,
            "message": f"Welcome email sent to {request.email}" if result else "Failed to send email"
        }
    except Exception as e:
        logger.error(f"Error sending welcome email: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/email-templates", response_class=HTMLResponse)
async def email_templates_page(request: Request):
    """Email templates management page"""
    return templates.TemplateResponse("email_templates.html", {
        "request": request,
        "title": "Email Templates - CuWhapp Admin"
    })

# ============================================
# WAHA Multi-Instance Monitoring
# ============================================

try:
    from waha_pool_manager import waha_pool
    from free_session_manager import free_session_manager
    import sqlite3
    waha_monitoring_enabled = waha_pool is not None
except ImportError:
    waha_monitoring_enabled = False
    waha_pool = None
    free_session_manager = None
    logger.warning("WAHA monitoring modules not available")

@app.get("/api/waha/instances")
async def get_waha_instances():
    """Get all WAHA instances and their status"""
    if not waha_monitoring_enabled:
        return {"error": "WAHA monitoring not available"}
    
    try:
        status = waha_pool.get_pool_status()
        
        # Add revenue calculations
        total_paid_users = 0
        monthly_revenue = 0
        
        # Calculate revenue based on instance usage
        for instance in status['instances']:
            if instance['type'] != 'free_users':
                # Estimate based on session usage
                if instance['sessions'] > 0:
                    # Rough calculation: average $20 per 10 sessions
                    monthly_revenue += (instance['sessions'] / 10) * 20
                    total_paid_users += instance['sessions'] // 10
        
        status['revenue_metrics'] = {
            'estimated_monthly_revenue': round(monthly_revenue, 2),
            'paid_users_estimate': total_paid_users,
            'scaling_threshold': 'New instance at 100 sessions',
            'cost_per_instance': '$5-10/month (estimated)'
        }
        
        return status
    except Exception as e:
        logger.error(f"Failed to get WAHA instances: {e}")
        return {"error": str(e)}

@app.get("/api/waha/free-sessions")
async def get_free_sessions_stats():
    """Get statistics about free user sessions"""
    if not waha_monitoring_enabled:
        return {"error": "WAHA monitoring not available"}
    
    try:
        stats = free_session_manager.get_stats()
        
        # Add additional insights
        stats['insights'] = {
            'auto_cleanup_enabled': True,
            'cleanup_interval': '5 minutes',
            'max_free_sessions': 100,
            'savings_from_cleanup': f"${stats.get('sessions_deleted_for_inactivity', 0) * 0.01:.2f}/month"
        }
        
        return stats
    except Exception as e:
        logger.error(f"Failed to get free session stats: {e}")
        return {"error": str(e)}

@app.get("/api/waha/scaling-metrics")
async def get_scaling_metrics(db: Session = Depends(get_db_dependency)):
    """Get scaling metrics and predictions"""
    if not waha_monitoring_enabled:
        return {"error": "WAHA monitoring not available"}
    
    try:
        # Get current status
        pool_status = waha_pool.get_pool_status()
        
        # Get subscription counts by plan
        plan_counts = db.query(
            UserSubscription.plan_type,
            func.count(UserSubscription.id).label('count')
        ).filter(
            UserSubscription.status == SubscriptionStatus.ACTIVE
        ).group_by(UserSubscription.plan_type).all()
        
        plan_dict = {plan: count for plan, count in plan_counts}
        
        # Calculate potential sessions
        potential_sessions = (
            plan_dict.get('free', 0) * 1 +
            plan_dict.get('starter', 0) * 1 +
            plan_dict.get('hobby', 0) * 3 +
            plan_dict.get('pro', 0) * 10 +
            plan_dict.get('premium', 0) * 30
        )
        
        # Calculate instances needed
        instances_needed = (potential_sessions // 100) + (1 if potential_sessions % 100 > 0 else 1)
        current_instances = pool_status['total_instances']
        
        # Revenue calculations
        monthly_revenue = (
            plan_dict.get('starter', 0) * 7 +
            plan_dict.get('hobby', 0) * 20 +
            plan_dict.get('pro', 0) * 45 +
            plan_dict.get('premium', 0) * 99
        )
        
        # Scaling predictions
        scaling_metrics = {
            'current_state': {
                'instances': current_instances,
                'total_capacity': pool_status['total_capacity'],
                'used_capacity': pool_status['total_sessions'],
                'utilization': f"{(pool_status['total_sessions'] / pool_status['total_capacity'] * 100):.1f}%"
            },
            'subscriptions': plan_dict,
            'potential': {
                'max_sessions_if_all_active': potential_sessions,
                'instances_needed': instances_needed,
                'additional_instances_required': max(0, instances_needed - current_instances)
            },
            'revenue': {
                'monthly_revenue': f"${monthly_revenue:,.2f}",
                'per_instance_cost': "$5-10",
                'total_infrastructure_cost': f"${current_instances * 7.5:,.2f}",
                'profit_margin': f"${monthly_revenue - (current_instances * 7.5):,.2f}"
            },
            'scaling_triggers': {
                '80%_capacity': pool_status['total_sessions'] >= pool_status['total_capacity'] * 0.8,
                'revenue_threshold': monthly_revenue > 500,
                'should_scale_now': pool_status['total_sessions'] >= pool_status['total_capacity'] * 0.9
            },
            'recommendations': []
        }
        
        # Add recommendations
        if scaling_metrics['scaling_triggers']['should_scale_now']:
            scaling_metrics['recommendations'].append("⚠️ Consider spinning up a new instance - approaching capacity")
        
        if monthly_revenue > current_instances * 100:
            scaling_metrics['recommendations'].append("✅ Revenue supports additional instances")
        
        if plan_dict.get('premium', 0) > current_instances:
            scaling_metrics['recommendations'].append("📈 Premium users exceed instance count - scale up")
        
        return scaling_metrics
        
    except Exception as e:
        logger.error(f"Failed to get scaling metrics: {e}")
        return {"error": str(e)}

@app.post("/api/waha/trigger-cleanup")
async def trigger_free_cleanup():
    """Manually trigger cleanup of inactive free sessions"""
    if not waha_monitoring_enabled:
        return {"error": "WAHA monitoring not available"}
    
    try:
        free_session_manager.cleanup_inactive_sessions()
        return {
            "success": True,
            "message": "Cleanup triggered successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to trigger cleanup: {e}")
        return {"error": str(e)}

@app.get("/waha-monitoring", response_class=HTMLResponse)
async def waha_monitoring_page(request: Request):
    """WAHA monitoring dashboard page"""
    return templates.TemplateResponse("waha_monitoring.html", {
        "request": request,
        "title": "WAHA Instance Monitoring"
    })

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)