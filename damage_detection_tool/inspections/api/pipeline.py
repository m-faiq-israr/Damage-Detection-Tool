from pathlib import Path
from uuid import uuid4
import requests

from django.conf import settings
from django.core.files.storage import FileSystemStorage

from ..ai.detector import detect_damage
from ..ai.rim_segmentation import get_rim_crop
from ..ai.rim_detector import detect_rim_damage
from ..ai.interior_detector import detect_interior_damage
from ..ai.compare import compare_damage
from ..ai.quality_check import check_image_quality
from ..storage import upload_file, get_file_url

# =========================================================
# PART DEFINITIONS
# =========================================================

EXTERIOR_PARTS = {
    "front",
    "rear",
    "left",
    "right",
    "front_left",
    "front_right",
    "rear_left",
    "rear_right",
}

RIM_PARTS = {
    "rim_front_left",
    "rim_front_right",
    "rim_rear_left",
    "rim_rear_right",
}

INTERIOR_PARTS = {
    "front_panel",
    "enter_driver",
    "enter_co_driver",
    "rear_row_seats",
    "trunk",
    "door_front_left",
    "door_front_right",
    "door_rear_left",
    "door_rear_right",
}


PART_CODES = {
    "rim_front_left": "A09",
    "rim_front_right": "A10",
    "rim_rear_left": "A11",
    "rim_rear_right": "A12",
    "front_panel": "AI01",
    "enter_driver": "AI02",
    "enter_co_driver": "AI03",
    "rear_row_seats": "AI04",
    "trunk": "AI05",
    "door_front_left": "AI06",
    "door_front_right": "AI07",
    "door_rear_left": "AI08",
    "door_rear_right": "AI09",
}


# =========================================================
# DOWNLOAD IMAGE
# =========================================================


def download_image(url, output_path):

    response = requests.get(
        url,
        timeout=60,
    )

    response.raise_for_status()

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(output_path, "wb") as file:
        file.write(response.content)

    return str(output_path)


def validate_image_quality(image_path):
    """
    Run quality checks on a locally downloaded image.

    Returns:
        {
            "passed": bool,
            "errors": [...]
        }
    """

    image_path = Path(image_path)

    with open(image_path, "rb") as file:

        quality_result = check_image_quality(file)

    return quality_result


# =========================================================
# AREA
# =========================================================


def get_area(part):

    if part in INTERIOR_PARTS:
        return "interior"

    return "exterior"


# =========================================================
# SINGLE IMAGE PROCESSING
# =========================================================


