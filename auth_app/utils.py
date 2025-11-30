from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
import threading

class EmailThread(threading.Thread):
    def __init__(self, email):
        self.email = email
        threading.Thread.__init__(self)

    def run(self):
        self.email.send()

class Util:
    @staticmethod
    def send_verification_email(user_data):
        """
        Send HTML verification email with username
        """
        # Render HTML content
        html_content = render_to_string('verification_success.html', {
            'user_first_name': user_data['user_first_name'],
            'username': user_data['username'],
            'verification_url': user_data['verification_url']
        })
        
        # Create plain text version as fallback
        text_content = f"""
        Hi {user_data['user_first_name']},
        
        Thank you for registering! Your username is: {user_data['username']}
        
        Please verify your email address by clicking the link below:
        
        {user_data['verification_url']}
        
        This link will expire in 24 hours.
        
        Best regards,
        Your App Team
        """
        
        # Create email message with both HTML and text versions
        email = EmailMultiAlternatives(
            subject=user_data['email_subject'],
            body=text_content,
            from_email='noreply@yourapp.com',
            to=[user_data['to_email']]
        )
        email.attach_alternative(html_content, "text/html")
        EmailThread(email).start()

    @staticmethod
    def send_password_reset_email(user_data):
        """
        Send HTML password reset email
        """
        # Render HTML content
        html_content = render_to_string('password_reset_email.html', {
            'user_first_name': user_data['user_first_name'],
            'reset_url': user_data['reset_url']
        })
        
        # Create plain text version as fallback
        text_content = f"""
        Hi {user_data['user_first_name']},
        
        We received a request to reset your password for your account.
        
        Please click the link below to reset your password:
        
        {user_data['reset_url']}
        
        This link will expire in 24 hours.
        
        If you didn't request a password reset, please ignore this email.
        
        Best regards,
        Your App Team
        """
        
        # Create email message with both HTML and text versions
        email = EmailMultiAlternatives(
            subject=user_data['email_subject'],
            body=text_content,
            from_email='noreply@yourapp.com',
            to=[user_data['to_email']]
        )
        email.attach_alternative(html_content, "text/html")
        EmailThread(email).start()

    @staticmethod
    def send_password_reset_success_email(user_data):
        """
        Send HTML password reset success email
        """
        # Render HTML content
        html_content = render_to_string('verification_success.html', {
            'user_first_name': user_data['user_first_name']
        })
        
        # Create plain text version as fallback
        text_content = f"""
        Hi {user_data['user_first_name']},
        
        Your password has been successfully reset.
        
        If you did not make this change, please contact our support team immediately.
        
        Best regards,
        Your App Team
        """
        
        # Create email message with both HTML and text versions
        email = EmailMultiAlternatives(
            subject=user_data['email_subject'],
            body=text_content,
            from_email='noreply@yourapp.com',
            to=[user_data['to_email']]
        )
        email.attach_alternative(html_content, "text/html")
        EmailThread(email).start()

    @staticmethod
    def send_welcome_email(user_data):
        """
        Send welcome email after successful verification
        """
        # Render HTML content
        html_content = render_to_string('emails/welcome_email.html', {
            'user_first_name': user_data['user_first_name'],
            'username': user_data['username']
        })
        
        # Create plain text version as fallback
        text_content = f"""
        Hi {user_data['user_first_name']},
        
        Welcome to our platform! Your account has been successfully verified.
        
        Your username: {user_data['username']}
        
        You can now log in and start using all the features.
        
        Best regards,
        Your App Team
        """
        
        # Create email message with both HTML and text versions
        email = EmailMultiAlternatives(
            subject=user_data['email_subject'],
            body=text_content,
            from_email='noreply@yourapp.com',
            to=[user_data['to_email']]
        )
        email.attach_alternative(html_content, "text/html")
        EmailThread(email).start()