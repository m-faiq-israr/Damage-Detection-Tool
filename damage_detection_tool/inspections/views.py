import os
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse
from django.shortcuts import render

from .ai.quality_check import check_image_quality
from .ai.detector import detect_damage
from .ai.rim_segmentation import get_rim_crop
from .ai.rim_detector import detect_rim_damage
from .ai.compare import compare_damage
from .ai.report import generate_report
from .pdf_report import generate_pdf
from .ai.interior_detector import detect_interior_damage
from .ai.single_detector import detect_single_image
from .storage import upload_file, get_file_url
from django.core.files.base import ContentFile

from .storage import upload_file, get_file_url

# =========================================================
# EXTERIOR PARTS
# =========================================================

PARTS = [
    "front",
    "rear",
    "left",
    "right",
    "front_right",
    "front_left",
    "rear_right",
    "rear_left",
    "rim_front_right",
    "rim_front_left",
    "rim_rear_right",
    "rim_rear_left",
    "windshield",
]


# =========================================================
# RIM PARTS
# =========================================================

RIM_PARTS = [
    "rim_front_right",
    "rim_front_left",
    "rim_rear_right",
    "rim_rear_left",
]


# =========================================================
# INTERIOR PARTS
# =========================================================

INTERIOR_PARTS = [
    "front_panel",
    "enter_driver",
    "enter_co_driver",
    "rear_row_seats",
    "trunk",
    "door_front_left",
    "door_front_right",
    "door_rear_left",
    "door_rear_right",
]

SINGLE_PARTS = [
    "front",
    "rear",
    "left",
    "right",
    "front_right",
    "front_left",
    "rear_right",
    "rear_left",
    "rim_front_right",
    "rim_front_left",
    "rim_rear_right",
    "rim_rear_left",
    "windshield",
    "front_panel",
    "enter_driver",
    "enter_co_driver",
    "rear_row_seats",
    "trunk",
    "front_left_door",
    "front_right_door",
    "rear_left_door",
    "rear_right_door",
]


def generate_request_id():
    return str(uuid.uuid4())


def upload_annotated_image(
    local_path,
    part,
    stage,
    request_id,
):
    """
    Upload an annotated image to Supabase
    and return its signed URL.
    """

    if not local_path:
        return None

    local_path = Path(local_path)

    if not local_path.exists():
        print(f"Supabase upload skipped. File not found: {local_path}")
        return None

    storage_path = (
        f"{request_id}/" f"analyzed-images/" f"{part}/" f"{stage}_{local_path.name}"
    )

    try:

        upload_file(
            local_path,
            storage_path,
            content_type="image/jpeg",
        )

        url = get_file_url(
            storage_path,
            expires_in=3600,
        )

        print("\n" + "=" * 60)
        print("SUPABASE IMAGE UPLOAD")
        print("=" * 60)
        print(f"Part       : {part}")
        print(f"Stage      : {stage}")
        print(f"Storage    : {storage_path}")
        print(f"URL        : {url}")
        print("=" * 60)

        return url

    except Exception as e:

        print("\n" + "=" * 60)
        print("SUPABASE IMAGE UPLOAD FAILED")
        print("=" * 60)
        print(f"File  : {local_path}")
        print(f"Error : {e}")
        print("=" * 60)

        return None


