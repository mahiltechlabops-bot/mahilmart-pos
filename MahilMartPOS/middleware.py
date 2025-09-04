import datetime
from django.conf import settings
from django.contrib.auth import logout

class AutoLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now = datetime.datetime.now().timestamp()
            last_activity = request.session.get('last_activity', now)

            # Idle timeout in seconds (default 10 min)
            timeout = getattr(settings, "AUTO_LOGOUT_DELAY", 60)

            if now - last_activity > timeout:
                logout(request)
                request.session.flush()

            request.session['last_activity'] = now

        return self.get_response(request)