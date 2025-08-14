# MahilMartPOS_App/decorators.py
from functools import wraps
from django.shortcuts import render

def access_required(allowed_roles=None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return render(request, "base.html", {"access_denied": True})

            if allowed_roles:
                user_role = None
                if request.user.is_superuser:
                    user_role = 'superuser'
                elif request.user.is_staff:
                    user_role = 'staff'
                else:
                    user_role = 'user'

                if user_role not in allowed_roles:
                    return render(request, "base.html", {"access_denied": True})

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
