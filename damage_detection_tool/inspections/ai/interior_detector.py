from pathlib import Path


from django.conf import settings
from inference_sdk import InferenceHTTPClient

CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key=settings.ROBOFLOW_API_KEY,
)

WORKSPACE_NAME = "m-faiq-israr"

WORKFLOW_ID = "general-segmentation-api-11"

INTERIOR_CLASSES = "Hole, Broken, Stain, Tear"


def detect_interior_damage(
    image_path,
    output_path=None,
):

    image_path = str(image_path)

    result = CLIENT.run_workflow(
        workspace_name=WORKSPACE_NAME,
        workflow_id=WORKFLOW_ID,
        images={"image": image_path},
        parameters={"classes": INTERIOR_CLASSES},
        use_cache=True,
    )

    # =====================================================
    # WORKFLOW RESULT
    # =====================================================

    detections = []

    if isinstance(result, list) and len(result) > 0:
        workflow_result = result[0]

    elif isinstance(result, dict):
        workflow_result = result

    else:
        workflow_result = {}

    # =====================================================
    # FIND PREDICTIONS
    # =====================================================

    predictions_data = workflow_result.get("predictions", {})

    predictions = []

    if isinstance(predictions_data, dict):

        predictions = predictions_data.get("predictions", [])

    elif isinstance(predictions_data, list):

        predictions = predictions_data

    # =====================================================
    # PROCESS DETECTIONS
    # =====================================================

    print(f"Detections: {len(predictions)}")

    for index, prediction in enumerate(predictions, start=1):

        damage_class = prediction.get("class", "Unknown")

        confidence = prediction.get("confidence", 0)

        # -----------------------------------------------
        # Bounding box
        # -----------------------------------------------

        x = prediction.get("x", 0)

        y = prediction.get("y", 0)

        width = prediction.get("width", 0)

        height = prediction.get("height", 0)

        x1 = int(x - width / 2)

        y1 = int(y - height / 2)

        x2 = int(x + width / 2)

        y2 = int(y + height / 2)

        bbox = [x1, y1, x2, y2]

        # -----------------------------------------------
        # Store detection
        # -----------------------------------------------

        detection = {
            "type": damage_class,
            "confidence": float(confidence),
            "bbox": bbox,
        }

        detections.append(detection)

    annotated_image = workflow_result.get("annotated_image")

    if annotated_image:

        try:

            import base64

            if isinstance(annotated_image, str):

                image_data = base64.b64decode(annotated_image)

                if output_path:

                    Path(output_path).write_bytes(image_data)

                    print("Interior annotated image saved:")

                    print(output_path)

        except Exception as e:

            print("Could not save annotated " f"interior image: {e}")

    return detections
