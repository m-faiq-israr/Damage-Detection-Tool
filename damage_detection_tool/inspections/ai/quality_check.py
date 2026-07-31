import cv2
import numpy as np


def check_image_quality(file):
    """
    Returns:
        {
            "passed": bool,
            "errors": [list of error messages]
        }
    """

    errors = []

    file.seek(0)

    image_array = np.frombuffer(file.read(), np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    file.seek(0)

    if image is None:
        return {
            "passed": False,
            "errors": ["Invalid image file."]
        }

    height, width = image.shape[:2]

    # ---------- Resolution --------

    # if width < 800 or height < 600:
    #     errors.append(
    #         f"Resolution too low ({width}x{height}). Minimum is 800x600."
    #     )

    # ---------- Blur ----------

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    variance = cv2.Laplacian(gray, cv2.CV_64F).var()

    if variance < 100:
        errors.append("Image is too blurry.")

    # ---------- Brightness ----------

    brightness = np.mean(gray)

    if brightness < 50:
        errors.append("Image is too dark.")

    if brightness > 220:
        errors.append("Image is overexposed.")


    return {
        "passed": len(errors) == 0,
        "errors": errors
    }