def download_report(request):

    report_type = request.GET.get("type", "comparison")

    request_id = request.session.get("request_id")

    if not request_id:
        return HttpResponse(
            "Request ID not found. Please run an inspection first.",
            status=400,
        )

    # =====================================================
    # SINGLE INSPECTION REPORT
    # =====================================================

    if report_type == "single":

        single_results = request.session.get("single_results", {})

        pdf_response = generate_pdf(single_results, report_type="single")

        storage_path = f"{request_id}/" f"report/" f"walkaround-report.pdf"

    # =====================================================
    # COMPARISON REPORT
    # =====================================================

    else:

        inspection_results = request.session.get("inspection_results", {})

        pdf_response = generate_pdf(inspection_results, report_type="comparison")

        storage_path = f"{request_id}/" f"report/" f"walkaround-report.pdf"
    # =====================================================
    # UPLOAD PDF TO SUPABASE
    # =====================================================

    try:

        # Get PDF bytes from HttpResponse
        pdf_bytes = pdf_response.content

        # Temporary local file
        temp_dir = Path(settings.MEDIA_ROOT) / "reports"

        temp_dir.mkdir(parents=True, exist_ok=True)

        if report_type == "single":

            local_pdf_path = (
                temp_dir / f"single_damage_report_" f"{request.session.session_key}.pdf"
            )

        else:

            local_pdf_path = (
                temp_dir / f"car_damage_comparison_report_"
                f"{request.session.session_key}.pdf"
            )

        # Save PDF locally
        with open(local_pdf_path, "wb") as pdf_file:

            pdf_file.write(pdf_bytes)

        # Upload to Supabase
        upload_file(
            local_pdf_path,
            storage_path,
            content_type="application/pdf",
        )

        # Generate signed URL
        pdf_url = get_file_url(
            storage_path,
            expires_in=3600,
        )

        # =================================================
        # CONSOLE LOG
        # =================================================

        print()
        print("=" * 60)

        if report_type == "single":

            print("SUPABASE SINGLE PDF UPLOAD SUCCESS")

        else:

            print("SUPABASE COMPARISON PDF UPLOAD SUCCESS")

        print("=" * 60)

        print("Storage Path:")
        print(storage_path)

        print()
        print("PDF URL:")
        print(pdf_url)

        print("=" * 60)
        print()

    except Exception as e:

        print()
        print("=" * 60)
        print("SUPABASE PDF UPLOAD FAILED")
        print("=" * 60)

        print("Error:", str(e))

        print("=" * 60)
        print()

    # =====================================================
    # RETURN PDF TO BROWSER
    # =====================================================

    return pdf_response


# =========================================================
# MAIN VIEW
# =========================================================


