from typing import Optional
import cv2
import numpy as np


class OpticalSystemModel:

    def __init__(
        self,
        reference_image:      np.ndarray,
        step_size:            float,
        max_distance:         float,
        ideal_focus_distance: float,
        roi_size:             tuple[int, int],
        blur_sensitivity:     float = 0.5
    ) -> None:
        if step_size <= 0.0:
            raise ValueError(f"step_size[{step_size}] <= 0")

        if max_distance <= 0.0:
            raise ValueError(f"max_distance[{max_distance}] <= 0")

        if step_size > max_distance:
            raise ValueError(
                f"step_size[{step_size}] > max_distance[{max_distance}]"
            )

        self._REF_IMAGE:           np.ndarray = reference_image
        self.STEP_SIZE:            float = step_size
        self.MAX_DISTANCE:         float = max_distance
        self.IDEAL_FOCUS_DISTANCE: float = ideal_focus_distance
        self.ROI_SIZE:             tuple[int, int] = roi_size
        self.BLUR_SENSITIVITY:     float = blur_sensitivity

    def distance_to_step_id(self, distance: float) -> int:
        """Converts coordinate to an integer motor step index"""
        if not (0.0 <= distance <= self.MAX_DISTANCE):
            raise ValueError(
                f"Requested coordinate {distance:.2f} mm is out of bounds [0.0, {self.MAX_DISTANCE:.2f}]"
            )
        return int(round(distance / self.STEP_SIZE))

    def calculate_frame(self, distance: float) -> np.ndarray:
        """Calculates Gaussian convolution based on distance from the ideal focus point"""
        distance_from_focus: float = abs(distance - self.IDEAL_FOCUS_DISTANCE)
        
        if distance_from_focus < (self.STEP_SIZE / 2.0):
            return self._REF_IMAGE.copy()

        sigma:       float = distance_from_focus * self.BLUR_SENSITIVITY
        kernel_radius: int = int(round(sigma * 2.0))
        kernel_size:   int = kernel_radius * 2 + 1
        
        if kernel_size < 3:
            kernel_size = 3

        assert kernel_size % 2 == 1, f"Gaussian kernel size must be odd: {kernel_size}"

        return cv2.GaussianBlur(self._REF_IMAGE, (kernel_size, kernel_size), sigmaX=sigma, sigmaY=sigma)