def process_single_image(
    request_id,
    part,
    image_url,
):

    media_dir = Path(settings.MEDIA_ROOT)

    job_dir = media_dir / "api" / str(request_id)

    job_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = f"{part}_{uuid4().hex}.jpg"

    image_path = job_dir / filename

    # -----------------------------------------------------
    # DOWNLOAD ORIGINAL
    # -----------------------------------------------------

    download_image(
        image_url,
        image_path,
    )

    # -----------------------------------------------------
    # QUALITY CHECK
    # -----------------------------------------------------

    quality_result = validate_image_quality(image_path)

    print()
    print("=" * 60)
    print("IMAGE QUALITY CHECK")
    print("=" * 60)
    print("Part:", part)
    print("Passed:", quality_result["passed"])

    if quality_result["errors"]:

        print("Errors:")

        for error in quality_result["errors"]:
            print("-", error)

    print("=" * 60)

    # -----------------------------------------------------
    # STOP IF QUALITY CHECK FAILED
    # -----------------------------------------------------

    if not quality_result["passed"]:

        return {
            "part": part,
            "damage": [],
            "annotated_url": None,
            "annotated_path": None,
            "pipeline": "quality_check",
            "quality_check": quality_result,
        }

    # -----------------------------------------------------
    # ANNOTATED OUTPUT
    # -----------------------------------------------------

    annotated_path = job_dir / (image_path.stem + "_annotated.jpg")

    # =====================================================
    # INTERIOR
    # =====================================================

    if part in INTERIOR_PARTS:

        damage = detect_interior_damage(
            str(image_path),
            str(annotated_path),
        )

        # Depending on your interior_detector.py,
        # damage may already be a list.
        if isinstance(damage, tuple):
            damage = damage[0]

        pipeline = "interior"

    # =====================================================
    # RIM
    # =====================================================

    elif part in RIM_PARTS:

        crop_path = job_dir / (image_path.stem + "_rim_crop.jpg")

        rim = get_rim_crop(
            str(image_path),
            str(crop_path),
        )

        if rim is None:

            return {
                "part": part,
                "damage": [],
                "annotated_path": None,
                "annotated_url": None,
                "pipeline": "rim",
            }

        damage = detect_rim_damage(
            str(image_path),
            str(crop_path),
            str(annotated_path),
            rim["x_offset"],
            rim["y_offset"],
        )

        pipeline = "rim"

    # =====================================================
    # EXTERIOR
    # =====================================================

    else:

        damage, _ = detect_damage(
            str(image_path),
            str(annotated_path),
        )

        pipeline = "exterior"

    # =====================================================
    # UPLOAD ANNOTATED IMAGE
    # =====================================================

    annotated_url = None

    if annotated_path.exists():

        storage_path = (
            f"{request_id}/" f"analyzed_images/" f"{part}/" f"{annotated_path.name}"
        )

        upload_file(
            annotated_path,
            storage_path,
            content_type="image/jpeg",
        )

        annotated_url = get_file_url(
            storage_path,
            expires_in=3600,
        )

        print()
        print("=" * 60)
        print("SUPABASE ANNOTATED IMAGE UPLOAD")
        print("=" * 60)
        print("Part:", part)
        print("URL:", annotated_url)
        print("=" * 60)

    return {
        "part": part,
        "damage": damage,
        "annotated_path": str(annotated_path) if annotated_path.exists() else None,
        "annotated_url": annotated_url,
        "pipeline": pipeline,
        "quality_check": quality_result,
    }


