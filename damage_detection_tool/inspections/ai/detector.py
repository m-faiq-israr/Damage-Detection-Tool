from ultralytics import YOLO
from pathlib import Path

MODEL_PATH = Path(__file__).parent / "models" / "car_damage_yolo11.pt"

model = YOLO(str(MODEL_PATH))


def detect_damage(image_path):
    """
    Returns a list of detections:
    [
        {
            "type": "scratch",
            "confidence": 0.91,
            "bbox": [x1,y1,x2,y2]
        }
    ]
    """

    results = model.predict(
        source=image_path,
        conf=0.35,
        verbose=False
    )

    detections = []

    for result in results:

        boxes = result.boxes # type: ignore

        for box in boxes: # type: ignore

            cls = int(box.cls.item())

            confidence = float(box.conf.item())

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

            detections.append({

                "type": model.names[cls],

                "confidence": confidence,

                "bbox": [x1, y1, x2, y2]

            })

    return detections