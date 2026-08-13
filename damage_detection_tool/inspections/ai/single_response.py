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
    "windshield": "A12",
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
    "windshield",
}


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
                    "part_code": PART_CODES.get(
                        part,
                        "UNKNOWN",
                    ),
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
