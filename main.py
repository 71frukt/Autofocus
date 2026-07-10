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
        project_root = project_root,
        config_path  = config_path,
        global_cfg   = config.global_cfg,
        optics_cfg   = config.optics_cfg
    )

    print("[INFO] starting hardware rtl simulation pipeline")
    print("-" * 70)
    
    points: Final[np.ndarray] = rtl_runner.run_focus_evaluation()

    print("-" * 70)
    print(f"{'step':<8}{'distance (mm)':<18}{'rtl metric score (ticks)':<25}")
    print("-" * 70)
    
    for step in range(len(points)):
        dist:  float
        score: float
        dist, score = points[step]
        print(f"[{step:2}]    {dist:<18.2f}{score:<25.2f}")
    print("-" * 70)

    ideal_dist: Final[float] = find_parabola_maximum(choose_pivot_points(points, config.focus_finder_cfg.lsm_points))
    print(f"maximum image sharpness found at distance {ideal_dist:.2f} mm")
    print("-" * 70)
    print("[INFO] execution completed successfully")


if __name__ == "__main__":
    main()