import shutil
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ..ai.report import generate_report
from ..pdf_report import generate_pdf

from ..storage import upload_file, get_file_url

from .pipeline import (
    process_single_image,
    process_comparison_part,
    PART_CODES,
    INTERIOR_PARTS,
)
from .auth import require_api_key

# =========================================================
# HELPERS
# =========================================================


def get_severity(confidence):

    confidence = float(confidence)

    if confidence >= 0.85:
        return "high"

    if confidence >= 0.60:
        return "medium"

    return "low"


def build_single_response(
    request_id,
    vehicle_id,
    tenant_id,
    kind,
    body_shape,
    part_catalog_version,
    results,
    report_url,
):

    parts = []

    for result in results:

        part = result["part"]

        damage_list = result.get(
            "damage",
            [],
        )

        for damage in damage_list:

            confidence = float(
                damage.get(
                    "confidence",
                    0,
                )
            )

            damage_type = damage.get(
                "type",
                damage.get(
                    "damage_type",
                    "Damage",
                ),
            )

            parts.append(
                {
                    "part_code": PART_CODES.get(
                        part,
                        "UNKNOWN",
                    ),
                    "area": ("interior" if part in INTERIOR_PARTS else "exterior"),
                    "probability": round(confidence * 100),
                    "severity": get_severity(confidence),
                    "label": damage_type,
                    "annotated_image_url": result.get("annotated_url"),
                }
            )

    return {
        "request_id": request_id,
        "vehicle_id": vehicle_id,
        "tenant_id": tenant_id,
        "kind": kind,
        "body_shape": body_shape,
        "part_catalog_version": part_catalog_version,
        "parts": parts,
        "report url": report_url,
    }


# =========================================================
# SINGLE INSPECTION API
# =========================================================


def build_comparison_response(
    request_id,
    vehicle_id,
    tenant_id,
    kind,
    body_shape,
    part_catalog_version,
    results,
    report_url,
):

    parts = []

    for result in results:

        part = result["part"]

        new_damage_list = result.get(
            "new_damage",
            [],
        )

        for damage in new_damage_list:

            confidence = float(
                damage.get(
                    "confidence",
                    0,
                )
            )

            damage_type = damage.get(
                "type",
                damage.get(
                    "damage_type",
                    "Damage",
                ),
            )

            parts.append(
                {
                    "part_code": PART_CODES.get(
                        part,
                        "UNKNOWN",
                    ),
                    "area": ("interior" if part in INTERIOR_PARTS else "exterior"),
                    "probability": round(confidence * 100),
                    "severity": get_severity(confidence),
                    "label": damage_type,
                    # We only return new damage.
                    "change": "new",
                    # Use the CURRENT/AFTER annotated image.
                    "annotated_image_url": result.get("after_annotated_url"),
                }
            )

    return {
        "request_id": request_id,
        "vehicle_id": vehicle_id,
        "tenant_id": tenant_id,
        "kind": kind,
        "body_shape": body_shape,
        "part_catalog_version": part_catalog_version,
        "parts": parts,
        "report url": report_url,
    }


