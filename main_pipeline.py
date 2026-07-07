import os
from typing import Any
import yaml
from src.optisc_dataset_manager import OpticsDatasetManager


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
    step_size:    float = float(optics_cfg["step_size"])
    max_distance: float = float(optics_cfg["max_distance"])
    num_steps:    int   = int(round(max_distance / step_size)) + 1

    print(f"[INFO] Starting processing {num_steps} positions...")

    for step in range(num_steps):
        distance: float = step * step_size
        if distance > max_distance:
            break

        # Вызов get_frame автоматически рассчитает блюр и сохранит PNG в dataset_dir,
        # если файл для данного шага еще не был создан ранее.
        _ = optics_dataset_manager.get_frame(distance)
        print(f"[STEP {step:02d}/{num_steps - 1}] The coordinate has been processed: {distance:.1f} mm")

    print("[INFO] Done.")


if __name__ == "__main__":
    main()