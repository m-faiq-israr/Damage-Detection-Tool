from pathlib import Path

import cv2
import requests
from django.conf import settings

# =========================================================
# EXTERIOR MODEL SERVICE CONFIGURATION
# =========================================================

EXTERIOR_MODEL_API_URL = settings.EXTERIOR_MODEL_API_URL

EXTERIOR_MODEL_API_KEY = settings.EXTERIOR_MODEL_API_KEY


# =========================================================
# DAMAGE DETECTION
# =========================================================


def detect_damage(image_path, output_path=None):
    """
    Run exterior car damage detection via our
    self-hosted YOLO model service.

    Returns:
        detections,
        annotated_image_path
    """

    # =====================================================
    # RUN MODEL SERVICE INFERENCE
    # =====================================================

    with open(image_path, "rb") as image_file:

        response = requests.post(
            f"{EXTERIOR_MODEL_API_URL}/v1/detect/exterior",
            files={"image": image_file},
            headers={"Authorization": f"Bearer {EXTERIOR_MODEL_API_KEY}"},
            timeout=120,
        )

    response.raise_for_status()

    predictions = response.json().get("predictions", [])

    detections = []

    # =====================================================
    # PROCESS PREDICTIONS
    # =====================================================

    for prediction in predictions:

        damage_class = prediction["class"]

        confidence = float(prediction["confidence"])

        if confidence < 0.35:
            continue

        x1, y1, x2, y2 = prediction["bbox"]

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

                # Draw bounding box

                cv2.rectangle(
                    image,
                    (x1, y1),
                    (x2, y2),
                    (0, 0, 255),
                    2,
                )

                # Label

                label = f"{damage_class} " f"{confidence:.2f}"

                cv2.putText(
                    image,
                    label,
                    (x1, max(y1 - 10, 20)),
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
