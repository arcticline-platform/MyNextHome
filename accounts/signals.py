# signals.py
import logging
from datetime import datetime, timedelta

now = datetime.now()

from django.conf import settings
from django.dispatch import receiver
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.db.models.signals import post_save

from django.contrib.auth.signals import (
    user_logged_in, user_logged_out, user_login_failed
)

from .models import UserProfile, LoginAttempt


logger = logging.getLogger(__name__)
FAILED_LOGIN_THRESHOLD = 5  # Number of failed attempts before sending an alert

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


def check_suspicious_activity(username, ip):
    recent_attempts = LoginAttempt.objects.filter(
        successful=False, 
        timestamp__gte=now() - timedelta(minutes=10)
    )
    ip_attempts = recent_attempts.filter(ip_address=ip).count()
    user_attempts = recent_attempts.filter(username=username).count() if username else 0

    if ip_attempts >= FAILED_LOGIN_THRESHOLD or user_attempts >= FAILED_LOGIN_THRESHOLD:
        alert_admin(username, ip, user_attempts, ip_attempts)


def alert_admin(username, ip, user_attempts, ip_attempts):
    message = (
        f"Suspicious login activity detected:\n\n"
        f"Username: {username or 'Unknown'}\n"
        f"IP Address: {ip}\n"
        f"Failed Attempts from IP: {ip_attempts}\n"
        f"Failed Attempts for Username: {user_attempts}\n"
        f"Time: {now()}"
    )
    send_mail(
        "Suspicious Login Activity Alert",
        message,
        settings.DEFAULT_FROM_EMAIL,
        [admin_email for admin_email in settings.ADMINS],
    )

def get_client_ip(request):
    """Utility to get client IP address from the request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@receiver(user_logged_in)
def log_successful_login(sender, request, user, **kwargs):
    logger.info(f"User '{user.username}' logged in successfully from IP: {get_client_ip(request)}")
    LoginAttempt.objects.create(
        user=user, username=user.username, ip_address=get_client_ip(request), success=True
    )


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    logger.info(f"User '{user.username}' logged out from IP: {get_client_ip(request)}")


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    logger.warning(f"Failed login attempt for username: {credentials.get('username')} from IP: {get_client_ip(request)}")
    LoginAttempt.objects.create(
        username=credentials.get('username'), ip_address=get_client_ip(request), success=False
    )
    check_suspicious_activity(credentials.get('username'), get_client_ip(request))
