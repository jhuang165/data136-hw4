from functools import wraps
from django.http import JsonResponse

def api_login_required(view_func):
    """
    Decorator for API views that returns 401 instead of redirecting to login page
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "Authentication required"}, 
                status=401
            )
        return view_func(request, *args, **kwargs)
    return wrapper

def curator_required(view_func):
    """
    Decorator for views that require curator status
    Returns 401 if not logged in, 403 if not curator
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "Authentication required"}, 
                status=401
            )
        if not request.user.profile.is_curator:
            return JsonResponse(
                {"error": "Curator privileges required"}, 
                status=403
            )
        return view_func(request, *args, **kwargs)
    return wrapper
