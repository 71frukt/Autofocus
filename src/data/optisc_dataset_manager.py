import os
import json
import shutil
import hashlib
from typing import Any, Optional
import cv2
from pathlib import Path
import numpy as np

from src.core.optics_model   import OpticalSystemModel
from src.data.config_checker import GlobalConfig, OpticsConfig


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


def _compute_pixel_matrix_hash(image_path: str) -> str:
    """Calculates SHA-256 from the raw byte buffer of the pixel matrix"""
    img: Optional[np.ndarray] = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Couldn't upload image for hash calculation: {image_path}")
    
    canonical_buffer: bytes = np.ascontiguousarray(img).tobytes()
    return hashlib.sha256(canonical_buffer).hexdigest()


class OpticsDatasetManager:
    """Proxy encapsulating dataset versioning, hashing, and filesystem caching."""

    def __init__(self, optics_cfg: OpticsConfig) -> None:
        pythonpath: str = os.environ.get("PYTHONPATH", "")

        if pythonpath:
            self._project_root: Path = Path(pythonpath.split(":")[0]).resolve()
        else:
            self._project_root = Path(__file__).resolve().parent.parent.parent

        self._base_dir:     str = os.path.normpath(os.path.join(str(self._project_root), optics_cfg.datasets_dir))
        self._raw_ref_path: str = os.path.normpath(os.path.join(str(self._project_root), optics_cfg.reference_image_path))
        
        self._optics_cfg: OpticsConfig = optics_cfg
        
        self._optics_model: Optional[OpticalSystemModel] = None
        self._disk_saved_steps: set[int] = set()

        manifest: dict[str, Any] = self._generate_manifest(optics_cfg)
        self._dataset_dir, self._active_ref_path = self._resolve_directory(manifest)
        
        self._scan_existing_steps()

    def _generate_manifest(self, optics_cfg: OpticsConfig) -> dict[str, Any]:
        """Generates a complete dataset manifest and calculates its final hash"""

        ref_pixel_hash: str = _compute_pixel_matrix_hash(self._raw_ref_path)

        core_parameters: dict[str, Any] = {
            "reference_pixel_hash": ref_pixel_hash,
            "max_distance":         float(optics_cfg.max_distance        ),
            "step_size":            float(optics_cfg.step_size           ),
            "ideal_focus_distance": float(optics_cfg.ideal_focus_distance),
            "blur_sensitivity":     float(optics_cfg.blur_sensitivity    ),
        }

        serialized_params: str = json.dumps(core_parameters, sort_keys=True)
        full_dataset_hash: str = hashlib.sha256(serialized_params.encode("utf-8")).hexdigest()

        return {
            "dataset_hash": full_dataset_hash,
            "short_hash":   full_dataset_hash[:8],
            "parameters":   core_parameters
        }

    def _resolve_directory(self, manifest: dict[str, Any]) -> tuple[str, str]:
        os.makedirs(self._base_dir, exist_ok=True)

        target_full_hash:  str = manifest["dataset_hash"]
        target_short_hash: str = manifest["short_hash"]
        max_version:       int = 0

        # 1) Scan the directories for a suffix match
        for entry in os.listdir(self._base_dir):
            full_dir_path: str = os.path.join(self._base_dir, entry)
            if not os.path.isdir(full_dir_path) or not entry.startswith("dataset_v"):
                continue

            parts: list[str] = entry.split("_") # ['dataset', 'v12', 'a1b2c3d4']
            
            try:
                version_num: int = int(parts[1][1:])
                if version_num > max_version:
                    max_version = version_num
            except (IndexError, ValueError):
                pass

            # 2) Checking for a collision in the full manifest when the suffix matches
            if len(parts) >= 3 and parts[-1] == target_short_hash:
                manifest_path: str = os.path.join(full_dir_path, "_manifest.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            saved_manifest: dict[str, Any] = json.load(f)
                        
                        if saved_manifest.get("dataset_hash") == target_full_hash:
                            # An existing valid folder was found
                            snapshot_path: str = os.path.join(full_dir_path, "reference_snapshot.png")
                            return full_dir_path, snapshot_path
                    except (json.JSONDecodeError, OSError):
                        continue

        # 3) a valid dataset is not found -> create a new directory
        new_version: int = max_version + 1
        new_dir_name: str = f"dataset_v{new_version}_{target_short_hash}"
        new_dataset_dir: str = os.path.join(self._base_dir, new_dir_name)
        
        os.makedirs(new_dataset_dir, exist_ok=True)

        # Create a manifest
        manifest_file_path: str = os.path.join(new_dataset_dir, "_manifest.json")
        with open(manifest_file_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4, ensure_ascii=False)

        # Creating a reference snapshot inside a new folder
        snapshot_file_path: str = os.path.join(new_dataset_dir, "reference_snapshot.png")
        shutil.copy2(self._raw_ref_path, snapshot_file_path)

        return new_dataset_dir, snapshot_file_path

    def _scan_existing_steps(self) -> None:
        """Populates index of already generated steps to avoid unnecessary IO operations."""
        for filename in os.listdir(self._dataset_dir):
            if filename.startswith("step_") and filename.endswith(".png"):
                try:
                    step_id_str: str = filename.split("_")[1]
                    self._disk_saved_steps.add(int(step_id_str))
                except (IndexError, ValueError):
                    continue

    def _init_lazy_model(self) -> OpticalSystemModel:
        """Lazy initialization of the domain model upon first computation request."""
        if self._optics_model is None:
            ref_img: Optional[np.ndarray] = cv2.imread(self._active_ref_path, cv2.IMREAD_COLOR)
            if ref_img is None:
                raise FileNotFoundError(f"Could not load active reference: {self._active_ref_path}")
                
            self._optics_model = OpticalSystemModel(
                reference_image      = ref_img,
                step_size            = float(self._optics_cfg.step_size           ),
                max_distance         = float(self._optics_cfg.max_distance        ),
                ideal_focus_distance = float(self._optics_cfg.ideal_focus_distance),
                blur_sensitivity     = float(self._optics_cfg.blur_sensitivity    )
            )
        return self._optics_model

    def get_frame(self, distance: float) -> np.ndarray:
        step_size:    float = float(self._optics_cfg.step_size)
        max_distance: float = float(self._optics_cfg.max_distance)
        
        if not (0.0 <= distance <= max_distance):
            raise ValueError(f"Requested coordinate {distance:.2f} mm is out of bounds [0.0, {max_distance:.2f}]")
        
        step_id: int = int(round(distance / step_size))
        filename: str = f"step_{step_id}_dist_{distance:.2f}.png"
        file_path: str = os.path.join(self._dataset_dir, filename)

        if step_id in self._disk_saved_steps and os.path.exists(file_path):
            cached_frame: Optional[np.ndarray] = cv2.imread(file_path, cv2.IMREAD_COLOR)
            if cached_frame is not None:
                return cached_frame

        model: OpticalSystemModel = self._init_lazy_model()
        frame: np.ndarray = model.calculate_frame(distance)
        
        cv2.imwrite(file_path, frame)
        self._disk_saved_steps.add(step_id)
        
        return frame

    @property
    def dataset_dir(self) -> str:
        return self._dataset_dir
    

