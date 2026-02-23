# utils/email_config.py
from django.conf import settings
from ..models import EmailConfig


def apply_email_settings():
    config = EmailConfig.objects.filter(is_active=True).first()
    if not config:
        return

    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST = config.email_host
    settings.EMAIL_PORT = config.email_port
    settings.EMAIL_USE_TLS = config.use_tls
    settings.EMAIL_HOST_USER = config.email_host_user
    settings.EMAIL_HOST_PASSWORD = config.email_host_password
    settings.DEFAULT_FROM_EMAIL = config.default_from_email or config.email_host_user
