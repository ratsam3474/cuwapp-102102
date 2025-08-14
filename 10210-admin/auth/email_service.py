"""
Email Service for CuWhapp
Handles all email communications including:
- Magic link authentication
- Newsletter subscriptions
- Campaign notifications
- Daily metrics reports
"""

import smtplib
import secrets
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json
import asyncio
from pathlib import Path

class EmailService:
    def __init__(self, smtp_host: str = "smtp.gmail.com", smtp_port: int = 587,
                 sender_email: str = None, sender_password: str = None):
        """Initialize email service with SMTP configuration"""
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email or "noreply@cuwapp.com"
        self.sender_password = sender_password
        self.sender_name = "CuWhapp Team"
        
        # Store magic links temporarily (in production, use Redis)
        self.magic_links = {}
        self.reset_tokens = {}
        
    def generate_magic_link(self, email: str, purpose: str = "login") -> str:
        """Generate a secure magic link for passwordless login"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=1)
        
        self.magic_links[token] = {
            "email": email,
            "purpose": purpose,
            "expires_at": expires_at,
            "used": False
        }
        
        base_url = "https://app.cuwapp.com"
        return f"{base_url}/auth/magic-link?token={token}&purpose={purpose}"
    
    def send_magic_link(self, email: str, name: str = None) -> bool:
        """Send magic link for passwordless authentication"""
        try:
            magic_link = self.generate_magic_link(email, "login")
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #1a4d2e, #2d5f3f); color: white; padding: 30px; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .button {{ display: inline-block; padding: 15px 30px; background: #1a4d2e; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                    .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🚀 CuWhapp - Quick Login</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {name or 'there'}! 👋</h2>
                        <p>You requested a magic link to sign in to CuWhapp. Click the button below to instantly access your dashboard:</p>
                        
                        <center>
                            <a href="{magic_link}" class="button">🔐 Sign In to CuWhapp</a>
                        </center>
                        
                        <div class="warning">
                            <strong>⏰ This link expires in 1 hour</strong><br>
                            For security reasons, this link can only be used once.
                        </div>
                        
                        <p>If you didn't request this, please ignore this email.</p>
                        
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                        
                        <p><strong>Why magic links?</strong><br>
                        • No passwords to remember<br>
                        • More secure than traditional passwords<br>
                        • Quick access to your campaigns</p>
                    </div>
                    <div class="footer">
                        <p>© 2025 CuWhapp - Cursor for WhatsApp<br>
                        <a href="https://www.cuwapp.com">Visit our website</a> | 
                        <a href="http://localhost:5503">Read our blog</a></p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return self._send_email(
                to_email=email,
                subject="🔐 Your CuWhapp Login Link",
                html_content=html_content
            )
        except Exception as e:
            print(f"Error sending magic link: {e}")
            return False
    
    def send_daily_campaign_reminder(self, email: str, campaign_stats: Dict) -> bool:
        """Send daily reminder about unprocessed campaign leads"""
        try:
            unprocessed = campaign_stats.get('unprocessed_rows', 0)
            campaign_name = campaign_stats.get('campaign_name', 'Your campaign')
            total_rows = campaign_stats.get('total_rows', 0)
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #ff6b6b, #feca57); padding: 30px; border-radius: 10px; text-align: center; }}
                    .stats-box {{ background: white; border: 2px solid #f0f0f0; padding: 20px; margin: 20px 0; border-radius: 10px; }}
                    .big-number {{ font-size: 48px; font-weight: bold; color: #1a4d2e; }}
                    .cta-button {{ display: inline-block; padding: 15px 40px; background: #1a4d2e; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .tip {{ background: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎯 {unprocessed} Leads Waiting!</h1>
                        <p style="font-size: 18px; margin: 0;">Don't keep them waiting - make your move!</p>
                    </div>
                    
                    <div class="stats-box">
                        <h2>📊 Campaign: {campaign_name}</h2>
                        <div class="big-number">{unprocessed}</div>
                        <p>unprocessed rows out of {total_rows} total</p>
                        
                        <center>
                            <a href="https://app.cuwapp.com" class="cta-button">
                                🚀 Start Processing Now
                            </a>
                        </center>
                    </div>
                    
                    <div class="tip">
                        <strong>💡 Pro Tip:</strong> The best time to send WhatsApp messages is between 10 AM - 12 PM and 5 PM - 8 PM for maximum engagement!
                    </div>
                    
                    <p style="text-align: center; color: #666;">
                        Your leads are waiting. Every moment counts!<br>
                        <strong>Turn those leads into conversations today! 💬</strong>
                    </p>
                </div>
            </body>
            </html>
            """
            
            return self._send_email(
                to_email=email,
                subject=f"🔥 {unprocessed} leads waiting in {campaign_name}!",
                html_content=html_content
            )
        except Exception as e:
            print(f"Error sending campaign reminder: {e}")
            return False
    
    def send_newsletter_welcome(self, email: str) -> bool:
        """Send welcome email for newsletter subscription"""
        try:
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #1a4d2e; color: white; padding: 30px; text-align: center; border-radius: 10px; }
                    .content { padding: 30px; }
                    .resource-box { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 10px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎉 Welcome to CuWhapp Newsletter!</h1>
                    </div>
                    <div class="content">
                        <h2>You're now part of the CuWhapp community!</h2>
                        <p>Get ready to receive:</p>
                        <ul>
                            <li>📚 Weekly WhatsApp marketing tips</li>
                            <li>🚀 Product updates and new features</li>
                            <li>💡 Success stories from other users</li>
                            <li>🎯 Exclusive strategies for better engagement</li>
                        </ul>
                        
                        <div class="resource-box">
                            <h3>🎁 Your Welcome Gift</h3>
                            <p>As a thank you for joining, here's our <strong>"10 WhatsApp Marketing Templates That Convert"</strong> guide!</p>
                            <a href="http://localhost:5503" style="display: inline-block; padding: 10px 20px; background: #1a4d2e; color: white; text-decoration: none; border-radius: 5px;">Download Guide</a>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return self._send_email(
                to_email=email,
                subject="🎉 Welcome to CuWhapp Newsletter!",
                html_content=html_content
            )
        except Exception as e:
            print(f"Error sending welcome email: {e}")
            return False
    
    def send_waitlist_confirmation(self, email: str, feature: str = "Chat") -> bool:
        """Send confirmation for waitlist signup"""
        try:
            position = len(self.magic_links) + 142  # Fake position for now
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 30px; text-align: center; border-radius: 10px; }}
                    .position-badge {{ display: inline-block; background: white; color: #667eea; padding: 10px 20px; border-radius: 20px; font-weight: bold; font-size: 24px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🚀 You're on the Waitlist!</h1>
                        <div class="position-badge">#{position}</div>
                    </div>
                    <div style="padding: 30px;">
                        <h2>Thanks for your interest in CuWhapp {feature}!</h2>
                        <p>We're working hard to bring you this amazing feature. You'll be among the first to know when it launches!</p>
                        
                        <p><strong>What happens next?</strong></p>
                        <ul>
                            <li>We'll notify you as soon as {feature} is ready</li>
                            <li>Early access for waitlist members</li>
                            <li>Special launch discount just for you</li>
                        </ul>
                        
                        <p>In the meantime, explore our current features at <a href="https://app.cuwapp.com">your dashboard</a>!</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return self._send_email(
                to_email=email,
                subject=f"✅ You're #{position} on the CuWhapp {feature} Waitlist!",
                html_content=html_content
            )
        except Exception as e:
            print(f"Error sending waitlist confirmation: {e}")
            return False
    
    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Internal method to send emails via SMTP"""
        try:
            # For development, just log the email
            print(f"\n📧 EMAIL WOULD BE SENT:")
            print(f"To: {to_email}")
            print(f"Subject: {subject}")
            print("Content: [HTML Email]")
            
            # In production, uncomment this:
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
            print(f"Error sending email: {e}")
            return False
    
    def verify_magic_link(self, token: str) -> Optional[Dict]:
        """Verify and consume a magic link token"""
        if token not in self.magic_links:
            return None
        
        link_data = self.magic_links[token]
        
        # Check if expired
        if datetime.now() > link_data['expires_at']:
            del self.magic_links[token]
            return None
        
        # Check if already used
        if link_data['used']:
            return None
        
        # Mark as used and return data
        link_data['used'] = True
        return link_data

# Initialize the email service
email_service = EmailService()