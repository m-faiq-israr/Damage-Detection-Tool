from .part_codes import resolve_exterior_part_code

PART_CODES = {
    "rim_front_right": "A08",
    "rim_front_left": "A09",
    "rim_rear_right": "A10",
    "rim_rear_left": "A11",
    "front_panel": "AI1",
    "enter_driver": "AI2",
    "enter_co_driver": "AI3",
    "rear_row_seats": "AI4",
    "trunk": "AI5",
    "door_front_left": "AI6",
    "door_front_right": "AI7",
    "door_rear_left": "AI8",
    "door_rear_right": "AI9",
}


# =========================================================
# EXTERIOR PARTS
# =========================================================

EXTERIOR_PARTS = {
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
}

# The subset of EXTERIOR_PARTS that are body-panel angles (as opposed
# to rims), whose part codes are resolved from the damage class.
EXTERIOR_ANGLE_PARTS = {
    "front",
    "rear",
    "left",
    "right",
    "front_right",
    "front_left",
    "rear_right",
    "rear_left",
}


def resolve_part_code(part, damage_class):

    if part in EXTERIOR_ANGLE_PARTS:
        return resolve_exterior_part_code(damage_class, part)

    return PART_CODES.get(part, "UNKNOWN")


# =========================================================
# BUILD COMPARISON RESPONSE
# =========================================================


def build_comparison_response(
    request_id,
    inspection_results,
    report_url,
):
    """
    Build the final JSON response for comparison inspection.

    Only newly detected damages are returned.
    """

    parts = []

    for part, result in inspection_results.items():

        # -------------------------------------------------
        # Determine area
        # -------------------------------------------------

        if part in EXTERIOR_PARTS:

            area = "exterior"

        else:

            area = "interior"

        # -------------------------------------------------
        # Supabase annotated image URL
        # -------------------------------------------------

        annotated_image_url = result.get("after_annotated")

        # -------------------------------------------------
        # New damages only
        # -------------------------------------------------

        new_damages = result.get("new_damage", [])

        for damage in new_damages:

            confidence = float(
                damage.get(
                    "confidence",
                    0,
                )
            )

            probability = round(confidence * 100)

            label = damage.get("damage_type") or damage.get("type") or "Unknown damage"

            parts.append(
                {
                    "part_code": resolve_part_code(part, label),
                    "area": area,
                    "probability": probability,
                    "severity": "very_high",
                    "label": label,
                    "change": "new",
                    "annotated_image_url": annotated_image_url,
                }
            )

    # -----------------------------------------------------
    # Final response
    # -----------------------------------------------------

    return {
        "request_id": request_id,
        "parts": parts,
        "report url": report_url,
    }
