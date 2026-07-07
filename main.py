import os
from typing import Any
import yaml
import numpy as np

from src.data.optisc_dataset_manager import OpticsDatasetManager
from src.autofocus.sharpness_metrics import calculate_lapd


def main() -> None:
    config_path: str = "config.yaml"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Файл конфигурации не найден: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config: dict[str, Any] = yaml.safe_load(f)

    global_cfg: dict[str, Any] = config["global"]
    optics_cfg: dict[str, Any] = config["optics"]

    optics_dataset_manager = OpticsDatasetManager(
        global_cfg = global_cfg,
        optics_cfg = optics_cfg
    )

    print(f"[INFO] Active dataset directory: {optics_dataset_manager.dataset_dir}")

    # Генерация 16 последовательных шагов фокусировки
    motor_step_size: float = float(optics_cfg["step_size"])
    max_distance:    float = float(optics_cfg["max_distance"])
    step_size:       float = max_distance / 16.0 / motor_step_size
    num_steps:       int   = int(round(max_distance / step_size)) + 1

    roi: tuple[int, int] = tuple(global_cfg["roi"])

    print(f"[INFO] Starting focus metric evaluation for {num_steps} positions...")
    print("-" * 70)
    print(f"{'Step':<8}{'Distance (mm)':<18}{'LAPD Score':<20}")
    print("-" * 70)

    for step in range(num_steps):
        distance: float = step * step_size
        if distance > max_distance:
            break

        # 1. Запрашиваем матрицу кадра (из кеша или генерируем Гауссом)
        frame: np.ndarray = optics_dataset_manager.get_frame(distance)

        # 2. Передаем полученный кадр и ROI в изолированную функцию метрики
        lapd_score: float = calculate_lapd(frame, roi)

        # Выводим логи в виде форматированной таблицы
        print(f"[{step:02d}/{num_steps - 1}]   {distance:<18.2f}{lapd_score:<20.2f}")

    print("-" * 70)

    print("[INFO] Done.")


if __name__ == "__main__":
    main()