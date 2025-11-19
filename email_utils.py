"""
Email utilities for HMS Hospital Management System
Professional email templates for various user interactions
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_verification_email(user, code):
    """
    Send professional verification email to user
    """
    subject = "Verify Your MEDIPLEX HMS Account - Action Required"
    
    # HTML email template
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Email Verification - MEDIPLEX HMS</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .logo {{ font-size: 28px; font-weight: bold; margin-bottom: 10px; }}
            .content {{ background-color: white; padding: 40px; border-radius: 0 0 10px 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .verification-code {{ background: #f8f9fa; border: 2px dashed #667eea; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; color: #667eea; margin: 20px 0; border-radius: 8px; letter-spacing: 3px; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 14px; }}
            .btn {{ display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .highlight {{ color: #667eea; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">🏥 MEDIPLEX HMS</div>
                <div>Hospital Management System</div>
            </div>
            <div class="content">
                <h2>Account Verification Required</h2>
                <p>Dear <span class="highlight">{user.first_name or 'User'}</span>,</p>
                <p>Thank you for registering with <strong>MEDIPLEX HOSPITAL MANAGEMENT SYSTEM</strong>. To complete your registration and activate your account, please use the verification code below:</p>
                
                <div class="verification-code">
                    {code}
                </div>
                
                <p><strong>⏰ This code will expire in 60 seconds for security reasons.</strong></p>
                
                <h3>How to verify:</h3>
                <ol>
                    <li>Return to the MEDIPLEX HMS application</li>
                    <li>Enter the verification code when prompted</li>
                    <li>Your account will be activated immediately</li>
                </ol>
                
                <p>If you didn't request this verification, please ignore this email. Your account remains secure.</p>
                
                <p>For any assistance, please contact our support team at <strong>support@mediplex.com</strong> or call <strong>+1-800-MEDIPLEX</strong>.</p>
            </div>
            <div class="footer">
                <p>&copy; 2024 MEDIPLEX Hospital Management System. All rights reserved.</p>
                <p>This is an automated message. Please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version for email clients that don't support HTML
    message = f"""
Dear {user.first_name or 'User'},

Thank you for registering with MEDIPLEX HOSPITAL MANAGEMENT SYSTEM.

To complete your registration and activate your account, please use the verification code below:

VERIFICATION CODE: {code}

This code will expire in 60 seconds for security reasons.

How to verify:
1. Return to the MEDIPLEX HMS application
2. Enter the verification code when prompted
3. Your account will be activated immediately

If you didn't request this verification, please ignore this email.

For any assistance, please contact our support team at support@mediplex.com or call +1-800-MEDIPLEX.

Best regards,
MEDIPLEX HMS Team
Hospital Management System
© 2024 MEDIPLEX. All rights reserved.
    """
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Could not send verification email: {e}")
        return False

