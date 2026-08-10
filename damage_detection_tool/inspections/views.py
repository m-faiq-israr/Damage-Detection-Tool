from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render

from .ai.quality_check import check_image_quality
from .ai.detector import detect_damage
from .ai.rim_segmentation import get_rim_crop
from .ai.rim_detector import detect_rim_damage
from .ai.compare import compare_damage
from .ai.report import generate_report
from .pdf_report import generate_pdf
from .ai.interior_detector import detect_interior_damage

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


# =========================================================
# DOWNLOAD PDF REPORT
# =========================================================


def download_report(request):

    inspection_results = request.session.get("inspection_results", {})

    return generate_pdf(inspection_results)


# =========================================================
# MAIN VIEW
# =========================================================


def index(request):

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

                    # -----------------------------------------
                    # COMPARE
                    # -----------------------------------------

                    new_damage = compare_damage(before_damage, after_damage)

                    inspection_results[part] = {
                        "before": before_damage,
                        "after": after_damage,
                        "new_damage": new_damage,
                        "before_annotated": fs.url(Path(before_output).name),
                        "after_annotated": fs.url(Path(after_output).name),
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

                    # -----------------------------------------
                    # COMPARE
                    # -----------------------------------------

                    new_damage = compare_damage(before_damage, after_damage)

                    inspection_results[part] = {
                        "before": before_damage,
                        "after": after_damage,
                        "new_damage": new_damage,
                        "before_annotated": fs.url(Path(before_output).name),
                        "after_annotated": fs.url(Path(after_output).name),
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

                new_damage = compare_damage(before_damage, after_damage)

                inspection_results[part] = {
                    "before": before_damage,
                    "after": after_damage,
                    "new_damage": new_damage,
                    "before_annotated": fs.url(Path(before_output).name),
                    "after_annotated": fs.url(Path(after_output).name),
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
