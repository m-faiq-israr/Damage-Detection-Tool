# api/auth.py

import os

from django.http import JsonResponse
from django.conf import settings


def require_api_key(request):

    authorization = request.headers.get("Authorization", "")

    if not authorization.startswith("Bearer "):

        return JsonResponse(
            {"error": "Authorization header required"},
            status=401,
        )

    token = authorization[7:].strip()

    expected_token = settings.AI_SERVICE_API_KEY

    if not expected_token:

        return JsonResponse(
            {"error": "API authentication is not configured"},
            status=500,
        )

    if token != expected_token:

        return JsonResponse(
            {"error": "Invalid API token"},
            status=401,
        )

    return None
