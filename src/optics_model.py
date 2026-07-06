import os
from typing import Optional
import cv2
import numpy as np


"""
    [ Запрос кадра для шага X ]
                │
                ▼
    [ Сгенерировать Blur на лету ]
                │
                ▼
    [ Проверить: "X.png" есть в датасете? ]
        Да : пропустить
        Нет: cv2.imwrite("X.png")
                │
                ▼
    [ Возврат матрицы в алгоритм ] 
"""

class OpticalSystemModel:

    def __init__(
        self,
        reference_image_path:    str,
        step_size_mm:            float,
        max_distance_mm:         float,
        ideal_focus_distance_mm: float,
        roi_size:                tuple[int, int],
        blur_sensitivity:        float = 0.5,
        dataset_dir:             Optional[str] = None
    ) -> None:
        self._REF_IMAGE: np.ndarray = cv2.imread(reference_image_path, cv2.IMREAD_COLOR)
        if self._REF_IMAGE is None:
            raise FileNotFoundError(f"He удалось загрузить изображение: {reference_image_path}")

        self._STEP_SIZE_MM:            float = step_size_mm
        self._MAX_DISTANCE_MM:         float = max_distance_mm
        self._IDEAL_FOCUS_DISTANCE_MM: float = ideal_focus_distance_mm
        self._ROI_SIZE:                tuple[int, int] = roi_size
        self._BLUR_SENSITIVITY:        float = blur_sensitivity
        self._DATASET_DIR:             Optional[str] = dataset_dir

        self._disk_saved_steps: set[int] = set()

        if self._DATASET_DIR is not None:
            os.makedirs(self._DATASET_DIR, exist_ok=True)


    def _distance_to_step_id(self, distance_mm: float) -> int:
        """Преобразует координату в целочисленный индекс шага мотора."""
        if not (0.0 <= distance_mm <= self._MAX_DISTANCE_MM):
            raise ValueError(
                f"Запрошенная координата {distance_mm:.2f} мм выходит за пределы [0.0, {self._MAX_DISTANCE_MM:.2f}]"
            )
        return int(round(distance_mm / self._STEP_SIZE_MM))

    def _calculate_blur(self, distance_mm: float) -> np.ndarray:
        """Вычисляет свёртку Гаусса в зависимости от удаления от точки идеального фокуса."""
        distance_from_focus: float = abs(distance_mm - self._IDEAL_FOCUS_DISTANCE_MM)
        
        if distance_from_focus < (self._STEP_SIZE_MM / 2.0):
            return self._REF_IMAGE.copy()

        sigma:       float = distance_from_focus * self._BLUR_SENSITIVITY
        kernel_radius: int = int(round(sigma * 2.0))
        kernel_size:   int = kernel_radius * 2 + 1
        
        if kernel_size < 3:
            kernel_size = 3

        return cv2.GaussianBlur(self._REF_IMAGE, (kernel_size, kernel_size), sigmaX=sigma, sigmaY=sigma)

    def _add_to_dataset_if_needed(self, step_id: int, distance_mm: float, frame: np.ndarray) -> None:
        """Сохраняет PNG на диск, если он еще не был сохранен."""
        if self._DATASET_DIR is None or step_id in self._disk_saved_steps:
            return

        filename: str = f"step_{step_id:04d}_dist_{distance_mm:.2f}mm.png"
        file_path: str = os.path.join(self._DATASET_DIR, filename)

        if not os.path.exists(file_path):
            cv2.imwrite(file_path, frame)
            
        self._disk_saved_steps.add(step_id)

    def get_frame(self, distance_mm: float) -> np.ndarray:
        """Основной интерфейсный метод получения кадра для заданной координаты мотора."""
        frame: np.ndarray = self._calculate_blur(distance_mm)

        if self._DATASET_DIR is not None:
            step_id: int = self._distance_to_step_id(distance_mm)
            self._add_to_dataset_if_needed(step_id, distance_mm, frame)

        return frame