from ultralytics import YOLO
from pathlib import Path
import cv2

MODEL_PATH = Path(__file__).parent / "models" / "car_damage_yolo11.pt"

model = YOLO(str(MODEL_PATH))


def detect_damage(image_path, output_path=None):
    """
    Returns:
        detections,
        annotated_image_path
    """

    results = model(
        image_path,
        conf=0.35,
        verbose=False
    )

    result = results[0] # type: ignore

    detections = []

    if result.boxes is not None: # type: ignore

        for box in result.boxes: # type: ignore

            cls = int(box.cls.item())

            confidence = float(box.conf.item())

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

            detections.append({
                "type": model.names[cls],
                "confidence": confidence,
                "bbox": [x1, y1, x2, y2]
            })

    annotated_path = None

    if output_path:

        annotated = result.plot() # type: ignore

        cv2.imwrite(output_path, annotated)

        annotated_path = output_path

    return detections, annotated_path