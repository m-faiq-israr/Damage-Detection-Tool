import json
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.http import (
    Http404,
    HttpRequest,
    FileResponse,
    JsonResponse,
)
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .api.views import single_inspection_api, comparison_api

# =========================================================
# CONSTANTS
# =========================================================

EXTERIOR_ANGLES = [
    {"code": "front", "label": "Front"},
    {"code": "rear", "label": "Rear"},
    {"code": "left", "label": "Left"},
    {"code": "right", "label": "Right"},
    {"code": "front_left", "label": "Front Left"},
    {"code": "front_right", "label": "Front Right"},
    {"code": "rear_left", "label": "Rear Left"},
    {"code": "rear_right", "label": "Rear Right"},
]

BODY_SHAPES = [
    "sedan",
    "suv",
    "hatchback",
    "coupe",
    "convertible",
    "pickup_truck",
    "van",
]

UPLOAD_SUBDIR = "test_uploads"


# =========================================================
# PAGE
# =========================================================


def test_ui_page(request):

    return render(
        request,
        "inspections/test_ui.html",
        {
            "angles": EXTERIOR_ANGLES,
            "angles_json": json.dumps(EXTERIOR_ANGLES),
            "body_shapes": BODY_SHAPES,
        },
    )


# =========================================================
# UPLOAD
# =========================================================


@csrf_exempt
@require_POST
def test_ui_upload(request):

    file = request.FILES.get("file")

    if not file:

        return JsonResponse(
            {"error": "file is required"},
            status=400,
        )

    extension = Path(file.name).suffix or ".jpg"

    filename = f"{uuid4().hex}{extension}"

    upload_dir = Path(settings.MEDIA_ROOT) / UPLOAD_SUBDIR

    upload_dir.mkdir(parents=True, exist_ok=True)

    destination = upload_dir / filename

    with open(destination, "wb") as out_file:

        for chunk in file.chunks():
            out_file.write(chunk)

    url = request.build_absolute_uri(
        reverse(
            "test_ui_media",
            args=[filename],
        )
    )

    return JsonResponse({"url": url})


# =========================================================
# MEDIA SERVING (always on, independent of DEBUG)
# =========================================================


def test_ui_media(request, filename):

    safe_name = Path(filename).name

    file_path = Path(settings.MEDIA_ROOT) / UPLOAD_SUBDIR / safe_name

    if not file_path.exists():
        raise Http404

    return FileResponse(open(file_path, "rb"))


# =========================================================
# SUBMIT (proxies into the real API views, in-process)
# =========================================================


def _delete_uploaded_sources(payload):

    upload_dir = Path(settings.MEDIA_ROOT) / UPLOAD_SUBDIR

    image_lists = [
        payload.get("images", []),
        payload.get("baseline_images", []),
        payload.get("current_images", []),
    ]

    for image_list in image_lists:

        for image in image_list:

            url = image.get("url", "")

            if "/test-ui/media/" not in url:
                continue

            filename = Path(url.split("?")[0]).name

            try:
                (upload_dir / filename).unlink(missing_ok=True)
            except Exception:
                pass


@csrf_exempt
@require_POST
def test_ui_submit(request):

    try:
        payload = json.loads(request.body)
    except Exception:

        return JsonResponse(
            {"error": "Invalid JSON payload"},
            status=400,
        )

    walkaround_type = payload.pop("walkaround_type", "single")

    api_key = settings.AI_SERVICE_API_KEY

    if not api_key:

        return JsonResponse(
            {"error": "AI_SERVICE_API_KEY is not configured on the server"},
            status=500,
        )

    internal_request = HttpRequest()
    internal_request.method = "POST"
    internal_request._body = json.dumps(payload).encode("utf-8")
    internal_request.META["HTTP_AUTHORIZATION"] = f"Bearer {api_key}"
    internal_request.META["CONTENT_TYPE"] = "application/json"

    try:

        if walkaround_type == "comparison":
            response = comparison_api(internal_request)
        else:
            response = single_inspection_api(internal_request)

    except Exception as error:

        _delete_uploaded_sources(payload)

        return JsonResponse(
            {"error": f"Inspection pipeline failed: {error}"},
            status=500,
        )

    _delete_uploaded_sources(payload)

    return response
