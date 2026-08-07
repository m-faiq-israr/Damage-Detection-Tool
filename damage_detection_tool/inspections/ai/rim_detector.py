import cv2

from inference_sdk import InferenceHTTPClient
from django.conf import settings

CLIENT = InferenceHTTPClient(
    api_url=settings.ROBOFLOW_API_URL,
    api_key=settings.ROBOFLOW_API_KEY,
)


def detect_rim_damage(image_path, output_path=None):

    result = CLIENT.infer(
        image_path,
        model_id=settings.ROBOFLOW_MODEL_ID,
    )

    detections = []

    # ---------------------------------------------------------
    # Load image for annotation
    # ---------------------------------------------------------

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    # ---------------------------------------------------------
    # Process Roboflow predictions
    # ---------------------------------------------------------

    for prediction in result.get("predictions", []):  # type: ignore

        damage_class = prediction["class"]

        confidence = float(prediction["confidence"])

        # -----------------------------------------------------
        # Ignore Good Bolt
        # -----------------------------------------------------

        if damage_class.lower() == "good bolt":
            continue

        # -----------------------------------------------------
        # Roboflow gives center coordinates
        # -----------------------------------------------------

        x = float(prediction["x"])
        y = float(prediction["y"])

        width = float(prediction["width"])
        height = float(prediction["height"])

        # Convert center coordinates -> corner coordinates

        x1 = int(x - width / 2)
        y1 = int(y - height / 2)

        x2 = int(x + width / 2)
        y2 = int(y + height / 2)

        # Keep coordinates inside image

        x1 = max(0, x1)
        y1 = max(0, y1)

        x2 = min(image.shape[1] - 1, x2)
        y2 = min(image.shape[0] - 1, y2)

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

        # -----------------------------------------------------
        # Draw bounding box
        # -----------------------------------------------------

        cv2.rectangle(
            image,
            (x1, y1),
            (x2, y2),
            (0, 0, 255),
            2,
        )

        # -----------------------------------------------------
        # Draw label
        # -----------------------------------------------------

        label = f"{damage_class} " f"{confidence:.2f}"

        cv2.putText(
            image,
            label,
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            2,
        )

    # ---------------------------------------------------------
    # Save annotated image
    # ---------------------------------------------------------

    if output_path:

        success = cv2.imwrite(output_path, image)

        if not success:
            raise ValueError(f"Could not save annotated image: {output_path}")

    # ---------------------------------------------------------
    # Console logging
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("ROBOFLOW RIM DETECTION")
    print("=" * 60)

    print(f"Image: {image_path}")

    if detections:

        print(f"Detections: {len(detections)}")

        for i, detection in enumerate(detections, start=1):

            print(f"\nDetection {i}")

            print(f"Class      : " f"{detection['type']}")

            print(f"Confidence : " f"{detection['confidence']:.4f}")

            print(f"Bounding Box: " f"{detection['bbox']}")

    else:

        print("No rim defects detected.")

    print("=" * 60 + "\n")

    return detections