@csrf_exempt
@require_POST
def single_inspection_api(request):

    auth_error = require_api_key(request)

    if auth_error:
        return auth_error

    try:

        import json

        payload = json.loads(request.body)

    except Exception:

        return JsonResponse(
            {"error": "Invalid JSON payload"},
            status=400,
        )

    # =====================================================
    # REQUEST ID
    # =====================================================

    request_id = payload.get("request_id")
    vehicle_id = payload.get("vehicle_id")
    tenant_id = payload.get("tenant_id")
    kind = payload.get("kind")
    body_shape = payload.get("body_shape")
    part_catalog_version = payload.get("part_catalog_version")

    if not request_id:

        return JsonResponse(
            {"error": "request_id is required"},
            status=400,
        )

    # =====================================================
    # IMAGES
    # =====================================================

    images = payload.get(
        "images",
        [],
    )

    if not isinstance(images, list):

        return JsonResponse(
            {"error": "images must be an array"},
            status=400,
        )

    # =====================================================
    # PROCESS
    # =====================================================

    results = []

    for image in images:

        angle_code = image.get("angle_code")

        image_url = image.get("url")

        if not angle_code:

            continue

        if not image_url:

            continue

        print()
        print("=" * 60)
        print(f"PROCESSING SINGLE IMAGE: {angle_code}")
        print("=" * 60)

        result = process_single_image(
            request_id=request_id,
            part=angle_code,
            image_url=image_url,
        )

        results.append(result)

    # =====================================================
    # GENERATE REPORT DATA
    # =====================================================

    report_results = {}

    for result in results:

        report_results[result["part"]] = {
            "damage": result.get(
                "damage",
                [],
            ),
            "annotated_path": result.get("annotated_path"),
        }

    json_report = generate_report(report_results)

    # =====================================================
    # GENERATE PDF
    # =====================================================

    pdf_response = generate_pdf(
        report_results,
        report_type="single",
    )

    # =====================================================
    # SAVE PDF LOCALLY
    # =====================================================

    reports_dir = Path(settings.MEDIA_ROOT) / "api_reports"

    reports_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    pdf_path = reports_dir / f"{request_id}_walkaround-report.pdf"

    with open(
        pdf_path,
        "wb",
    ) as file:

        file.write(pdf_response.content)

    # =====================================================
    # UPLOAD PDF
    # =====================================================

    storage_path = f"{request_id}/" f"report/" f"walkaround-report.pdf"

    upload_file(
        pdf_path,
        storage_path,
        content_type="application/pdf",
    )

    report_url = get_file_url(
        storage_path,
        expires_in=3600,
    )

    print()
    print("=" * 60)
    print("SUPABASE PDF UPLOAD SUCCESS")
    print("=" * 60)
    print("Request ID:", request_id)
    print("Report URL:", report_url)
    print("=" * 60)

    try:

        if pdf_path.exists():

            pdf_path.unlink()

            print()
            print("=" * 60)
            print("LOCAL PDF DELETED")
            print("=" * 60)
            print("Deleted:", pdf_path)
            print("=" * 60)

    except Exception as e:

        print()
        print("=" * 60)
        print("LOCAL PDF DELETE FAILED")
        print("=" * 60)
        print("File:", pdf_path)
        print("Error:", str(e))
        print("=" * 60)

    # =====================================================
    # BUILD RESPONSE
    # =====================================================

    response_data = build_single_response(
        request_id=request_id,
        vehicle_id=vehicle_id,
        tenant_id=tenant_id,
        kind=kind,
        body_shape=body_shape,
        part_catalog_version=part_catalog_version,
        results=results,
        report_url=report_url,
    )

    # =====================================================
    # CLEAN TEMPORARY LOCAL FILES
    # =====================================================

    job_dir = Path(settings.MEDIA_ROOT) / "api" / str(request_id)

    try:

        if job_dir.exists():

            shutil.rmtree(job_dir)

            print()
            print("=" * 60)
            print("TEMPORARY FILES DELETED")
            print("=" * 60)
            print("Deleted:", job_dir)
            print("=" * 60)

    except Exception as e:

        print()
        print("=" * 60)
        print("TEMPORARY FILE CLEANUP FAILED")
        print("=" * 60)
        print("Error:", str(e))
        print("=" * 60)

    # =====================================================
    # PRINT JSON
    # =====================================================

    print()
    print("=" * 60)
    print("FINAL API RESPONSE")
    print("=" * 60)

    import json

    print(
        json.dumps(
            response_data,
            indent=4,
        )
    )

    print("=" * 60)

    return JsonResponse(
        response_data,
        status=200,
    )


