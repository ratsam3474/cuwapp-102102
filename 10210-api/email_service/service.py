"""
Email Service for CuWhapp
Works alongside Clerk authentication
Handles newsletters, waitlists, and campaign notifications
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class CuWhappEmailService:
    def __init__(self, smtp_host: str = "smtp.gmail.com", smtp_port: int = 587,
                 sender_email: str = None, sender_password: str = None):
        """Initialize email service"""
        import os
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email or os.getenv('NOTIFICATION_EMAIL', 'notifications@cuwapp.com')
        self.sender_password = sender_password
        self.sender_name = "CuWhapp Team"
        self.api_url = os.getenv('API_GATEWAY_URL', 'https://app.cuwapp.com')
        
        # Storage path for email lists
        base_path = os.getenv("DATA_PATH", "data")
        self.storage_path = Path(base_path) / "email"
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def send_campaign_reminder(self, user_email: str, user_name: str, campaign_data: Dict) -> bool:
        """Send daily reminder about unprocessed campaign rows"""
        try:
            unprocessed = campaign_data.get('unprocessed_rows', 0)
            campaign_name = campaign_data.get('campaign_name', 'Your campaign')
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #1a4d2e, #2d5f3f); color: white; padding: 40px; border-radius: 10px 10px 0 0; text-align: center; }}
                    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .stat-card {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                    .big-number {{ font-size: 48px; font-weight: bold; color: #1a4d2e; margin: 10px 0; }}
                    .cta-button {{ display: inline-block; padding: 15px 40px; background: #1a4d2e; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .tip {{ background: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎯 Hey {user_name}!</h1>
                        <p style="font-size: 20px; margin: 0;">You have leads waiting!</p>
                    </div>
                    
                    <div class="content">
                        <div class="stat-card">
                            <h2 style="margin-top: 0;">📊 {campaign_name}</h2>
                            <div class="big-number">{unprocessed:,}</div>
                            <p style="color: #666;">unprocessed contacts ready to engage</p>
                            
                            <center>
                                <a href="{self.api_url}" class="cta-button">
                                    🚀 Process Them Now
                                </a>
                            </center>
                        </div>
                        
                        <div class="tip">
                            <strong>💡 Pro Tip:</strong> Best engagement times are 10-12 AM and 5-8 PM. 
                            Schedule your campaigns to maximize response rates!
                        </div>
                        
                        <p style="text-align: center; color: #666; margin-top: 30px;">
                            Don't let these opportunities slip away!<br>
                            <strong>Every lead is a potential conversion 🎯</strong>
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return self._send_email(
                to_email=user_email,
                to_name=user_name,
                subject=f"🔥 {unprocessed:,} contacts waiting in {campaign_name}",
                html_content=html_content
            )
        except Exception as e:
            logger.error(f"Error sending campaign reminder: {e}")
            return False
    
    def send_newsletter_welcome(self, email: str, name: str = None) -> bool:
        """Send welcome email for newsletter subscription"""
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #1a4d2e; color: white; padding: 40px; text-align: center; border-radius: 10px; }}
                    .content {{ padding: 30px; }}
                    .feature {{ background: #f8f9fa; padding: 20px; margin: 15px 0; border-radius: 8px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎉 Welcome to CuWhapp Newsletter!</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {name or 'there'}! You're in!</h2>
                        
                        <p>Get ready for weekly insights on:</p>
                        
                        <div class="feature">
                            <strong>📚 WhatsApp Marketing Tips</strong><br>
                            Proven strategies to boost engagement
                        </div>
                        
                        <div class="feature">
                            <strong>🚀 Product Updates</strong><br>
                            Be first to know about new features
                        </div>
                        
                        <div class="feature">
                            <strong>💡 Success Stories</strong><br>
                            Learn from other CuWhapp users
                        </div>
                        
                        <p style="text-align: center; margin-top: 30px;">
                            <a href="http://localhost:5503" style="display: inline-block; padding: 12px 30px; background: #1a4d2e; color: white; text-decoration: none; border-radius: 5px;">
                                Read Our Blog
                            </a>
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Save subscriber to list
            self._save_subscriber(email, name)
            
            return self._send_email(
                to_email=email,
                to_name=name,
                subject="🎉 Welcome to CuWhapp Newsletter!",
                html_content=html_content
            )
        except Exception as e:
            logger.error(f"Error sending welcome email: {e}")
            return False
    
    def send_waitlist_confirmation(self, email: str, name: str = None, feature: str = "Chat") -> bool:
        """Send waitlist confirmation email"""
        try:
            # Get position in waitlist
            position = self._get_waitlist_position(email, feature)
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 40px; text-align: center; border-radius: 10px; }}
                    .position-badge {{ display: inline-block; background: white; color: #667eea; padding: 10px 25px; border-radius: 25px; font-weight: bold; font-size: 28px; margin: 20px 0; }}
                    .content {{ padding: 30px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🚀 You're on the List!</h1>
                        <div class="position-badge">#{position}</div>
                    </div>
                    <div class="content">
                        <h2>Thanks {name or 'there'}!</h2>
                        <p>You're now on the waitlist for <strong>CuWhapp {feature}</strong>!</p>
                        
                        <p><strong>What happens next?</strong></p>
                        <ul>
                            <li>📧 We'll email you when {feature} is ready</li>
                            <li>🎁 Early access for waitlist members</li>
                            <li>💰 Special launch discount</li>
                        </ul>
                        
                        <p>Meanwhile, explore our current features:</p>
                        <p style="text-align: center;">
                            <a href="{self.api_url}" style="display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px;">
                                Go to Dashboard
                            </a>
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return self._send_email(
                to_email=email,
                to_name=name,
                subject=f"✅ You're #{position} on the {feature} Waitlist!",
                html_content=html_content
            )
        except Exception as e:
            logger.error(f"Error sending waitlist confirmation: {e}")
            return False
    
    def _send_email(self, to_email: str, to_name: str, subject: str, html_content: str) -> bool:
        """Internal method to send emails"""
        try:
            # For development, just log
            logger.info(f"📧 Email queued: {subject} to {to_email}")
            
            # Save to email queue
            queue_file = self.storage_path / "email_queue.json"
            queue = []
            if queue_file.exists():
                with open(queue_file, 'r') as f:
                    queue = json.load(f)
            
            queue.append({
                "to_email": to_email,
                "to_name": to_name,
                "subject": subject,
                "queued_at": datetime.now().isoformat(),
                "status": "pending"
            })
            
            with open(queue_file, 'w') as f:
                json.dump(queue, f, indent=2)
            
            # In production, send via SMTP:
            """
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = to_email
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            """
            
            return True
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def _save_subscriber(self, email: str, name: str = None):
        """Save newsletter subscriber"""
        subscribers_file = self.storage_path / "newsletter_subscribers.json"
        subscribers = {}
        
        if subscribers_file.exists():
            with open(subscribers_file, 'r') as f:
                subscribers = json.load(f)
        
        subscribers[email] = {
            "email": email,
            "name": name,
            "subscribed_at": datetime.now().isoformat(),
            "active": True
        }
        
        with open(subscribers_file, 'w') as f:
            json.dump(subscribers, f, indent=2)
    
    def _get_waitlist_position(self, email: str, feature: str) -> int:
        """Get or assign waitlist position"""
        waitlist_file = self.storage_path / f"waitlist_{feature.lower()}.json"
        waitlist = {}
        
        if waitlist_file.exists():
            with open(waitlist_file, 'r') as f:
                waitlist = json.load(f)
        
        if email not in waitlist:
            waitlist[email] = {
                "position": len(waitlist) + 1,
                "joined_at": datetime.now().isoformat()
            }
            
            with open(waitlist_file, 'w') as f:
                json.dump(waitlist, f, indent=2)
        
        return waitlist[email]["position"]

# Initialize the service
email_service = CuWhappEmailService()