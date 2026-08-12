import cv2

from inference_sdk import InferenceHTTPClient
from django.conf import settings

CLIENT = InferenceHTTPClient(
    api_url=settings.ROBOFLOW_API_URL,
    api_key=settings.ROBOFLOW_API_KEY,
)


def detect_rim_damage(
    image_path,
    crop_path,
    output_path,
    x_offset,
    y_offset,
):

    # ---------------------------------------------------------
    # Run rim damage model on cropped rim
    # ---------------------------------------------------------

    result = CLIENT.infer(
        crop_path,
        model_id=settings.ROBOFLOW_MODEL_ID,
    )

    # ---------------------------------------------------------
    # Load original image
    # ---------------------------------------------------------

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    detections = []

    # ---------------------------------------------------------
    # Process predictions
    # ---------------------------------------------------------

    for prediction in result.get("predictions", []):  # type: ignore

        damage_class = prediction["class"]

        confidence = float(prediction["confidence"])

        # -----------------------------------------------------
        # Ignore Good Bolt
        # -----------------------------------------------------

        if damage_class.lower() in ["good bolt", "wrong bolt"]:
            continue

        # -----------------------------------------------------
        # Roboflow coordinates
        #
        # x/y = center
        # width/height = dimensions
        # -----------------------------------------------------

        x = float(prediction["x"])
        y = float(prediction["y"])

        width = float(prediction["width"])

        height = float(prediction["height"])

        # -----------------------------------------------------
        # Convert center coordinates to crop coordinates
        # -----------------------------------------------------

        crop_x1 = int(x - width / 2)

        crop_y1 = int(y - height / 2)

        crop_x2 = int(x + width / 2)

        crop_y2 = int(y + height / 2)

        # -----------------------------------------------------
        # Convert crop coordinates to ORIGINAL coordinates
        # -----------------------------------------------------

        original_x1 = crop_x1 + x_offset
        original_y1 = crop_y1 + y_offset

        original_x2 = crop_x2 + x_offset
        original_y2 = crop_y2 + y_offset

        # -----------------------------------------------------
        # Keep coordinates inside original image
        # -----------------------------------------------------

        original_x1 = max(0, original_x1)

        original_y1 = max(0, original_y1)

        original_x2 = min(image.shape[1] - 1, original_x2)

        original_y2 = min(image.shape[0] - 1, original_y2)

        bbox = [
            original_x1,
            original_y1,
            original_x2,
            original_y2,
        ]

        detections.append(
            {
                "type": damage_class,
                "confidence": confidence,
                "bbox": bbox,
            }
        )

        # -----------------------------------------------------
        # Draw red bounding box
        # -----------------------------------------------------

        cv2.rectangle(
            image,
            (original_x1, original_y1),
            (original_x2, original_y2),
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
            (
                original_x1,
                max(original_y1 - 10, 20),
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            2,
        )

    # ---------------------------------------------------------
    # Save annotated ORIGINAL image
    # ---------------------------------------------------------

    success = cv2.imwrite(output_path, image)

    if not success:
        raise ValueError(f"Could not save annotated image: " f"{output_path}")

    # ---------------------------------------------------------
    # Console output
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("ROBOFLOW RIM DAMAGE DETECTION")
    print("=" * 60)

    print(f"Original Image: {image_path}")

    print(f"Rim Crop: {crop_path}")

    print(f"Detections: {len(detections)}")

    for i, detection in enumerate(detections, start=1):

        print(f"\nDetection {i}")

        print(f"Class      : " f"{detection['type']}")

        print(f"Confidence : " f"{detection['confidence']:.4f}")

        print(f"Bounding Box: " f"{detection['bbox']}")

    print("=" * 60 + "\n")

    return detections
