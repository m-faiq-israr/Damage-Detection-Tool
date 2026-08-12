from pathlib import Path

from .detector import detect_damage
from .rim_segmentation import get_rim_crop
from .rim_detector import detect_rim_damage
from .interior_detector import detect_interior_damage

RIM_PARTS = [
    "rim_front_right",
    "rim_front_left",
    "rim_rear_right",
    "rim_rear_left",
]


def detect_single_image(
    part,
    image_path,
    output_path,
):
    """
    Run damage detection on a single image.

    Returns:
        {
            "damage": [...],
            "annotated_path": "...",
            "pipeline": "yolo" / "rim" / "interior"
        }
    """

    # =====================================================
    # RIM PIPELINE
    # =====================================================

    if part in RIM_PARTS:

        print()
        print("=" * 60)
        print(f"SINGLE IMAGE RIM INSPECTION: {part}")
        print("=" * 60)

        image_path = str(image_path)

        image_file = Path(image_path)

        rim_crop_output = str(image_file.with_name(image_file.stem + "_rim_crop.jpg"))

        # -------------------------------------------------
        # STEP 1: SEGMENT RIM
        # -------------------------------------------------

        rim = get_rim_crop(
            image_path,
            rim_crop_output,
        )

        if rim is None:

            print("No rim detected.")

            return {
                "damage": [],
                "annotated_path": None,
                "pipeline": "rim",
            }

        # -------------------------------------------------
        # STEP 2: RIM DAMAGE DETECTION
        # -------------------------------------------------

        damage = detect_rim_damage(
            image_path,
            rim_crop_output,
            output_path,
            rim["x_offset"],
            rim["y_offset"],
        )

        return {
            "damage": damage,
            "annotated_path": output_path,
            "pipeline": "rim",
        }

    # =====================================================
    # INTERIOR PIPELINE
    # =====================================================

    if part in [
        "front_panel",
        "enter_driver",
        "enter_co_driver",
        "rear_row_seats",
        "trunk",
        "front_left_door",
        "front_right_door",
        "rear_left_door",
        "rear_right_door",
    ]:

        print()
        print("=" * 60)
        print(f"SINGLE IMAGE INTERIOR INSPECTION: {part}")
        print("=" * 60)

        damage = detect_interior_damage(
            image_path,
            output_path,
        )

        return {
            "damage": damage,
            "annotated_path": output_path,
            "pipeline": "interior",
        }

    # =====================================================
    # NORMAL YOLO PIPELINE
    # =====================================================

    print()
    print("=" * 60)
    print(f"SINGLE IMAGE YOLO INSPECTION: {part}")
    print("=" * 60)

    damage, annotated_path = detect_damage(
        image_path,
        output_path,
    )

    return {
        "damage": damage,
        "annotated_path": annotated_path,
        "pipeline": "yolo",
    }
