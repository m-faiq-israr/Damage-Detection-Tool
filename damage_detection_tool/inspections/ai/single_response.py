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
    "front_left_door": "AI6",
    "front_right_door": "AI7",
    "rear_left_door": "AI8",
    "rear_right_door": "AI9",
}


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


def build_single_response(
    request_id,
    single_results,
    report_url,
):

    parts = []

    for part, result in single_results.items():

        # Determine area
        if part in EXTERIOR_PARTS:
            area = "exterior"
        else:
            area = "interior"

        # Supabase annotated image URL
        annotated_image_url = result.get("supabase_annotated_url")

        # Detected damages
        damages = result.get("damage", [])

        for damage in damages:

            confidence = float(damage.get("confidence", 0))

            probability = round(confidence * 100)

            label = damage.get("damage_type") or damage.get("type") or "Unknown damage"

            parts.append(
                {
                    "part_code": resolve_part_code(part, label),
                    "area": area,
                    "probability": probability,
                    "severity": "high",
                    "label": label,
                    "annotated_image_url": annotated_image_url,
                }
            )

    return {
        "request_id": request_id,
        "parts": parts,
        "report url": report_url,
    }
