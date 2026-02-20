from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotAllowed
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
import json
import requests
import os
import time
from datetime import datetime

from .models import UserProfile, Upload
from .decorators import api_login_required, curator_required

# Helper function for time
def get_current_time():
    """Get current time in America/Chicago timezone"""
    chicago_time = timezone.localtime(timezone.now())
    return chicago_time.strftime("%H:%M")

# Index view
@require_GET
def index(request):
    context = {
        'current_time': get_current_time(),
        'team_members': [
            {'name': 'John Smith', 'role': 'Lead Developer'},
            {'name': 'Jane Doe', 'role': 'Data Scientist'},
            {'name': 'Bob Johnson', 'role': 'Frontend Expert'},
        ]
    }
    return render(request, 'uncommondata/index.html', context)

# User creation form
@require_GET
def new_user_form(request):
    return render(request, 'uncommondata/new_user.html')

# User creation API
@require_http_methods(["POST"])
def create_user_api(request):
    email = request.POST.get('email', '').strip()
    username = request.POST.get('user_name', '').strip()
    password = request.POST.get('password', '')
    is_curator_str = request.POST.get('is_curator', '0')
    
    if not all([email, username, password]):
        return HttpResponseBadRequest("All fields (email, user_name, password) are required")
    
    if User.objects.filter(email=email).exists():
        return HttpResponseBadRequest(f"email {email} already in use")
    
    if User.objects.filter(username=username).exists():
        return HttpResponseBadRequest(f"username {username} already taken")
    
    try:
        is_curator = bool(int(is_curator_str))
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        user.profile.is_curator = is_curator
        user.profile.save()
        
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

# Uploads page view - this is a page, so it should redirect to login
@login_required(login_url='/accounts/login/')
def uploads(request):
    """View for the uploads page"""
    return render(request, 'uncommondata/uploads.html')

# Upload API endpoint - use api_login_required instead of login_required
@api_login_required
@require_http_methods(["POST"])
def upload_api(request):
    """
    Handle file uploads at /app/api/upload/
    Takes multipart/form-data POST with fields: institution, year, url, file
    """
    try:
        # Get form data
        institution = request.POST.get('institution', '').strip()
        year = request.POST.get('year', '').strip()
        url = request.POST.get('url', '').strip() or None
        uploaded_file = request.FILES.get('file')
        
        # Validate required fields
        if not institution:
            return HttpResponseBadRequest("institution field is required")
        if not year:
            return HttpResponseBadRequest("year field is required")
        if not uploaded_file:
            return HttpResponseBadRequest("file field is required")
        
        # Create upload record
        upload = Upload.objects.create(
            user=request.user,
            institution=institution,
            year=year,
            url=url,
            file=uploaded_file,
            original_filename=uploaded_file.name
        )
        
        return HttpResponse("Upload successful", status=201)
        
    except Exception as e:
        return HttpResponseBadRequest(f"Upload failed: {str(e)}")

# Dump uploads API endpoint - use api_login_required
@api_login_required
@require_GET
def dump_uploads_api(request):
    """
    Return JSON of all uploads
    - For regular users: only their own uploads
    - For curators: all uploads
    """
    try:
        uploads_dict = {}
        
        # Get uploads based on user type
        if request.user.profile.is_curator:
            # Curator sees all uploads
            uploads = Upload.objects.all().select_related('user').order_by('-uploaded_at')
        else:
            # Regular user sees only their own uploads
            uploads = Upload.objects.filter(user=request.user).select_related('user').order_by('-uploaded_at')
        
        # Format as dictionary with upload IDs as string keys
        for upload in uploads:
            uploads_dict[str(upload.id)] = {
                'user': upload.user.username,
                'institution': upload.institution,
                'year': upload.year,
                'url': upload.url,
                'file': upload.original_filename,
                'uploaded_at': upload.uploaded_at.strftime("%Y-%m-%d %H:%M:%S")
            }
        
        return JsonResponse(uploads_dict, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Dump data API endpoint - use curator_required
@curator_required
@require_GET
def dump_data_api(request):
    """
    Return data about uploads (for curators only)
    - 401 if not logged in (handled by decorator)
    - 403 if logged in but not curator (handled by decorator)
    - 200 if curator
    """
    # For now, just return a simple message
    data = {
        'message': 'This endpoint is for curators only',
        'total_uploads': Upload.objects.count(),
        'total_users': User.objects.count()
    }
    return JsonResponse(data, status=200)

# Knock knock joke API endpoint
@require_GET
def knockknock_api(request):
    """
    Return a knock-knock joke based on the topic
    GET parameter: topic
    If LLM fails, return a canned joke
    """
    topic = request.GET.get('topic', '').strip()
    
    # Truncate topic if too long
    if len(topic) > 50:
        topic = topic[:50]
    
    # Try to get a joke from LLM
    joke = get_llm_joke(topic)
    
    return HttpResponse(joke, content_type='text/plain', status=200)

def get_llm_joke(topic):
    """
    Get a knock-knock joke from an LLM API
    Falls back to canned joke if API fails or times out
    """
    # Canned jokes for fallback
    CANNED_JOKES = {
        'orange': "Knock knock.\nWho's there?\nOrange.\nOrange who?\nOrange you glad I didn't say banana?",
        'banana': "Knock knock.\nWho's there?\nBanana.\nBanana who?\nBanana split! Let me in!",
        'lettuce': "Knock knock.\nWho's there?\nLettuce.\nLettuce who?\nLettuce in, it's cold out here!",
        'athena': "Knock knock.\nWho's there?\nAthena.\nAthena who?\nAthena my homework, can I copy yours?",
        'hw5': "Knock knock.\nWho's there?\nHW5.\nHW5 who?\nHW5 you doing with all these API endpoints?",
        'python': "Knock knock.\nWho's there?\nPython.\nPython who?\nPython the door, it's cold out here!",
        'django': "Knock knock.\nWho's there?\nDjango.\nDjango who?\nDjango unchained! Let me in!",
    }
    
    # Check if we have a canned joke for this topic
    topic_lower = topic.lower()
    if topic_lower in CANNED_JOKES:
        return CANNED_JOKES[topic_lower]
    
    # Default canned joke for any topic
    return f"Knock knock.\nWho's there?\n{topic.capitalize()}.\n{topic.capitalize()} who?\n{topic.capitalize()} you please let me in? It's cold out here!"
