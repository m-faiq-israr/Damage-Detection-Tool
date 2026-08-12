import base64
from pathlib import Path

import cv2

from django.conf import settings
from inference_sdk import InferenceHTTPClient

CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key=settings.ROBOFLOW_API_KEY,
)


WORKSPACE_NAME = "m-faiq-israr"

WORKFLOW_ID = "general-segmentation-api-11"


INTERIOR_CLASSES = "Hole, " "Broken, " "Stain, " "Tear"


def detect_interior_damage(
    image_path,
    output_path=None,
):

    print()
    print("=" * 60)
    print("ROBOFLOW INTERIOR DAMAGE DETECTION")
    print("=" * 60)

    print(f"Image: {image_path}")

    # =====================================================
    # RUN WORKFLOW
    # =====================================================

    result = CLIENT.run_workflow(
        workspace_name=WORKSPACE_NAME,
        workflow_id=WORKFLOW_ID,
        images={"image": str(image_path)},
        parameters={"classes": INTERIOR_CLASSES},
        use_cache=True,
    )

    # =====================================================
    # GET RESULT
    # =====================================================

    if isinstance(result, list) and result:

        workflow_result = result[0]

    elif isinstance(result, dict):

        workflow_result = result

    else:

        return []

    predictions_container = workflow_result.get("predictions", {})

    if isinstance(predictions_container, dict):

        predictions = predictions_container.get("predictions", [])

    else:

        predictions = []

    print(f"Detections: {len(predictions)}")

    damage = []

    # =====================================================
    # PROCESS DETECTIONS
    # =====================================================

    for index, prediction in enumerate(predictions, start=1):

        damage_type = prediction.get("class", "Unknown")

        confidence = float(prediction.get("confidence", 0))

        x = float(prediction.get("x", 0))

        y = float(prediction.get("y", 0))

        width = float(prediction.get("width", 0))

        height = float(prediction.get("height", 0))

        x1 = int(x - width / 2)

        y1 = int(y - height / 2)

        x2 = int(x + width / 2)

        y2 = int(y + height / 2)

        bbox = [
            x1,
            y1,
            x2,
            y2,
        ]

        damage.append(
            {
                "type": damage_type,
                "confidence": confidence,
                "bbox": bbox,
            }
        )

        print()
        print(f"Detection {index}")

        print(f"Class      : {damage_type}")

        print(f"Confidence : {confidence:.4f}")

        print(f"Bounding Box: {bbox}")

    # =====================================================
    # ANNOTATE ORIGINAL IMAGE
    # =====================================================

    image = cv2.imread(str(image_path))

    if image is None:

        return damage

    for item in damage:

        x1, y1, x2, y2 = item["bbox"]

        label = f'{item["type"]} ' f'{item["confidence"]:.2f}'

        cv2.rectangle(
            image,
            (x1, y1),
            (x2, y2),
            (0, 0, 255),
            2,
        )

        cv2.putText(
            image,
            label,
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 255),
            2,
        )

    # =====================================================
    # SAVE ANNOTATED IMAGE
    # =====================================================

    if output_path:

        cv2.imwrite(str(output_path), image)

        print()
        print("Interior annotated image saved:")

        print(output_path)

    print("=" * 60)

    return damage
