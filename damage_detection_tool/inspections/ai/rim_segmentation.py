import cv2
import numpy as np

from inference_sdk import InferenceHTTPClient
from pycocotools import mask as mask_utils

from django.conf import settings

CLIENT = InferenceHTTPClient(
    api_url=settings.ROBOFLOW_API_URL,
    api_key=settings.ROBOFLOW_API_KEY,
)


def get_rim_crop(image_path, output_path=None):

    result = CLIENT.run_workflow(
        workspace_name=settings.ROBOFLOW_WORKSPACE,
        workflow_id=settings.ROBOFLOW_WORKFLOW_ID,
        images={"image": image_path},
        parameters={"classes": "rim"},
        use_cache=True,
    )

    if not result:
        print(f"No workflow result for: {image_path}")

        return None

    workflow_result = result[0]

    predictions_data = workflow_result.get("predictions", {})

    predictions = predictions_data.get("predictions", [])

    if not predictions:

        print(f"No rim detected in: {image_path}")

        return None

    rim_prediction = max(
        predictions, key=lambda prediction: prediction.get("confidence", 0)
    )

    print("\n" + "=" * 60)
    print("RIM SEGMENTATION")
    print("=" * 60)

    print(f"Image      : {image_path}")

    print(f"Class      : {rim_prediction['class']}")

    print(f"Confidence : " f"{rim_prediction['confidence']:.4f}")

    # ---------------------------------------------------------
    # Load original image
    # ---------------------------------------------------------

    image = cv2.imread(image_path)

    if image is None:

        raise ValueError(f"Could not read image: {image_path}")

    image_height, image_width = image.shape[:2]

    # ---------------------------------------------------------
    # Decode RLE segmentation mask
    # ---------------------------------------------------------

    rle = rim_prediction.get("rle_mask")

    if not rle:

        print("No segmentation mask returned.")

        return None

    mask = mask_utils.decode(rle)

    mask = np.asarray(mask, dtype=np.uint8)

    if mask.shape[0] != image_height or mask.shape[1] != image_width:

        mask = cv2.resize(
            mask, (image_width, image_height), interpolation=cv2.INTER_NEAREST
        )

    ys, xs = np.where(mask > 0)

    if len(xs) == 0:

        print("Rim mask is empty.")

        return None

    x1 = int(xs.min())
    y1 = int(ys.min())

    x2 = int(xs.max())
    y2 = int(ys.max())

    # ---------------------------------------------------------
    # Add small padding around rim
    # ---------------------------------------------------------

    padding = 10

    x1 = max(0, x1 - padding)

    y1 = max(0, y1 - padding)

    x2 = min(image_width - 1, x2 + padding)

    y2 = min(image_height - 1, y2 + padding)

    # ---------------------------------------------------------
    # Crop original image
    # ---------------------------------------------------------

    crop = image[y1 : y2 + 1, x1 : x2 + 1]

    # ---------------------------------------------------------
    # Apply mask to crop
    # ---------------------------------------------------------

    crop_mask = mask[y1 : y2 + 1, x1 : x2 + 1]

    crop_mask = (crop_mask * 255).astype(np.uint8)

    isolated_rim = cv2.bitwise_and(crop, crop, mask=crop_mask)

    # ---------------------------------------------------------
    # Save cropped rim for debugging
    # ---------------------------------------------------------

    if output_path:

        cv2.imwrite(output_path, isolated_rim)

    print(f"Rim bounding box: " f"[{x1}, {y1}, {x2}, {y2}]")

    print(f"Crop size: " f"{isolated_rim.shape[1]} x " f"{isolated_rim.shape[0]}")

    print("=" * 60 + "\n")

    # ---------------------------------------------------------
    # Return crop + original coordinates
    # ---------------------------------------------------------

    return {
        "crop": isolated_rim,
        "x_offset": x1,
        "y_offset": y1,
        "bbox": [x1, y1, x2, y2],
    }
