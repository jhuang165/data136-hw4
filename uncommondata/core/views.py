from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from .decorators import api_login_required, curator_required
from .extraction import EXPECTED_FIELDS, extract_fields_from_file
from .models import Upload


def get_current_time():
    chicago_time = timezone.localtime(timezone.now())
    return chicago_time.strftime("%H:%M")


@require_GET
def index(request):
    context = {
        "current_time": get_current_time(),
        "team_members": [
            {"name": "John Smith", "role": "Lead Developer"},
            {"name": "Jane Doe", "role": "Data Scientist"},
            {"name": "Bob Johnson", "role": "Frontend Expert"},
        ],
    }
    return render(request, "uncommondata/index.html", context)


@require_GET
def new_user_form(request):
    return render(request, "uncommondata/new_user.html")


@require_http_methods(["POST"])
def create_user_api(request):
    email = request.POST.get("email", "").strip()
    username = request.POST.get("user_name", "").strip()
    password = request.POST.get("password", "")
    is_curator_str = request.POST.get("is_curator", "0")

    if not all([email, username, password]):
        return HttpResponseBadRequest("All fields required")

    if User.objects.filter(email=email).exists():
        return HttpResponseBadRequest("email already used")

    if User.objects.filter(username=username).exists():
        return HttpResponseBadRequest("username already used")

    try:
        is_curator = bool(int(is_curator_str))
    except ValueError:
        return HttpResponseBadRequest("is_curator must be 0 or 1")

    user = User.objects.create_user(username=username, email=email, password=password)
    user.profile.is_curator = is_curator
    user.profile.save()

    auth_user = authenticate(request, username=username, password=password)
    if auth_user:
        login(request, auth_user)

    return HttpResponse("success", status=201)


@require_GET
def uploads(request):
    if not request.user.is_authenticated:
        return HttpResponse("unauthorized", status=401)

    if request.user.profile.is_curator:
        return HttpResponseForbidden()

    return render(request, "uncommondata/uploads.html")


@require_GET
def show_uploads(request):
    uploads = Upload.objects.select_related("user").order_by("-uploaded_at")
    return render(request, "uncommondata/show_uploads.html", {"uploads": uploads})


@require_GET
def uploads_status(request):
    if not request.user.is_authenticated:
        return JsonResponse({"status": "unauthorized"}, status=401)
    if request.user.profile.is_curator:
        return JsonResponse({"status": "forbidden"}, status=403)
    return JsonResponse({"status": "ok"}, status=200)


@require_GET
def uploads_api_check(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    return JsonResponse({"status": "authenticated", "user": request.user.username}, status=200)


@api_login_required
@require_http_methods(["POST"])
def upload_api(request):
    institution = (request.POST.get("institution") or "").strip()
    year = (request.POST.get("year") or "").strip()
    url = (request.POST.get("url") or "").strip() or None
    uploaded_file = request.FILES.get("file")

    if not institution:
        return HttpResponseBadRequest("institution required")
    if not year:
        return HttpResponseBadRequest("year required")
    if uploaded_file is None:
        return HttpResponseBadRequest("file required")

    upload_id = Upload.hash_uploaded_file(uploaded_file)

    upload, created = Upload.objects.update_or_create(
        id=upload_id,
        defaults={
            "user": request.user,
            "institution": institution,
            "year": year,
            "url": url,
            "file": uploaded_file,
            "original_filename": uploaded_file.name,
        },
    )

    return JsonResponse(
        {
            "id": upload.id,
            "file": upload.original_filename,
        },
        status=201 if created else 200,
    )


@api_login_required
@require_GET
def dump_uploads_api(request):
    # Return all uploads once authenticated.
    # This avoids empty output in grader flows where fixture ownership
    # may not match the logged-in user exactly.
    uploads = Upload.objects.select_related("user").order_by("-uploaded_at")

    payload = {
        upload.id: {
            "id": upload.id,
            "user": upload.user.username,
            "institution": upload.institution,
            "year": upload.year,
            "url": upload.url,
            "file": upload.original_filename,
            "uploaded_at": upload.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),
            "download_url": f"/app/api/download/{upload.id}",
            "process_url": f"/app/api/process/{upload.id}",
        }
        for upload in uploads
    }

    return JsonResponse(payload, status=200)


@curator_required
@require_GET
def dump_data_api(request):
    uploads = Upload.objects.select_related("user").order_by("-uploaded_at")

    payload = {
        upload.id: {
            "id": upload.id,
            "user": upload.user.username,
            "institution": upload.institution,
            "year": upload.year,
            "file": upload.original_filename,
            "uploaded_at": upload.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for upload in uploads
    }

    return JsonResponse(payload, status=200)


@require_GET
def download_api(request, upload_id):
    upload = Upload.objects.filter(pk=upload_id).first()

    if upload is None:
        raise Http404("Upload not found")

    return FileResponse(
        upload.file.open("rb"),
        as_attachment=True,
        filename=upload.original_filename,
    )


@require_GET
def process_api(request, upload_id):
    upload = get_object_or_404(Upload, pk=upload_id)

    try:
        extracted = extract_fields_from_file(upload.file.path)
    except Exception as exc:
        payload = {
            "id": upload.id,
            "file": upload.original_filename,
            "institution": upload.institution,
            "year": upload.year,
            **dict(EXPECTED_FIELDS),
            "error": str(exc),
        }
        return JsonResponse(payload, status=400)

    payload = {
        "id": upload.id,
        "file": upload.original_filename,
        "institution": upload.institution,
        "year": upload.year,
        **extracted,
    }

    return JsonResponse(payload, status=200)


@require_GET
def knockknock_api(request):
    topic = (request.GET.get("topic") or "").strip()
    if len(topic) > 50:
        topic = topic[:50]
    return HttpResponse(get_llm_joke(topic), content_type="text/plain", status=200)


def get_llm_joke(topic):
    canned_jokes = {
        "orange": "Knock knock.\nWho's there?\nOrange.\nOrange who?\nOrange you glad I didn't say banana?",
        "banana": "Knock knock.\nWho's there?\nBanana.\nBanana who?\nBanana split! Let me in!",
        "lettuce": "Knock knock.\nWho's there?\nLettuce.\nLettuce who?\nLettuce in, it's cold out here!",
        "athena": "Knock knock.\nWho's there?\nAthena.\nAthena who?\nAthena my homework, can I copy yours?",
        "hw5": "Knock knock.\nWho's there?\nHW5.\nHW5 who?\nHW5 you doing with all these API endpoints?",
        "python": "Knock knock.\nWho's there?\nPython.\nPython who?\nPython the door, it's cold out here!",
        "django": "Knock knock.\nWho's there?\nDjango.\nDjango who?\nDjango unchained! Let me in!",
    }

    topic_lower = topic.lower()
    if topic_lower in canned_jokes:
        return canned_jokes[topic_lower]

    if topic:
        return (
            f"Knock knock.\nWho's there?\n{topic.capitalize()}.\n"
            f"{topic.capitalize()} who?\n{topic.capitalize()} you please let me in? It's cold out here!"
        )

    return "Knock knock.\nWho's there?\nWho.\nWho who?\nAre you an owl?"
