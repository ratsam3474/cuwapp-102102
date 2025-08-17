"""
Email Template Management for CuWhapp
Professional HTML email templates with customization
"""

from typing import Dict, List, Optional
from datetime import datetime
import json
import os
from pathlib import Path

class EmailTemplateManager:
    def __init__(self):
        base_path = os.getenv("APP_PATH", ".")
        self.templates_dir = Path(base_path) / "email_service" / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.api_url = os.getenv('API_GATEWAY_URL', 'https://app.cuwapp.com')
        self.support_email = os.getenv('SUPPORT_EMAIL', 'support@cuwapp.com')
        self.load_templates()
    
    def load_templates(self):
        """Load or create default email templates"""
        self.templates = {
            "welcome_default": self.get_welcome_template(),
            "welcome_premium": self.get_premium_welcome_template(),
            "welcome_minimal": self.get_minimal_welcome_template()
        }
    
    def get_welcome_template(self) -> str:
        """Default professional welcome email template"""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to CuWhapp</title>
            <!--[if mso]>
            <noscript>
                <xml>
                    <o:OfficeDocumentSettings>
                        <o:PixelsPerInch>96</o:PixelsPerInch>
                    </o:OfficeDocumentSettings>
                </xml>
            </noscript>
            <![endif]-->
            <style>
                @media only screen and (max-width: 600px) {
                    .container { width: 100% !important; }
                    .content { padding: 20px !important; }
                    .cta-button { width: 100% !important; text-align: center !important; }
                }
            </style>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f4f4f4;">
                <tr>
                    <td align="center" style="padding: 40px 0;">
                        <table class="container" role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <!-- Header -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #1a4d2e 0%, #2d5f3f 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0;">
                                    <h1 style="margin: 0; color: #ffffff; font-size: 32px; font-weight: 700;">
                                        🎉 Welcome to CuWhapp!
                                    </h1>
                                    <p style="margin: 10px 0 0 0; color: #e8f5e9; font-size: 16px;">
                                        Your WhatsApp Business automation journey starts here
                                    </p>
                                </td>
                            </tr>
                            
                            <!-- Main Content -->
                            <tr>
                                <td class="content" style="padding: 40px 30px;">
                                    <h2 style="color: #1a4d2e; font-size: 24px; margin-bottom: 20px;">
                                        Hi {{name}}! 👋
                                    </h2>
                                    
                                    <p style="color: #333333; font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
                                        We're thrilled to have you join the CuWhapp community! You're now part of thousands of businesses revolutionizing their WhatsApp marketing and customer engagement.
                                    </p>
                                    
                                    <!-- Features Section -->
                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: 30px 0;">
                                        <tr>
                                            <td style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                                                <h3 style="color: #1a4d2e; font-size: 18px; margin-bottom: 15px;">
                                                    🚀 Here's what you can do with CuWhapp:
                                                </h3>
                                                <ul style="color: #555555; font-size: 14px; line-height: 1.8; margin: 0; padding-left: 20px;">
                                                    <li><strong>Bulk Messaging:</strong> Reach thousands of customers instantly</li>
                                                    <li><strong>Campaign Management:</strong> Create and schedule targeted campaigns</li>
                                                    <li><strong>Contact Warmer:</strong> Build trust with gradual engagement</li>
                                                    <li><strong>Analytics Dashboard:</strong> Track performance in real-time</li>
                                                    <li><strong>Multi-Session Support:</strong> Manage multiple WhatsApp accounts</li>
                                                </ul>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <!-- CTA Buttons -->
                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: 30px 0;">
                                        <tr>
                                            <td align="center">
                                                <a href="{self.api_url}" class="cta-button" style="display: inline-block; padding: 15px 40px; background-color: #1a4d2e; color: #ffffff; text-decoration: none; border-radius: 5px; font-weight: 600; font-size: 16px;">
                                                    Go to Dashboard
                                                </a>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td align="center" style="padding-top: 15px;">
                                                <a href="http://localhost:5503" style="color: #1a4d2e; text-decoration: underline; font-size: 14px;">
                                                    Read our Getting Started Guide
                                                </a>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <!-- Quick Tips -->
                                    <div style="background-color: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; margin: 30px 0; border-radius: 4px;">
                                        <h4 style="color: #1a4d2e; margin: 0 0 10px 0; font-size: 16px;">
                                            💡 Quick Start Tip:
                                        </h4>
                                        <p style="color: #555555; margin: 0; font-size: 14px; line-height: 1.6;">
                                            Start by creating your first WhatsApp session. Click "Create Session" in your dashboard, scan the QR code with your WhatsApp, and you're ready to send your first campaign!
                                        </p>
                                    </div>
                                    
                                    <!-- Support Section -->
                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-top: 40px; padding-top: 30px; border-top: 1px solid #e0e0e0;">
                                        <tr>
                                            <td align="center">
                                                <h3 style="color: #333333; font-size: 18px; margin-bottom: 15px;">
                                                    Need Help?
                                                </h3>
                                                <p style="color: #666666; font-size: 14px; line-height: 1.6; margin-bottom: 20px;">
                                                    Our support team is here to help you succeed
                                                </p>
                                                <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                                    <tr>
                                                        <td style="padding: 0 10px;">
                                                            <a href="mailto:{self.support_email}" style="color: #1a4d2e; text-decoration: none; font-size: 14px;">
                                                                📧 Email Support
                                                            </a>
                                                        </td>
                                                        <td style="padding: 0 10px;">
                                                            <a href="http://localhost:5503" style="color: #1a4d2e; text-decoration: none; font-size: 14px;">
                                                                📚 Documentation
                                                            </a>
                                                        </td>
                                                    </tr>
                                                </table>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td style="background-color: #f8f9fa; padding: 30px; text-align: center; border-radius: 0 0 8px 8px;">
                                    <p style="color: #666666; font-size: 12px; margin: 0 0 10px 0;">
                                        {{current_year}} CuWhapp. All rights reserved.
                                    </p>
                                    <p style="color: #999999; font-size: 11px; margin: 0;">
                                        You received this email because you signed up for CuWhapp.
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
    
    def get_premium_welcome_template(self) -> str:
        """Premium animated welcome email template"""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to CuWhapp Premium</title>
            <style>
                @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
                .fade-in { animation: fadeIn 1s ease-in; }
                @media only screen and (max-width: 600px) {
                    .container { width: 100% !important; }
                    .two-column td { display: block !important; width: 100% !important; }
                }
            </style>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Helvetica Neue', Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh;">
            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                <tr>
                    <td align="center" style="padding: 60px 20px;">
                        <table class="container" role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="background: #ffffff; border-radius: 20px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
                            <!-- Animated Header -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 60px 40px; text-align: center;">
                                    <div class="fade-in">
                                        <img src="https://via.placeholder.com/80x80/ffffff/667eea?text=CW" alt="CuWhapp" style="width: 80px; height: 80px; border-radius: 50%; margin-bottom: 20px;">
                                        <h1 style="margin: 0; color: #ffffff; font-size: 36px; font-weight: 300; letter-spacing: 2px;">
                                            WELCOME TO PREMIUM
                                        </h1>
                                        <p style="margin: 20px 0 0 0; color: #ffffff; font-size: 18px; opacity: 0.9;">
                                            {{name}}, you're now a VIP member! 🌟
                                        </p>
                                    </div>
                                </td>
                            </tr>
                            
                            <!-- Premium Benefits -->
                            <tr>
                                <td style="padding: 50px 40px;">
                                    <h2 style="color: #333333; font-size: 28px; margin-bottom: 30px; text-align: center;">
                                        Your Premium Benefits
                                    </h2>
                                    
                                    <!-- Two Column Layout -->
                                    <table class="two-column" role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                        <tr>
                                            <td width="50%" style="padding: 20px; text-align: center;">
                                                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); width: 60px; height: 60px; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                                                    <span style="font-size: 28px;">🚀</span>
                                                </div>
                                                <h3 style="color: #333333; margin: 0 0 10px 0;">Unlimited Campaigns</h3>
                                                <p style="color: #666666; font-size: 14px; margin: 0;">No limits on your outreach</p>
                                            </td>
                                            <td width="50%" style="padding: 20px; text-align: center;">
                                                <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); width: 60px; height: 60px; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                                                    <span style="font-size: 28px;">📊</span>
                                                </div>
                                                <h3 style="color: #333333; margin: 0 0 10px 0;">Advanced Analytics</h3>
                                                <p style="color: #666666; font-size: 14px; margin: 0;">Deep insights & reports</p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td width="50%" style="padding: 20px; text-align: center;">
                                                <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); width: 60px; height: 60px; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                                                    <span style="font-size: 28px;">⚡</span>
                                                </div>
                                                <h3 style="color: #333333; margin: 0 0 10px 0;">Priority Support</h3>
                                                <p style="color: #666666; font-size: 14px; margin: 0;">24/7 dedicated assistance</p>
                                            </td>
                                            <td width="50%" style="padding: 20px; text-align: center;">
                                                <div style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); width: 60px; height: 60px; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                                                    <span style="font-size: 28px;">🎯</span>
                                                </div>
                                                <h3 style="color: #333333; margin: 0 0 10px 0;">AI Features</h3>
                                                <p style="color: #666666; font-size: 14px; margin: 0;">Smart automation tools</p>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <!-- Premium CTA -->
                                    <div style="text-align: center; margin: 40px 0;">
                                        <a href="{self.api_url}" style="display: inline-block; padding: 18px 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; border-radius: 50px; font-weight: 600; font-size: 16px; box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);">
                                            Access Premium Dashboard
                                        </a>
                                    </div>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
    
    def get_minimal_welcome_template(self) -> str:
        """Minimal clean welcome email template"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #ffffff;">
            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                <tr>
                    <td align="center" style="padding: 60px 20px;">
                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="500">
                            <tr>
                                <td style="text-align: center; padding-bottom: 40px;">
                                    <h1 style="margin: 0; font-size: 48px; font-weight: 900; color: #1a4d2e;">
                                        CuWhapp
                                    </h1>
                                </td>
                            </tr>
                            <tr>
                                <td>
                                    <h2 style="font-size: 24px; font-weight: 400; color: #333333; margin: 0 0 20px 0;">
                                        Welcome, {{name}}
                                    </h2>
                                    <p style="font-size: 16px; line-height: 1.6; color: #666666; margin: 0 0 30px 0;">
                                        Your account is ready. Start sending WhatsApp campaigns and engaging with your customers at scale.
                                    </p>
                                    <a href="{self.api_url}" style="display: inline-block; padding: 12px 32px; background-color: #1a4d2e; color: #ffffff; text-decoration: none; border-radius: 4px; font-weight: 500;">
                                        Open Dashboard
                                    </a>
                                    <p style="font-size: 14px; color: #999999; margin: 40px 0 0 0;">
                                        Questions? Reply to this email or visit our <a href="http://localhost:5503" style="color: #1a4d2e;">documentation</a>.
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
    
    def get_template(self, template_name: str) -> str:
        """Get a specific template"""
        return self.templates.get(template_name, self.templates["welcome_default"])
    
    def save_custom_template(self, name: str, html_content: str, metadata: Dict = None):
        """Save a custom template"""
        template_file = self.templates_dir / f"{name}.html"
        template_file.write_text(html_content)
        
        # Save metadata
        if metadata:
            meta_file = self.templates_dir / f"{name}.json"
            meta_file.write_text(json.dumps(metadata, indent=2))
        
        # Add to templates dict
        self.templates[name] = html_content
        
        return True
    
    def list_templates(self) -> List[Dict]:
        """List all available templates"""
        templates = []
        for name, content in self.templates.items():
            templates.append({
                "name": name,
                "display_name": name.replace("_", " ").title(),
                "size": len(content),
                "preview": content[:200] + "..." if len(content) > 200 else content
            })
        
        # Add custom templates from files
        for template_file in self.templates_dir.glob("*.html"):
            name = template_file.stem
            if name not in self.templates:
                templates.append({
                    "name": name,
                    "display_name": name.replace("_", " ").title(),
                    "size": template_file.stat().st_size,
                    "custom": True
                })
        
        return templates

# Initialize template manager
template_manager = EmailTemplateManager()