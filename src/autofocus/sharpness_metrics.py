import cv2
import numpy as np

_K: np.ndarray = np.array([
    [ 0, -1,  0],
    [-1,  4, -1],
    [ 0, -1,  0]
], dtype=np.float32)

_COEF: float = 1.0 / np.sqrt(2.0)
        
_K_D1: np.ndarray = np.array([
    [0,  0, 1],
    [0, -2, 0],
    [1,  0, 0]
], dtype=np.float32) * _COEF

_K_D2: np.ndarray = np.array([
    [1,  0, 0],
    [0, -2, 0],
    [0,  0, 1]
], dtype=np.float32) * _COEF


def _extract_center_roi(image: np.ndarray, roi: tuple[int, int]) -> np.ndarray:
    if image is None or image.size == 0:
        raise ValueError("Input image is empty or None")

    height, width = image.shape[:2]
    roi_w,  roi_h = roi

    if roi_w <= 0 or roi_h <= 0:
        raise ValueError(f"ROI dimensions must be positive, got: w={roi_w}, h={roi_h}")

    if roi_w > width or roi_h > height:
        raise ValueError(
            f"ROI size [{roi_w}x{roi_h}] exceeds image dimensions [{width}x{height}]"
        )

    start_x: int = (width  - roi_w) // 2
    start_y: int = (height - roi_h) // 2

    crop: np.ndarray = image[start_y : start_y + roi_h, start_x : start_x + roi_w]

    if len(crop.shape) == 3:
        return cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return crop


def calculate_lapd(image: np.ndarray, roi: tuple[int, int]) -> float:
    """Calculates the LAPD focus metric score within the specified center ROI."""
    intensity_image = _extract_center_roi(image, roi)

    # grey spectrum
    assert len(intensity_image.shape) == 2, "ROI extraction failed to output a 2D single-channel matrix"

    res_k   = cv2.filter2D(intensity_image, cv2.CV_32F, _K)
    res_kd1 = cv2.filter2D(intensity_image, cv2.CV_32F, _K_D1)
    res_kd2 = cv2.filter2D(intensity_image, cv2.CV_32F, _K_D2)

    lapd_matrix = np.abs(res_k) + np.abs(res_kd1) + np.abs(res_kd2)

    return float(np.sum(lapd_matrix))