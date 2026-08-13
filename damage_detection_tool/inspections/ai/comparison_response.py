# =========================================================
# PART CODES
# =========================================================

PART_CODES = {
    "front": "A00",
    "rear": "A01",
    "left": "A02",
    "right": "A03",
    "front_right": "A04",
    "front_left": "A05",
    "rear_right": "A06",
    "rear_left": "A07",
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
                    "part_code": PART_CODES.get(
                        part,
                        "UNKNOWN",
                    ),
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
