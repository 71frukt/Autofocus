from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final
import yaml


@dataclass(frozen=True)
class GlobalConfig:
    roi: tuple[int, int]
    simulator: str

    def __post_init__(self) -> None:
        if len(self.roi) != 2:
            raise ValueError(f"Roi dimension count must be exactly 2, got {len(self.roi)}")

        if self.roi[0] <= 0 or self.roi[1] <= 0:
            raise ValueError(f"Roi dimensions must be strictly positive, got {self.roi}")
        
        valid_simulators: Final[list[str]] = ["icarus", "verilator", "questa", "modelsim"]
        if self.simulator not in valid_simulators:
            raise ValueError(
                f"Unsupported simulator backend '{self.simulator}', "
                f"use one of {valid_simulators}"
            )


@dataclass(frozen=True)
class OpticsConfig:
    datasets_dir:         str
    reference_image_path: str
    max_distance:         float
    step_size:            float
    ideal_focus_distance: float
    blur_sensitivity:     float


    def __post_init__(self) -> None:
        if self.max_distance <= 0.0:
            raise ValueError(f"Maximum distance must be positive, got {self.max_distance}")

        if self.step_size <= 0.0:
            raise ValueError(f"Motor step size must be positive, got {self.step_size}")

@dataclass(frozen=True)
class FocusFinderConfig:
    num_scans:  int
    lsm_points: int

    def __post_init__(self) -> None:
        if self.num_scans <= 0.0:
            raise ValueError(f"Number of scans must be positive, got {self.num_scans}")

        if self.lsm_points <= 0.0:
            raise ValueError(f"Number of LSM points must be positive, got {self.lsm_points}")

@dataclass(frozen=True)
class AppConfig:
    global_cfg:       GlobalConfig
    optics_cfg:       OpticsConfig
    focus_finder_cfg: FocusFinderConfig

    @classmethod
    def load(cls, config_path: str | Path) -> "AppConfig":
        path: Final[Path] = Path(config_path).resolve()
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found at path {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw_data: dict[str, Any] = yaml.safe_load(f)

        try:
            g_data: dict[str, Any] = raw_data["global"]
            global_obj: GlobalConfig = GlobalConfig(
                roi       = tuple(g_data["roi"]),
                simulator = str  (g_data["simulator"])
            )

            o_data: dict[str, Any] = raw_data["optics"]
            optics_obj: OpticsConfig = OpticsConfig(
                datasets_dir         = str  (o_data["datasets_dir"        ]),
                reference_image_path = str  (o_data["reference_image_path"]),
                max_distance         = float(o_data["max_distance"        ]),
                step_size            = float(o_data["step_size"           ]),
                ideal_focus_distance = float(o_data["ideal_focus_distance"]),
                blur_sensitivity     = float(o_data["blur_sensitivity"    ]),
            )

            o_data: dict[str, Any] = raw_data["focus_finder"]
            focus_finder_obj: FocusFinderConfig = FocusFinderConfig(
                num_scans  = int(o_data["num_scans"]),
                lsm_points = int(o_data["lsm_points"])
            )

            return cls(global_cfg       = global_obj,
                       optics_cfg       = optics_obj,
                       focus_finder_cfg = focus_finder_obj)

        except KeyError as e:
            raise KeyError(f"Missing mandatory configuration key {e}") from e
        except (ValueError, TypeError) as e:
            raise ValueError(f"Configuration static validation failed: {e}") from e