def process_comparison_part(
    request_id,
    part,
    baseline_url,
    current_url,
):
    """
    Process one part for before/after comparison.

    Downloads:
        baseline image
        current image

    Runs:
        exterior YOLO
        rim segmentation + rim detector
        interior detector

    Then compares baseline vs current damage.

    Returns:
        {
            "part": ...,
            "before": [...],
            "after": [...],
            "new_damage": [...],
            "before_annotated_url": ...,
            "after_annotated_url": ...,
            "pipeline": ...
        }
    """

    media_dir = Path(settings.MEDIA_ROOT)

    job_dir = media_dir / "api" / str(request_id) / "comparison" / part

    job_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # =====================================================
    # FILE PATHS
    # =====================================================

    baseline_path = job_dir / "baseline.jpg"
    current_path = job_dir / "current.jpg"

    baseline_annotated = job_dir / "baseline_annotated.jpg"

    current_annotated = job_dir / "current_annotated.jpg"

    # =====================================================
    # DOWNLOAD IMAGES
    # =====================================================

    download_image(
        baseline_url,
        baseline_path,
    )

    download_image(
        current_url,
        current_path,
    )

    # =====================================================
    # QUALITY CHECK - BASELINE
    # =====================================================

    baseline_quality = validate_image_quality(baseline_path)

    print()
    print("=" * 60)
    print("BASELINE IMAGE QUALITY CHECK")
    print("=" * 60)
    print("Part:", part)
    print("Passed:", baseline_quality["passed"])

    if baseline_quality["errors"]:

        print("Errors:")

        for error in baseline_quality["errors"]:
            print("-", error)

    print("=" * 60)

    if not baseline_quality["passed"]:

        return {
            "part": part,
            "before": [],
            "after": [],
            "new_damage": [],
            "before_annotated_url": None,
            "after_annotated_url": None,
            "before_annotated_path": None,
            "after_annotated_path": None,
            "quality_check_failed": True,
            "quality_check_stage": "baseline",
            "quality_errors": baseline_quality["errors"],
        }

    # =====================================================
    # QUALITY CHECK - CURRENT
    # =====================================================

    current_quality = validate_image_quality(current_path)

    print()
    print("=" * 60)
    print("CURRENT IMAGE QUALITY CHECK")
    print("=" * 60)
    print("Part:", part)
    print("Passed:", current_quality["passed"])

    if current_quality["errors"]:

        print("Errors:")

        for error in current_quality["errors"]:
            print("-", error)

    print("=" * 60)

    if not current_quality["passed"]:

        return {
            "part": part,
            "before": [],
            "after": [],
            "new_damage": [],
            "before_annotated_url": None,
            "after_annotated_url": None,
            "before_annotated_path": None,
            "after_annotated_path": None,
            "quality_check_failed": True,
            "quality_check_stage": "current",
            "quality_errors": current_quality["errors"],
        }

    # =====================================================
    # INTERIOR
    # =====================================================

    if part in INTERIOR_PARTS:

        before_damage = detect_interior_damage(
            str(baseline_path),
            str(baseline_annotated),
        )

        after_damage = detect_interior_damage(
            str(current_path),
            str(current_annotated),
        )

        if isinstance(before_damage, tuple):
            before_damage = before_damage[0]

        if isinstance(after_damage, tuple):
            after_damage = after_damage[0]

        pipeline = "interior"

    # =====================================================
    # RIM
    # =====================================================

    elif part in RIM_PARTS:

        baseline_crop = job_dir / "baseline_rim_crop.jpg"

        current_crop = job_dir / "current_rim_crop.jpg"

        baseline_rim = get_rim_crop(
            str(baseline_path),
            str(baseline_crop),
        )

        current_rim = get_rim_crop(
            str(current_path),
            str(current_crop),
        )

        if baseline_rim is None or current_rim is None:

            return {
                "part": part,
                "before": [],
                "after": [],
                "new_damage": [],
                "before_annotated_url": None,
                "after_annotated_url": None,
                "pipeline": "rim",
            }

        before_damage = detect_rim_damage(
            str(baseline_path),
            str(baseline_crop),
            str(baseline_annotated),
            baseline_rim["x_offset"],
            baseline_rim["y_offset"],
        )

        after_damage = detect_rim_damage(
            str(current_path),
            str(current_crop),
            str(current_annotated),
            current_rim["x_offset"],
            current_rim["y_offset"],
        )

        pipeline = "rim"

    # =====================================================
    # EXTERIOR
    # =====================================================

    else:

        before_damage, _ = detect_damage(
            str(baseline_path),
            str(baseline_annotated),
        )

        after_damage, _ = detect_damage(
            str(current_path),
            str(current_annotated),
        )

        pipeline = "exterior"

    # =====================================================
    # COMPARE
    # =====================================================

    new_damage = compare_damage(
        before_damage,
        after_damage,
    )

    # =====================================================
    # UPLOAD BASELINE ANNOTATED IMAGE
    # =====================================================

    before_url = None

    if baseline_annotated.exists():

        storage_path = (
            f"{request_id}/" f"analyzed_images/" f"{part}/" f"baseline_annotated.jpg"
        )

        upload_file(
            baseline_annotated,
            storage_path,
            content_type="image/jpeg",
        )

        before_url = get_file_url(
            storage_path,
            expires_in=3600,
        )

    # =====================================================
    # UPLOAD CURRENT ANNOTATED IMAGE
    # =====================================================

    after_url = None

    if current_annotated.exists():

        storage_path = (
            f"{request_id}/" f"analyzed_images/" f"{part}/" f"current_annotated.jpg"
        )

        upload_file(
            current_annotated,
            storage_path,
            content_type="image/jpeg",
        )

        after_url = get_file_url(
            storage_path,
            expires_in=3600,
        )

    # =====================================================
    # RETURN
    # =====================================================

    return {
        "part": part,
        "before": before_damage,
        "after": after_damage,
        "new_damage": new_damage,
        "before_annotated_url": before_url,
        "after_annotated_url": after_url,
        "before_annotated_path": (
            str(baseline_annotated) if baseline_annotated.exists() else None
        ),
        "after_annotated_path": (
            str(current_annotated) if current_annotated.exists() else None
        ),
        "pipeline": pipeline,
    }