def index(request):

    if request.method == "POST":

        request_id = str(uuid.uuid4())

        request.session["request_id"] = request_id

    else:

        request_id = request.session.get("request_id", str(uuid.uuid4()))

    uploaded = {}
    quality_errors = []
    inspection_results = {}
    json_report = ""

    # =====================================================
    # POST REQUEST
    # =====================================================

    if request.method == "POST":

        # =================================================
        # STEP 1: QUALITY CHECK
        # =================================================

        # Exterior + Interior
        ALL_PARTS = PARTS + INTERIOR_PARTS

        for stage in ["before", "after"]:

            for part in ALL_PARTS:

                field = f"{stage}_{part}"

                if field in request.FILES:

                    file = request.FILES[field]

                    result = check_image_quality(file)

                    if not result["passed"]:

                        quality_errors.append(
                            {
                                "field": field,
                                "errors": result["errors"],
                            }
                        )

        # =================================================
        # STEP 2: SAVE IMAGES
        # =================================================

        if not quality_errors:

            fs = FileSystemStorage()

            saved_files = {}

            for stage in ["before", "after"]:

                for part in ALL_PARTS:

                    field = f"{stage}_{part}"

                    if field in request.FILES:

                        file = request.FILES[field]

                        filename = fs.save(file.name, file)

                        uploaded[field] = fs.url(filename)

                        saved_files[field] = Path(settings.MEDIA_ROOT) / filename

            # =================================================
            # STEP 3: EXTERIOR DAMAGE DETECTION
            # =================================================

            for part in PARTS:

                before_key = f"before_{part}"
                after_key = f"after_{part}"

                if before_key not in saved_files or after_key not in saved_files:
                    continue

                before_path = str(saved_files[before_key])

                after_path = str(saved_files[after_key])

                # =============================================
                # RIM PIPELINE
                # =============================================

                if part in RIM_PARTS:

                    print(f"\nProcessing rim: {part}")

                    # -----------------------------------------
                    # BEFORE RIM CROP
                    # -----------------------------------------

                    before_crop_output = str(
                        saved_files[before_key].with_name(
                            saved_files[before_key].stem + "_rim_crop.jpg"
                        )
                    )

                    before_rim = get_rim_crop(before_path, before_crop_output)

                    # -----------------------------------------
                    # AFTER RIM CROP
                    # -----------------------------------------

                    after_crop_output = str(
                        saved_files[after_key].with_name(
                            saved_files[after_key].stem + "_rim_crop.jpg"
                        )
                    )

                    after_rim = get_rim_crop(after_path, after_crop_output)

                    # -----------------------------------------
                    # CHECK RIM SEGMENTATION
                    # -----------------------------------------

                    if before_rim is None or after_rim is None:

                        print(
                            f"Skipping {part}: "
                            "rim not detected in "
                            "before or after image."
                        )

                        continue

                    # -----------------------------------------
                    # ANNOTATED IMAGE PATHS
                    # -----------------------------------------

                    before_output = str(
                        saved_files[before_key].with_name(
                            saved_files[before_key].stem + "_annotated.jpg"
                        )
                    )

                    after_output = str(
                        saved_files[after_key].with_name(
                            saved_files[after_key].stem + "_annotated.jpg"
                        )
                    )

                    # -----------------------------------------
                    # BEFORE RIM DAMAGE
                    # -----------------------------------------

                    before_damage = detect_rim_damage(
                        before_path,
                        before_crop_output,
                        before_output,
                        before_rim["x_offset"],
                        before_rim["y_offset"],
                    )

                    # -----------------------------------------
                    # AFTER RIM DAMAGE
                    # -----------------------------------------

                    after_damage = detect_rim_damage(
                        after_path,
                        after_crop_output,
                        after_output,
                        after_rim["x_offset"],
                        after_rim["y_offset"],
                    )

                    before_supabase_url = upload_annotated_image(
                        before_output,
                        part,
                        "before",
                        request_id=request_id,
                    )

                    after_supabase_url = upload_annotated_image(
                        after_output,
                        part,
                        "after",
                        request_id=request_id,
                    )

                    # -----------------------------------------
                    # COMPARE
                    # -----------------------------------------

                    new_damage = compare_damage(before_damage, after_damage)

                    inspection_results[part] = {
                        "before": before_damage,
                        "after": after_damage,
                        "new_damage": new_damage,
                        "before_annotated": before_supabase_url,
                        "after_annotated": after_supabase_url,
                        "before_annotated_path": before_output,
                        "after_annotated_path": after_output,
                    }

                # =============================================
                # NORMAL YOLO PIPELINE
                # =============================================

                else:

                    before_output = str(
                        saved_files[before_key].with_name(
                            saved_files[before_key].stem + "_annotated.jpg"
                        )
                    )

                    after_output = str(
                        saved_files[after_key].with_name(
                            saved_files[after_key].stem + "_annotated.jpg"
                        )
                    )

                    # -----------------------------------------
                    # YOLO BEFORE
                    # -----------------------------------------

                    before_damage, before_annotated = detect_damage(
                        before_path, before_output
                    )

                    # -----------------------------------------
                    # YOLO AFTER
                    # -----------------------------------------

                    after_damage, after_annotated = detect_damage(
                        after_path, after_output
                    )

                    before_supabase_url = upload_annotated_image(
                        before_annotated,
                        part,
                        "before",
                        request_id=request_id,
                    )

                    after_supabase_url = upload_annotated_image(
                        after_annotated,
                        part,
                        "after",
                        request_id=request_id,
                    )

                    # -----------------------------------------
                    # COMPARE
                    # -----------------------------------------

                    new_damage = compare_damage(before_damage, after_damage)

                    inspection_results[part] = {
                        "before": before_damage,
                        "after": after_damage,
                        "new_damage": new_damage,
                        "before_annotated": before_supabase_url,
                        "after_annotated": after_supabase_url,
                        "before_annotated_path": before_output,
                        "after_annotated_path": after_output,
                    }

            # =================================================
            # STEP 4: INTERIOR IMAGES
            # =================================================

            for part in INTERIOR_PARTS:

                before_key = f"before_{part}"
                after_key = f"after_{part}"

                if before_key not in saved_files and after_key not in saved_files:
                    continue

                before_path = str(saved_files[before_key])

                after_path = str(saved_files[after_key])

                print()
                print("=" * 60)
                print(f"PROCESSING INTERIOR PART: {part.upper()}")
                print("=" * 60)

                # ---------------------------------------------
                # Annotated image paths
                # ---------------------------------------------

                before_output = str(
                    saved_files[before_key].with_name(
                        saved_files[before_key].stem + "_interior_annotated.jpg"
                    )
                )

                after_output = str(
                    saved_files[after_key].with_name(
                        saved_files[after_key].stem + "_interior_annotated.jpg"
                    )
                )

                before_damage = detect_interior_damage(before_path, before_output)

                after_damage = detect_interior_damage(after_path, after_output)

                before_supabase_url = upload_annotated_image(
                    before_output,
                    part,
                    "before",
                    request_id=request_id,
                )

                after_supabase_url = upload_annotated_image(
                    after_output,
                    part,
                    "after",
                    request_id=request_id,
                )

                new_damage = compare_damage(before_damage, after_damage)

                inspection_results[part] = {
                    "before": before_damage,
                    "after": after_damage,
                    "new_damage": new_damage,
                    "before_annotated": before_supabase_url,
                    "after_annotated": after_supabase_url,
                    "before_annotated_path": before_output,
                    "after_annotated_path": after_output,
                    "interior": True,
                }

            # =================================================
            # STEP 5: GENERATE REPORT
            # =================================================

            json_report = generate_report(inspection_results)

            # Store results in session for PDF
            request.session["inspection_results"] = inspection_results

    return render(
        request,
        "inspections/index.html",
        {
            "uploaded": uploaded,
            # Exterior
            "parts": PARTS,
            # Interior
            "interior_parts": INTERIOR_PARTS,
            # Results
            "quality_errors": quality_errors,
            "inspection_results": inspection_results,
            "json_report": json_report,
        },
    )


