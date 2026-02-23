from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from MahilMartPOS_App.models import ActivityLog


def get_user_role(user):
    if user and user.groups.exists():
        return ", ".join(user.groups.values_list("name", flat=True))
    return "N/A"


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ActivityLog.objects.create(
        user=user,
        username=user.username,
        role=get_user_role(user),
        action="LOGIN",
        module="Authentication",
        description="User logged in",
        ip_address=request.META.get("REMOTE_ADDR"),
        device_name=request.META.get("HTTP_USER_AGENT", "")[:255],
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    ActivityLog.objects.create(
        user=user,
        username=user.username,
        role=get_user_role(user),
        action="LOGOUT",
        module="Authentication",
        description="User logged out",
        ip_address=request.META.get("REMOTE_ADDR"),
        device_name=request.META.get("HTTP_USER_AGENT", "")[:255],
    )
