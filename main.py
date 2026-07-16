import os
from pathlib import Path
from typing import Final
import numpy as np

from src.autofocus.focus_lsm_search import choose_pivot_points, find_parabola_maximum
from rtl_lapd.runner import RtlLapdSimulationRunner
from src.data.config_checker import AppConfig


def main() -> None:
    config_name:  Final[str]  = "config.yaml"
    project_root: Final[Path] = Path(__file__).parent.resolve()
    config_path:  Final[Path] = project_root / config_name

    config: Final[AppConfig] = AppConfig.load(config_path)

    rtl_runner: Final[RtlLapdSimulationRunner] = RtlLapdSimulationRunner(
        project_root     = project_root,
        optics_cfg       = config.optics_cfg,
        focus_finder_cfg = config.focus_finder_cfg
    )

    print("[INFO] starting hardware rtl simulation pipeline")
    print("-" * 70)
    
    rtl_metrics: Final[np.ndarray] = rtl_runner.run_focus_evaluation()

    
    num_steps = config.focus_finder_cfg.num_scans
    step_size = float(config.optics_cfg.max_distance) / num_steps
    distances = [step * step_size for step in range(num_steps)]

    points = np.column_stack((distances, rtl_metrics))

    print("-" * 70)
    print(f"{'step':<6} {'dist (mm)':<15} {'score':<10}")
    print("-" * 70)

    for step in range(num_steps):
        print(f"{step:<6} {distances[step]:<15.3f} {rtl_metrics[step]:<10.0f}")

    ideal_dist: Final[float] = find_parabola_maximum(choose_pivot_points(points, config.focus_finder_cfg.lsm_points))
    print(f"maximum image sharpness found at distance {ideal_dist:.2f} mm")
    print("-" * 70)
    print("[INFO] execution completed successfully")


if __name__ == "__main__":
    main()