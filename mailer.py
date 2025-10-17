from flask_mail import Mail, Message
from flask import url_for, current_app
import config
from user import User

mail = Mail()

def send_new_user_notification(app, user_email):
    """Notifies all admins that a new user has registered."""
    with app.app_context():
        admin_emails = User.get_admin_emails()
        if not admin_emails:
            current_app.logger.warning("No admin users found to send new user notification.")
            return

        msg = Message(
            'New User Registration',
            sender=config.MAIL_DEFAULT_SENDER,
            recipients=admin_emails
        )
        msg.body = f"A new user with the email {user_email} has registered and is waiting for approval."
        try:
            mail.send(msg)
            current_app.logger.info(f"Admin notification sent for {user_email} to: {', '.join(admin_emails)}")
        except Exception as e:
            current_app.logger.error(f"Error sending admin notification: {e}")

def send_approval_email(app, user_email):
    """Sends an email to the user when their account is approved."""
    with app.app_context():
        msg = Message(
            'Your Account has been Approved!',
            sender=config.MAIL_DEFAULT_SENDER,
            recipients=[user_email]
        )
        msg.body = "Congratulations! Your account has been approved by an administrator. You can now log in."
        try:
            mail.send(msg)
            current_app.logger.info(f"Approval email sent to {user_email}")
        except Exception as e:
            current_app.logger.error(f"Error sending approval email: {e}")

def send_denial_email(app, user_email):
    """Sends an email to the user when their account is denied."""
    with app.app_context():
        msg = Message(
            'Your Registration Status',
            sender=config.MAIL_DEFAULT_SENDER,
            recipients=[user_email]
        )
        msg.body = "We regret to inform you that your registration has been denied at this time."
        try:
            mail.send(msg)
            current_app.logger.info(f"Denial email sent to {user_email}")
        except Exception as e:
            current_app.logger.error(f"Error sending denial email: {e}")

def send_password_reset_email(app, user_email, token):
    """Sends a password reset email to the user."""
    with app.app_context():
        reset_url = url_for('auth.reset_password', token=token, _external=True)
        msg = Message(
            'Password Reset Request',
            sender=config.MAIL_DEFAULT_SENDER,
            recipients=[user_email]
        )
        msg.body = f"Click the following link to reset your password: {reset_url}"
        try:
            mail.send(msg)
            current_app.logger.info(f"Password reset email sent to {user_email}")
        except Exception as e:
            current_app.logger.error(f"Error sending password reset email: {e}")