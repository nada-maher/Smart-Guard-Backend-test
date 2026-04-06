"""
Email Service
Sends notifications to moderators and real-time abnormal behavior alerts
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os
from datetime import datetime
from config.settings import settings

import asyncio

async def send_signup_notification(email: str, full_name: str, organization: str, role: str) -> bool:
    """Send signup notification for a new user registration"""
    print(f"📧 Sending signup notification for: {full_name} ({email}) for {organization}")
    
    # Get all admin emails for the specific organization
    recipients = get_admin_emails_for_organization(organization)
    sender = settings.SENDER_EMAIL
    password = settings.SENDER_PASSWORD
    
    if not recipients or not sender or not password:
        print("⚠️ Email credentials missing. Skipping signup notification.")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🆕 [SIGNUP REQUEST] New User for {organization}: {full_name}"
    msg['From'] = sender
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; direction: rtl; text-align: right;">
            <div style="background-color: #f3f4f6; padding: 20px; border-radius: 10px; border: 1px solid #d1d5db;">
                <h2 style="color: #1f2937;">📝 طلب تسجيل جديد</h2>
                <p style="font-size: 16px;">تم استلام طلب تسجيل جديد لنظام <b>{organization}</b>.</p>
                
                <ul style="list-style: none; padding: 0;">
                    <li><b>⏰ الوقت:</b> {now}</li>
                    <li><b>👤 الاسم:</b> {full_name}</li>
                    <li><b>📧 البريد الإلكتروني:</b> {email}</li>
                    <li><b>🏢 المنظمة:</b> {organization}</li>
                    <li><b>🔑 الدور:</b> {role}</li>
                </ul>
                
                <p style="margin-top: 20px; color: #4b5563;">يرجى مراجعة طلبات التسجيل من خلال لوحة التحكم الخاصة بالمسؤول.</p>
            </div>
        </body>
    </html>
    """
    msg.attach(MIMEText(html, 'html'))

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, send_email_sync, recipients, sender, password, msg)

async def send_signup_notification_dev(email: str, full_name: str, organization: str, role: str) -> bool:
    """Mock signup notification for development (Legacy support)"""
    return await send_signup_notification(email, full_name, organization, role)

import traceback

def send_email_sync(recipients, sender, password, msg):
    """Synchronous function to send email to multiple recipients"""
    try:
        if not recipients:
            print("⚠️ No recipients provided. Skipping email send.")
            return False

        print(f"🔄 Connecting to {settings.SMTP_SERVER}:{settings.SMTP_PORT}...")
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=15)
        server.starttls()
        
        print(f"🔄 Logging in as {sender}...")
        server.login(sender, password)
        
        # Send to all recipients
        # Instead of creating copies, we'll just set the To header for each one if needed
        # or send a single email with multiple recipients in the envelope
        for recipient in recipients:
            # Update the To header for each recipient
            if 'To' in msg:
                del msg['To']
            msg['To'] = recipient
            
            server.send_message(msg)
            print(f"✅ Email sent to {recipient}")
        
        server.quit()
        print(f"✅ Email process completed for {len(recipients)} recipients")
        return True
    except Exception as e:
        print(f"❌ Failed to send email alert: {e}")
        traceback.print_exc()
        return False

def get_admin_emails_for_organization(organization: str) -> list:
    """Get admin emails for a specific organization"""
    try:
        # Specific email mappings for organizations
        organization_emails = {
            "BNU": ["smartguardbnuadmin@gmail.com", "smartguardbnu@gmail.com"],
            "BUE": ["smartguardbueadmin@gmail.com", "smartguardbnu@gmail.com"],
            "Smart Guard": ["smartguardbnu@gmail.com"]
        }
        
        # Return specific emails if organization is mapped
        if organization in organization_emails:
            admin_emails = organization_emails[organization]
            print(f"✅ Found {len(admin_emails)} admin emails for {organization}: {admin_emails}")
            return admin_emails
        
        # Fallback to default email for other organizations
        print(f"❌ No specific emails found for organization: {organization}")
        print(f"📧 Falling back to default email: {settings.RECIPIENT_EMAIL}")
        return [settings.RECIPIENT_EMAIL]
            
    except Exception as e:
        print(f"❌ Error getting admin emails: {e}")
        print(f"📧 Falling back to default email: {settings.RECIPIENT_EMAIL}")
        return [settings.RECIPIENT_EMAIL]

async def send_abnormal_alert_email(confidence: float, video_id: str, frame_path: str = None, event_name: str = "Abnormal Behaviour", organization: str = "Smart Guard") -> bool:
    """
    Send an email alert for detected abnormal behavior
    """
    print(f"🚨 EMAIL SERVICE: Received organization: '{organization}' (type: {type(organization)})")
    print(f"🚨 Sending email alert for organization: '{organization}'")
    
    # Get all admin emails for the specific organization
    recipients = get_admin_emails_for_organization(organization)
    
    # Default sender credentials
    sender = settings.SENDER_EMAIL
    password = settings.SENDER_PASSWORD
    
    # Override credentials for BNU and BUE
    if organization == "BNU":
        sender = "smartguardbnuadmin@gmail.com"
        password = "ampl annq gvxs sfwy"
    elif organization == "BUE":
        sender = "smartguardbueadmin@gmail.com"
        password = "izyi whzy dult rvvf"
    
    if not recipients or not sender or not password:
        print(f"⚠️ Email credentials missing for {organization}. Skipping email alert.")
        return False

    msg = MIMEMultipart('alternative')
    
    # Camera titles mapping
    camera_titles = {
        "cam1": "المدخل الرئيسي",
        "cam2": "المخرج الجانبي", 
        "cam3": "موقف السيارات",
        "cam4": "الممر الخلفي"
    }
    
    # Get camera title or use default
    camera_title = camera_titles.get(video_id, "موقع غير محدد")
    
    msg['Subject'] = f"🚨🚨 [PRIORITY] {organization.upper()} ALERT: {event_name} at {camera_title} ({confidence:.2%})"
    msg['From'] = sender
    # Don't set 'To' here since we'll set it individually for each recipient

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    bg_color = "#fee2e2"
    border_color = "#ef4444"
    text_color = "#b91c1c"
    
    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; direction: rtl; text-align: right;">
            <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px; border: 3px solid {border_color};">
                <h2 style="color: {text_color};">⚡ تنبيه: {event_name}</h2>
                <p style="font-size: 16px;">⚠️ تحذير عالي الخطورة! تم رصد نشاط مريب بواسطة نظام <b>{organization}</b>.</p>
                
                <ul style="list-style: none; padding: 0;">
                    <li><b>⏰ الوقت:</b> {now}</li>
                    <li><b>📍 الموقع:</b> {video_id} - {camera_title}</li>
                    <li><b>🎯 نسبة التأكد:</b> {confidence:.2%}</li>
                    <li><b>🚩 التصنيف:</b> {event_name}</li>
                </ul>
                
                <p style="margin-top: 20px; color: #4b5563;">يرجى مراجعة البث المباشر فوراً لاتخاذ الإجراء اللازم.</p>
            </div>
            <p style="font-size: 12px; color: #9ca3af; margin-top: 20px;">هذا تنبيه تلقائي من نظام {organization} للذكاء الاصطناعي.</p>
        </body>
    </html>
    """
    msg.attach(MIMEText(html, 'html'))

    loop = asyncio.get_event_loop()
    try:
        success = await loop.run_in_executor(None, send_email_sync, recipients, sender, password, msg)
        return success
    except Exception as e:
        print(f"❌ Error in send_abnormal_alert_email executor: {e}")
        return False