def single_inspection(request):

    if request.method == "POST":

        request_id = str(uuid.uuid4())

        request.session["request_id"] = request_id

    else:

        request_id = request.session.get("request_id", str(uuid.uuid4()))

    uploaded = {}
    quality_errors = []
    single_results = {}
    json_report = ""

    if request.method == "POST":

        # =====================================================
        # STEP 1: QUALITY CHECK
        # =====================================================

        for part in SINGLE_PARTS:

            field = f"single_{part}"

            if field not in request.FILES:
                continue

            file = request.FILES[field]

            result = check_image_quality(file)

            if not result["passed"]:

                quality_errors.append(
                    {
                        "field": field,
                        "errors": result["errors"],
                    }
                )

        # =====================================================
        # STEP 2: SAVE + DETECT
        # =====================================================

        if not quality_errors:

            fs = FileSystemStorage()

            for part in SINGLE_PARTS:

                field = f"single_{part}"

                if field not in request.FILES:
                    continue

                file = request.FILES[field]

                filename = fs.save(file.name, file)

                uploaded[field] = fs.url(filename)

                image_path = Path(settings.MEDIA_ROOT) / filename

                output_path = str(
                    image_path.with_name(image_path.stem + "_single_annotated.jpg")
                )

                # =================================================
                # DETECT DAMAGE
                # =================================================

                result = detect_single_image(
                    part,
                    str(image_path),
                    output_path,
                )

                # =====================================================
                # UPLOAD ANNOTATED IMAGE TO SUPABASE
                # =====================================================

                supabase_annotated_url = None

                if result["annotated_path"]:

                    try:

                        annotated_path = Path(result["annotated_path"])

                        storage_path = (
                            f"{request_id}/"
                            f"analyzed_images/"
                            f"{part}/"
                            f"{filename}"
                        )

                        upload_file(
                            annotated_path,
                            storage_path,
                            content_type="image/jpeg",
                        )

                        supabase_annotated_url = get_file_url(storage_path)

                        print()
                        print("=" * 60)
                        print("SUPABASE SINGLE INSPECTION IMAGE UPLOAD")
                        print("=" * 60)
                        print(f"Part       : {part}")
                        print(f"Storage    : {storage_path}")
                        print(f"URL        : {supabase_annotated_url}")
                        print("=" * 60)

                    except Exception as e:

                        print()
                        print("=" * 60)
                        print("SUPABASE SINGLE INSPECTION IMAGE UPLOAD FAILED")
                        print("=" * 60)
                        print(f"File  : {result['annotated_path']}")
                        print(f"Error : {e}")
                        print("=" * 60)

                annotated_url = None

                if result["annotated_path"]:

                    annotated_url = fs.url(Path(result["annotated_path"]).name)

                single_results[part] = {
                    "damage": result["damage"],
                    "annotated": annotated_url,
                    "annotated_path": result["annotated_path"],
                    "supabase_annotated_url": supabase_annotated_url,
                    "pipeline": result["pipeline"],
                }

            # =====================================================
            # STEP 3: GENERATE JSON REPORT
            # =====================================================

            json_report = generate_report(single_results)

            # =====================================================
            # STEP 4: SAVE TO SESSION
            # =====================================================

            request.session["single_results"] = single_results

            request.session["single_json_report"] = json_report

            request.session.modified = True

    return render(
        request,
        "inspections/single_inspection.html",
        {
            "single_parts": SINGLE_PARTS,
            "uploaded": uploaded,
            "single_results": single_results,
            "quality_errors": quality_errors,
            "json_report": json_report,
        },
    )
