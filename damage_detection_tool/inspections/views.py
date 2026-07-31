from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from httpx import request
from .ai.quality_check import check_image_quality

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

    if request.method == "POST":

    # ---------- Check all images first ----------

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

    # ---------- Only save if ALL images passed ----------

        if not quality_errors:

            fs = FileSystemStorage()

            for stage in ["before", "after"]:
                for part in PARTS:

                    field = f"{stage}_{part}"

                    if field in request.FILES:

                        file = request.FILES[field]

                        filename = fs.save(file.name, file)

                        uploaded[field] = fs.url(filename)

    return render(
        request,
        "inspections/index.html",
        {
            "uploaded": uploaded,
            "parts": PARTS,
            "quality_errors": quality_errors,
        },
    )