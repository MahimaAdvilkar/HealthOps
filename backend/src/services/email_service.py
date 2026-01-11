"""
Email Service for HealthOps
Sends notifications using Gmail API for scheduling confirmations and workflow updates
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from datetime import datetime
import requests

# Load environment variables
load_dotenv()


class EmailService:
    """
    Email service for sending notifications
    Supports Gmail API and SMTP fallback
    """
    
    def __init__(self):
        self.sender_email = os.getenv("SENDER_EMAIL", "noreply@healthops.com")
        self.default_receiver = os.getenv("DEFAULT_RECEIVER_EMAIL", "advilkarmahima190@gmail.com")
        self.gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        
    def send_scheduling_confirmation(
        self,
        referral_data: Dict[str, Any],
        caregiver_data: Optional[Dict[str, Any]] = None,
        receiver_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send scheduling confirmation email to patient/customer
        
        Args:
            referral_data: Referral information
            caregiver_data: Assigned caregiver information (optional)
            receiver_email: Email address to send to (defaults to config)
            
        Returns:
            Result dictionary with success status
        """
        try:
            # Use default receiver if not provided
            to_email = receiver_email or self.default_receiver
            
            # Build email content
            subject = f"HealthOps - Scheduling Confirmation for {referral_data.get('referral_id')}"
            
            # Create HTML email body
            html_body = self._build_scheduling_email_html(referral_data, caregiver_data)
            
            # Send email
            result = self._send_email(
                to_email=to_email,
                subject=subject,
                html_body=html_body
            )
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to send scheduling confirmation email"
            }
    
    def send_workflow_notification(
        self,
        referral_id: str,
        workflow_status: str,
        details: str,
        receiver_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send workflow status notification email
        
        Args:
            referral_id: Referral ID
            workflow_status: Current workflow status
            details: Additional details
            receiver_email: Email address to send to
            
        Returns:
            Result dictionary
        """
        try:
            to_email = receiver_email or self.default_receiver
            
            subject = f"HealthOps - Workflow Update: {referral_id}"
            
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px;">
                        <h2 style="color: #6366f1;">Workflow Status Update</h2>
                        <p><strong>Referral ID:</strong> {referral_id}</p>
                        <p><strong>Status:</strong> <span style="color: #10b981; font-weight: bold;">{workflow_status}</span></p>
                        <p><strong>Details:</strong></p>
                        <p style="background-color: #f3f4f6; padding: 15px; border-radius: 5px;">{details}</p>
                        <hr style="margin: 20px 0; border: none; border-top: 1px solid #e5e7eb;">
                        <p style="color: #6b7280; font-size: 12px;">This is an automated notification from HealthOps</p>
                    </div>
                </body>
            </html>
            """
            
            return self._send_email(to_email, subject, html_body)
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_scheduling_email_html(
        self,
        referral_data: Dict[str, Any],
        caregiver_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build HTML email body for scheduling confirmation"""
        
        referral_id = referral_data.get('referral_id', 'N/A')
        patient_city = referral_data.get('patient_city', 'N/A')
        service_type = referral_data.get('service_type', 'N/A')
        urgency = referral_data.get('urgency', 'Routine')
        units = referral_data.get('auth_units_remaining', 0)
        
        caregiver_info = ""
        if caregiver_data:
            caregiver_name = caregiver_data.get('caregiver_name', 'TBD')
            caregiver_skills = caregiver_data.get('skills', 'N/A')
            caregiver_city = caregiver_data.get('city', 'N/A')
            
            caregiver_info = f"""
            <div style="background-color: #f0fdf4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #059669; margin-top: 0;">Assigned Caregiver</h3>
                <p><strong>Name:</strong> {caregiver_name}</p>
                <p><strong>Skills:</strong> {caregiver_skills}</p>
                <p><strong>Location:</strong> {caregiver_city}</p>
            </div>
            """
        
        urgency_color = "#ef4444" if urgency == "Urgent" else "#10b981"
        
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #6366f1; margin-bottom: 10px;">HealthOps</h1>
                        <h2 style="color: #1f2937; margin-top: 0;">Scheduling Confirmation</h2>
                    </div>
                    
                    <div style="background-color: #eef2ff; padding: 20px; border-radius: 5px; margin-bottom: 20px;">
                        <p style="margin: 0; font-size: 16px;">Your referral has been scheduled successfully!</p>
                    </div>
                    
                    <h3 style="color: #374151; border-bottom: 2px solid #6366f1; padding-bottom: 10px;">Referral Details</h3>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <tr>
                            <td style="padding: 10px 0;"><strong>Referral ID:</strong></td>
                            <td style="padding: 10px 0;">{referral_id}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0;"><strong>Service Type:</strong></td>
                            <td style="padding: 10px 0;">{service_type}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0;"><strong>Location:</strong></td>
                            <td style="padding: 10px 0;">{patient_city}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0;"><strong>Priority:</strong></td>
                            <td style="padding: 10px 0;"><span style="color: {urgency_color}; font-weight: bold;">{urgency}</span></td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0;"><strong>Authorized Units:</strong></td>
                            <td style="padding: 10px 0;">{units} units</td>
                        </tr>
                    </table>
                    
                    {caregiver_info}
                    
                    <div style="background-color: #fef3c7; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #f59e0b;">
                        <p style="margin: 0;"><strong>Next Steps:</strong></p>
                        <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                            <li>A coordinator will contact you within 24 hours</li>
                            <li>Please ensure all documentation is ready</li>
                            <li>Keep your phone accessible for confirmation</li>
                        </ul>
                    </div>
                    
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
                    
                    <p style="color: #6b7280; font-size: 12px; text-align: center;">
                        This is an automated notification from HealthOps<br>
                        Scheduled on: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}
                    </p>
                </div>
            </body>
        </html>
        """
        
        return html
    
    def _send_email(self, to_email: str, subject: str, html_body: str) -> Dict[str, Any]:
        """
        Send email using Gmail SMTP with app password
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = to_email
            
            # Attach HTML body
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Check if SMTP credentials are configured
            if not self.gmail_app_password:
                print(f"\n{'='*60}")
                print(f"EMAIL NOTIFICATION (NOT SENT - NO APP PASSWORD)")
                print(f"{'='*60}")
                print(f"To: {to_email}")
                print(f"Subject: {subject}")
                print(f"{'='*60}\n")
                return {
                    "success": False,
                    "message": "Gmail App Password not configured",
                    "to_email": to_email,
                    "subject": subject,
                    "note": "Set GMAIL_APP_PASSWORD in .env file"
                }
            
            # Send email via Gmail SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Secure the connection
                server.login(self.sender_email, self.gmail_app_password)
                server.send_message(msg)
            
            print(f"\n{'='*60}")
            print(f"EMAIL SENT SUCCESSFULLY")
            print(f"{'='*60}")
            print(f"To: {to_email}")
            print(f"Subject: {subject}")
            print(f"{'='*60}\n")
            
            return {
                "success": True,
                "message": f"Email sent successfully to {to_email}",
                "to_email": to_email,
                "subject": subject,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"\nEMAIL ERROR: {str(e)}\n")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to send email"
            }


# Singleton instance
email_service = EmailService()
