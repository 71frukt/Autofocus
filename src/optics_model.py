import os
from typing import Optional
import cv2
import numpy as np


"""
    [ Request frame for step X ]
                │
                ▼
        [ Generate blur ]   генерировать каждый раз картинку быстрее чем доставать из датасета (если она там уже есть)
                │
                ▼
    [ Check: Is "X.png" in dataset? ]
        Yes: skip
        No : cv2.imwrite("X.png")
                │
                ▼
    [ Return matrix to algorithm ] 
"""

class OpticalSystemModel:

    def __init__(
        self,
        reference_image_path: str,
        step_size:            float,
        max_distance:         float,
        ideal_focus_distance: float,
        roi_size:             tuple[int, int],
        blur_sensitivity:     float = 0.5,
        dataset_dir:          Optional[str] = None
    ) -> None:
        self._REF_IMAGE: np.ndarray = cv2.imread(reference_image_path, cv2.IMREAD_COLOR)
        if self._REF_IMAGE is None:
            raise FileNotFoundError(f"Could not load image: {reference_image_path}")

        self.STEP_SIZE:            float = step_size
        self.MAX_DISTANCE:         float = max_distance
        self.IDEAL_FOCUS_DISTANCE: float = ideal_focus_distance
        self.ROI_SIZE:             tuple[int, int] = roi_size
        self.BLUR_SENSITIVITY:     float = blur_sensitivity
        self.DATASET_DIR:          Optional[str] = dataset_dir

        self._disk_saved_steps: set[int] = set()

        if self.DATASET_DIR is not None:
            os.makedirs(self.DATASET_DIR, exist_ok=True)

        if step_size <= 0.0:
            raise ValueError(f"step_size[{step_size}] <= 0")

        if max_distance <= 0.0:
            raise ValueError(f"max_distance[{max_distance}] <= 0")

        if step_size > max_distance:
            raise ValueError(
                f"step_size[{step_size}] > max_distance[{max_distance}]")

    def _distance_to_step_id(self, distance: float) -> int:
        """Converts coordinate to an integer motor step index."""
        if not (0.0 <= distance <= self.MAX_DISTANCE):
            raise ValueError(
                f"Requested coordinate {distance:.2f} mm is out of bounds [0.0, {self.MAX_DISTANCE:.2f}]"
            )
        return int(round(distance / self.STEP_SIZE))

    def _calculate_blur(self, distance: float) -> np.ndarray:
        """Calculates Gaussian convolution based on distance from the ideal focus point."""
        distance_from_focus: float = abs(distance - self.IDEAL_FOCUS_DISTANCE)
        
        if distance_from_focus < (self.STEP_SIZE / 2.0):
            return self._REF_IMAGE.copy()

        sigma:       float = distance_from_focus * self.BLUR_SENSITIVITY
        kernel_radius: int = int(round(sigma * 2.0))
        kernel_size:   int = kernel_radius * 2 + 1
        
        if kernel_size < 3:
            kernel_size = 3

        return cv2.GaussianBlur(self._REF_IMAGE, (kernel_size, kernel_size), sigmaX=sigma, sigmaY=sigma)

    def _add_to_dataset_if_needed(self, step_id: int, distance: float, frame: np.ndarray) -> None:
        """Saves PNG to disk if it has not been saved yet."""
        if self.DATASET_DIR is None or step_id in self._disk_saved_steps:
            return

        filename: str = f"step_{step_id:04d}_dist_{distance:.2f}.png"
        file_path: str = os.path.join(self.DATASET_DIR, filename)

        if not os.path.exists(file_path):
            cv2.imwrite(file_path, frame)
            
        self._disk_saved_steps.add(step_id)

    def get_frame(self, distance: float) -> np.ndarray:
        """Primary interface method to retrieve a frame for a given motor coordinate."""
        frame: np.ndarray = self._calculate_blur(distance)

        if self.DATASET_DIR is not None:
            step_id: int = self._distance_to_step_id(distance)
            self._add_to_dataset_if_needed(step_id, distance, frame)

        return frame