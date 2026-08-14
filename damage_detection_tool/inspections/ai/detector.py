import cv2

from inference_sdk import InferenceHTTPClient
from django.conf import settings

CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key=settings.ROBOFLOW_API_KEY,
)

MODEL_ID = "car-damage-detection-5ioys-gngb8/1"


def detect_damage(image_path, output_path=None):
    result = CLIENT.infer(
        image_path,
        model_id=MODEL_ID,
    )

    predictions = result.get("predictions", [])  # type: ignore
    detections = []

    for prediction in predictions:

        damage_class = prediction["class"]

        confidence = float(prediction["confidence"])

        # -------------------------------------------------
        # CONFIDENCE FILTER
        # -------------------------------------------------

        if confidence < 0.35:
            continue

        x = float(prediction["x"])
        y = float(prediction["y"])

        width = float(prediction["width"])

        height = float(prediction["height"])

        # -------------------------------------------------
        # CENTER → CORNERS
        # -------------------------------------------------

        x1 = int(x - width / 2)

        y1 = int(y - height / 2)

        x2 = int(x + width / 2)

        y2 = int(y + height / 2)

        detections.append(
            {
                "type": damage_class,
                "confidence": confidence,
                "bbox": [
                    x1,
                    y1,
                    x2,
                    y2,
                ],
            }
        )

    # =====================================================
    # CREATE ANNOTATED IMAGE
    # =====================================================

    annotated_path = None

    if output_path:

        image = cv2.imread(image_path)

        if image is not None:

            for detection in detections:

                x1, y1, x2, y2 = detection["bbox"]

                damage_class = detection["type"]

                confidence = detection["confidence"]

                # -------------------------------------------------
                # DRAW BOUNDING BOX
                # -------------------------------------------------

                cv2.rectangle(
                    image,
                    (x1, y1),
                    (x2, y2),
                    (0, 0, 255),
                    2,
                )

                # -------------------------------------------------
                # LABEL
                # -------------------------------------------------

                label = f"{damage_class} " f"{confidence:.2f}"

                cv2.putText(
                    image,
                    label,
                    (
                        x1,
                        max(
                            y1 - 10,
                            20,
                        ),
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 255),
                    2,
                )

            cv2.imwrite(
                output_path,
                image,
            )

            annotated_path = output_path

    # =====================================================
    # RETURN
    # =====================================================

    return detections, annotated_path
