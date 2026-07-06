import yaml
from src.optics_model import OpticalSystemModel


def main() -> None:
    """Основной пайплайн генерации датасета размытых изображений."""
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    global_cfg = config["global"]
    optics_cfg = config["optics"]

    optics = OpticalSystemModel(
        reference_image_path    = optics_cfg["reference_image_path"],
        step_size_mm            = float(optics_cfg["step_size_mm"]),
        max_distance_mm         = float(optics_cfg["max_distance_mm"]),
        ideal_focus_distance_mm = float(optics_cfg["ideal_focus_distance_mm"]),
        roi_size                = tuple(global_cfg["roi"]),
        blur_sensitivity        = float(optics_cfg["blur_sensitivity"]),
        dataset_dir             = "datasets/bom_bom/blurred", 
    )

    # Генерация 16 последовательных шагов фокусировки
    num_steps: int = 32
    step_size: float = float(optics_cfg["step_size_mm"])

    print(f"[INFO] Запуск генерации {num_steps} кадров...")

    for step in range(num_steps):
        distance_mm: float = step * step_size

        # Вызов get_frame автоматически рассчитает блюр и сохранит PNG в dataset_dir,
        # если файл для данного шага еще не был создан ранее.
        _ = optics.get_frame(distance_mm)

        print(
            f"[STEP {step:02d}/{num_steps - 1}] Обработана позиция мотора: {distance_mm:.1f} мм"
        )

    print("[INFO] Генерация датасета успешно завершена.")


if __name__ == "__main__":
    main()