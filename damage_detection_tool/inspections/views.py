from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render

from .ai.quality_check import check_image_quality
from .ai.detector import detect_damage
from .ai.compare import compare_damage
from .ai.report import generate_report


PARTS = [
    "front",
    "rear",
    "left",
    "right",
    "bonnet",
    "trunk",
]


def index(request):

    uploaded = {}
    quality_errors = []
    inspection_results = {}
    json_report = ""

    if request.method == "POST":

        # ----------------------------
        # Step 1: Quality Check
        # ----------------------------

        for stage in ["before", "after"]:

            for part in PARTS:

                field = f"{stage}_{part}"

                if field in request.FILES:

                    file = request.FILES[field]

                    result = check_image_quality(file)

                    if not result["passed"]:

                        quality_errors.append({
                            "field": field,
                            "errors": result["errors"]
                        })

        # ----------------------------
        # Step 2: Save Images
        # ----------------------------

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

                        saved_files[field] = Path(
                            settings.MEDIA_ROOT
                        ) / filename

            # ----------------------------
            # Step 3: YOLO Detection
            # ----------------------------

            for part in PARTS:

                before_key = f"before_{part}"
                after_key = f"after_{part}"

                if (
                    before_key not in saved_files
                    or after_key not in saved_files
                ):
                    continue

                before_path = str(saved_files[before_key])
                after_path = str(saved_files[after_key])

                before_damage = detect_damage(before_path)
                after_damage = detect_damage(after_path)

                new_damage = compare_damage(
                    before_damage,
                    after_damage
                )

                inspection_results[part] = {
                    "before": before_damage,
                    "after": after_damage,
                    "new_damage": new_damage,
                }

            # ----------------------------
            # Step 4: JSON Report
            # ----------------------------

            json_report = generate_report(
                inspection_results
            )

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