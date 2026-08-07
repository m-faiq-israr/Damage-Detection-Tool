from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render

from .ai.quality_check import check_image_quality
from .ai.detector import detect_damage
from .ai.rim_detector import detect_rim_damage
from .ai.compare import compare_damage
from .ai.report import generate_report
from .pdf_report import generate_pdf

# =========================================================
# Parts
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
    # Rim categories
    "rim_front_right",
    "rim_front_left",
    "rim_rear_right",
    "rim_rear_left",
    "windshield",
]


# Parts handled by the Roboflow rim model
RIM_PARTS = [
    "rim_front_right",
    "rim_front_left",
    "rim_rear_right",
    "rim_rear_left",
]


# Everything except rims is handled by YOLO
BODY_PARTS = [part for part in PARTS if part not in RIM_PARTS]


# =========================================================
# Download PDF Report
# =========================================================


def download_report(request):

    inspection_results = request.session.get("inspection_results", {})

    return generate_pdf(inspection_results)


# =========================================================
# YOLO Detection Helper
# =========================================================


def process_body_part(part, saved_files, fs):
    """
    Process one vehicle body part using YOLO.

    Returns:
        (
            part,
            inspection_result
        )

    or None if either before/after image is missing.
    """

    before_key = f"before_{part}"
    after_key = f"after_{part}"

    # Both images are required
    if before_key not in saved_files or after_key not in saved_files:
        return None

    before_path = str(saved_files[before_key])

    after_path = str(saved_files[after_key])

    # -----------------------------------------------------
    # Create output paths for annotated images
    # -----------------------------------------------------

    before_path_obj = Path(before_path)
    after_path_obj = Path(after_path)

    before_output = str(
        before_path_obj.with_name(before_path_obj.stem + "_annotated.jpg")
    )

    after_output = str(after_path_obj.with_name(after_path_obj.stem + "_annotated.jpg"))

    # -----------------------------------------------------
    # YOLO detection - BEFORE
    # -----------------------------------------------------

    before_damage, before_annotated = detect_damage(before_path, before_output)

    # -----------------------------------------------------
    # YOLO detection - AFTER
    # -----------------------------------------------------

    after_damage, after_annotated = detect_damage(after_path, after_output)

    # -----------------------------------------------------
    # Compare BEFORE vs AFTER
    # -----------------------------------------------------

    new_damage = compare_damage(before_damage, after_damage)

    # -----------------------------------------------------
    # Return standardized result
    # -----------------------------------------------------

    return (
        part,
        {
            "before": before_damage,
            "after": after_damage,
            "new_damage": new_damage,
            # Used by HTML
            "before_annotated": fs.url(Path(before_output).name),
            "after_annotated": fs.url(Path(after_output).name),
            # Used by PDF generation
            "before_annotated_path": before_output,
            "after_annotated_path": after_output,
        },
    )


# =========================================================
# Rim Detection Helper
# =========================================================


def process_rim_part(part, saved_files, fs):

    before_key = f"before_{part}"
    after_key = f"after_{part}"

    if before_key not in saved_files or after_key not in saved_files:
        return None

    before_path = str(saved_files[before_key])

    after_path = str(saved_files[after_key])

    # ---------------------------------------------------------
    # Annotated output paths
    # ---------------------------------------------------------

    before_path_obj = Path(before_path)
    after_path_obj = Path(after_path)

    before_output = str(
        before_path_obj.with_name(before_path_obj.stem + "_annotated.jpg")
    )

    after_output = str(after_path_obj.with_name(after_path_obj.stem + "_annotated.jpg"))

    # ---------------------------------------------------------
    # Roboflow detection
    # ---------------------------------------------------------

    before_damage = detect_rim_damage(before_path, before_output)

    after_damage = detect_rim_damage(after_path, after_output)

    # ---------------------------------------------------------
    # Compare BEFORE vs AFTER
    # ---------------------------------------------------------

    new_damage = compare_damage(before_damage, after_damage)

    # ---------------------------------------------------------
    # Return results
    # ---------------------------------------------------------

    return (
        part,
        {
            "before": before_damage,
            "after": after_damage,
            "new_damage": new_damage,
            # HTML
            "before_annotated": fs.url(Path(before_output).name),
            "after_annotated": fs.url(Path(after_output).name),
            # PDF
            "before_annotated_path": before_output,
            "after_annotated_path": after_output,
        },
    )


# =========================================================
# Main Inspection View
# =========================================================


def index(request):

    uploaded = {}
    quality_errors = []
    inspection_results = {}
    json_report = ""

    if request.method == "POST":

        # =================================================
        # Step 1: Image Quality Check
        # =================================================

        for stage in ["before", "after"]:

            for part in PARTS:

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
        # Step 2: Save Images
        # =================================================

        if not quality_errors:

            fs = FileSystemStorage()

            saved_files = {}

            for stage in ["before", "after"]:

                for part in PARTS:

                    field = f"{stage}_{part}"

                    if field in request.FILES:

                        file = request.FILES[field]

                        filename = fs.save(file.name, file)

                        uploaded[field] = fs.url(filename)

                        saved_files[field] = Path(settings.MEDIA_ROOT) / filename

            # =================================================
            # Step 3: Parallel Detection
            # =================================================

            with ThreadPoolExecutor(max_workers=2) as executor:

                # -------------------------------------------------
                # Thread 1:
                # YOLO processes all vehicle body parts
                # -------------------------------------------------

                body_future = executor.submit(
                    lambda: [
                        process_body_part(part, saved_files, fs) for part in BODY_PARTS
                    ]
                )

                # -------------------------------------------------
                # Thread 2:
                # Roboflow processes all rim parts
                # -------------------------------------------------

                rim_future = executor.submit(
                    lambda: [
                        process_rim_part(part, saved_files, fs) for part in RIM_PARTS
                    ]
                )

                # Wait for YOLO results
                body_results = body_future.result()

                # Wait for Roboflow results
                rim_results = rim_future.result()

            # =================================================
            # Step 4: Merge Results
            # =================================================

            all_results = body_results + rim_results

            for result in all_results:

                if result is None:
                    continue

                part, data = result

                inspection_results[part] = data

            # =================================================
            # Step 5: Generate Report
            # =================================================

            json_report = generate_report(inspection_results)

            # =================================================
            # Step 6: Store Results in Session
            # =================================================

            request.session["inspection_results"] = inspection_results

    # =====================================================
    # Render UI
    # =====================================================

    return render(
        request,
        "inspections/index.html",
        {
            "uploaded": uploaded,
            "parts": PARTS,
            "quality_errors": quality_errors,
            "inspection_results": inspection_results,
            "json_report": json_report,
        },
    )
