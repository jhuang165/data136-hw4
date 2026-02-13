from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.utils import timezone
import datetime

from .models import UserProfile

def get_current_time():
    """Helper function to get current formatted time - 24-hour format with hours and minutes"""
    # Format: "HH:MM" in 24-hour format
    chicago_time = timezone.localtime(timezone.now())
    return chicago_time.strftime("%H:%M")

@require_GET
def index(request):
    """
    Main index page that displays:
    - Team bio
    - Current time (in HH:MM format)
    - Highlights logged in user's name
    """
    context = {
        'current_time': get_current_time(),
        'team_members': [
            {'name': 'John Smith', 'role': 'Lead Developer'},
            {'name': 'Jane Doe', 'role': 'Data Scientist'},
            {'name': 'Bob Johnson', 'role': 'Frontend Expert'},
        ]
    }
    
    return render(request, 'uncommondata/index.html', context)

@require_GET
def new_user_form(request):
    """
    Display the user creation form at /app/new/
    Only accepts GET requests, returns 405 for other methods
    """
    return render(request, 'uncommondata/new_user.html')

@require_http_methods(["POST"])
def create_user_api(request):
    """
    API endpoint to create a new user at /app/api/createUser/
    Requires POST with fields: email, user_name, password, is_curator
    """
    # Extract data from POST request
    email = request.POST.get('email', '').strip()
    username = request.POST.get('user_name', '').strip()
    password = request.POST.get('password', '')
    is_curator_str = request.POST.get('is_curator', '0')
    
    # Basic validation
    if not all([email, username, password]):
        return HttpResponseBadRequest("All fields (email, user_name, password) are required")
    
    # Check if email already exists
    if User.objects.filter(email=email).exists():
        return HttpResponseBadRequest(f"email {email} already in use")
    
    # Check if username already exists
    if User.objects.filter(username=username).exists():
        return HttpResponseBadRequest(f"username {username} already taken")
    
    try:
        # Convert is_curator to boolean
        is_curator = bool(int(is_curator_str))
        
        # Create the user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # Set the is_curator flag through the profile
        user.profile.is_curator = is_curator
        user.profile.save()
        
        # Log the user in automatically
        authenticated_user = authenticate(
            request, 
            username=username, 
            password=password
        )
        if authenticated_user:
            login(request, authenticated_user)
        
        return HttpResponse("success", status=201)
        
    except ValueError:
        return HttpResponseBadRequest("is_curator must be 0 or 1")
    except Exception as e:
        return HttpResponseBadRequest(f"Error creating user: {str(e)}")