@csrf_exempt
@require_POST
def comparison_api(request):

    auth_error = require_api_key(request)

    if auth_error:
        return auth_error

    try:

        import json

        payload = json.loads(request.body)

    except Exception:

        return JsonResponse(
            {"error": "Invalid JSON payload"},
            status=400,
        )

    # =====================================================
    # REQUIRED REQUEST FIELDS
    # =====================================================

    required_fields = [
        "request_id",
        "vehicle_id",
        "tenant_id",
        "kind",
        "body_shape",
        "part_catalog_version",
        "baseline_images",
        "current_images",
    ]

    for field in required_fields:

        if field not in payload:

            return JsonResponse(
                {"error": f"{field} is required"},
                status=400,
            )

    # =====================================================
    # REQUEST VALUES
    # =====================================================

    request_id = payload["request_id"]

    vehicle_id = payload["vehicle_id"]

    tenant_id = payload["tenant_id"]

    kind = payload["kind"]

    body_shape = payload["body_shape"]

    part_catalog_version = payload["part_catalog_version"]

    baseline_images = payload["baseline_images"]

    current_images = payload["current_images"]

    # =====================================================
    # VALIDATE IMAGE ARRAYS
    # =====================================================

    if not isinstance(
        baseline_images,
        list,
    ):

        return JsonResponse(
            {"error": ("baseline_images " "must be an array")},
            status=400,
        )

    if not isinstance(
        current_images,
        list,
    ):

        return JsonResponse(
            {"error": ("current_images " "must be an array")},
            status=400,
        )

    # =====================================================
    # MAP IMAGES BY ANGLE CODE
    # =====================================================

    baseline_map = {}

    for image in baseline_images:

        angle_code = image.get("angle_code")

        url = image.get("url")

        if angle_code and url:

            baseline_map[angle_code] = url

    current_map = {}

    for image in current_images:

        angle_code = image.get("angle_code")

        url = image.get("url")

        if angle_code and url:

            current_map[angle_code] = url

    # =====================================================
    # FIND COMMON PARTS
    # =====================================================

    common_parts = set(baseline_map.keys()) & set(current_map.keys())

    if not common_parts:

        return JsonResponse(
            {
                "error": (
                    "No matching angle_code "
                    "found between "
                    "baseline_images and "
                    "current_images"
                )
            },
            status=400,
        )

    # =====================================================
    # PROCESS
    # =====================================================

    results = []

    for part in sorted(common_parts):

        print()
        print("=" * 60)
        print(f"PROCESSING COMPARISON: " f"{part}")
        print("=" * 60)

        result = process_comparison_part(
            request_id=request_id,
            part=part,
            baseline_url=baseline_map[part],
            current_url=current_map[part],
        )

        results.append(result)

    # =====================================================
    # GENERATE REPORT DATA
    # =====================================================

    report_results = {}

    for result in results:

        report_results[result["part"]] = {
            "before": result.get(
                "before",
                [],
            ),
            "after": result.get(
                "after",
                [],
            ),
            "new_damage": result.get(
                "new_damage",
                [],
            ),
            "before_annotated_path": result.get("before_annotated_path"),
            "after_annotated_path": result.get("after_annotated_path"),
        }

    # =====================================================
    # GENERATE PDF
    # =====================================================

    pdf_response = generate_pdf(
        report_results,
        report_type="comparison",
    )

    # =====================================================
    # SAVE PDF LOCALLY
    # =====================================================

    reports_dir = Path(settings.MEDIA_ROOT) / "api_reports"

    reports_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    pdf_path = reports_dir / f"{request_id}_walkaround-report.pdf"

    with open(
        pdf_path,
        "wb",
    ) as file:

        file.write(pdf_response.content)

    # =====================================================
    # UPLOAD PDF
    # =====================================================

    storage_path = f"{request_id}/" f"report/" f"walkaround-report.pdf"

    upload_file(
        pdf_path,
        storage_path,
        content_type="application/pdf",
    )

    report_url = get_file_url(
        storage_path,
        expires_in=3600,
    )

    print()
    print("=" * 60)
    print("SUPABASE COMPARISON PDF UPLOAD SUCCESS")
    print("=" * 60)

    print(
        "Request ID:",
        request_id,
    )

    print(
        "Report URL:",
        report_url,
    )

    print("=" * 60)

    # =====================================================
    # DELETE LOCAL PDF
    # =====================================================

    try:

        if pdf_path.exists():

            pdf_path.unlink()

            print()
            print("=" * 60)
            print("LOCAL COMPARISON PDF DELETED")
            print("=" * 60)
            print("Deleted:", pdf_path)
            print("=" * 60)

    except Exception as e:

        print()
        print("=" * 60)
        print("COMPARISON PDF DELETE FAILED")
        print("=" * 60)
        print("File:", pdf_path)
        print("Error:", str(e))
        print("=" * 60)

    # =====================================================
    # BUILD RESPONSE
    # =====================================================

    response_data = build_comparison_response(
        request_id=request_id,
        vehicle_id=vehicle_id,
        tenant_id=tenant_id,
        kind=kind,
        body_shape=body_shape,
        part_catalog_version=(part_catalog_version),
        results=results,
        report_url=report_url,
    )

    # DELETE ALL TEMPORARY IMAGES
    job_dir = Path(settings.MEDIA_ROOT) / "api" / str(request_id)

    try:

        if job_dir.exists():
            shutil.rmtree(job_dir)

            print("TEMPORARY COMPARISON FILES DELETED:", job_dir)

    except Exception as e:
        print("COMPARISON IMAGE CLEANUP FAILED:", e)

    # =====================================================
    # PRINT RESPONSE
    # =====================================================

    import json

    print()
    print("=" * 60)
    print("FINAL COMPARISON API RESPONSE")
    print("=" * 60)

    print(
        json.dumps(
            response_data,
            indent=4,
        )
    )

    print("=" * 60)

    return JsonResponse(
        response_data,
        status=200,
    )
