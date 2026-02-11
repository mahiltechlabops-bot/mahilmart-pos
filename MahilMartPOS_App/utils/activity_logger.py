from MahilMartPOS_App.models import ActivityLog


def get_client_ip(request):
    if not request:
        return None

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]
    return request.META.get("REMOTE_ADDR")


def get_user_role(user):
    """
    Role = Django Group(s)
    """
    if user and user.groups.exists():
        # If user has multiple groups, show all
        return ", ".join(user.groups.values_list("name", flat=True))
    return "N/A"


def log_activity(request, action, module, description):
    user = request.user if request and request.user.is_authenticated else None

    ActivityLog.objects.create(
        user=user,
        username=user.username if user else "System",
        role=get_user_role(user),
        action=action,
        module=module,
        description=description,
        ip_address=get_client_ip(request),
        device_name=request.META.get("HTTP_USER_AGENT", "")[:255] if request else "",
    )
