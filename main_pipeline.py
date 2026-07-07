import os
import shutil
import json
import hashlib
from typing import Any, Optional
import cv2
import numpy as np
import yaml
from src.optics_model import OpticalSystemModel


def _compute_pixel_matrix_hash(image_path: str) -> str:
    """Calculates SHA-256 from the raw byte buffer of the pixel matrix"""
    img: Optional[np.ndarray] = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Couldn't upload image for hash calculation: {image_path}")
    
    canonical_buffer: bytes = np.ascontiguousarray(img).tobytes()
    return hashlib.sha256(canonical_buffer).hexdigest()


def _generate_dataset_manifest(global_cfg: dict[str, Any], optics_cfg: dict[str, Any]) -> dict[str, Any]:
    """Generates a complete dataset manifest and calculates its final hash"""
    ref_path: str = optics_cfg["reference_image_path"]
    ref_pixel_hash: str = _compute_pixel_matrix_hash(ref_path)

    core_parameters: dict[str, Any] = {
        "reference_pixel_hash": ref_pixel_hash,
        "max_distance":         float(optics_cfg["max_distance"        ]),
        "step_size":            float(optics_cfg["step_size"           ]),
        "ideal_focus_distance": float(optics_cfg["ideal_focus_distance"]),
        "blur_sensitivity":     float(optics_cfg["blur_sensitivity"    ]),
        "roi":                  list (global_cfg["roi"                 ]),
    }

    serialized_params: str = json.dumps(core_parameters, sort_keys=True)
    full_dataset_hash: str = hashlib.sha256(serialized_params.encode("utf-8")).hexdigest()

    manifest: dict[str, Any] = {
        "dataset_hash": full_dataset_hash,
        "short_hash":   full_dataset_hash[:8],
        "parameters":   core_parameters
    }

    return manifest


def _resolve_dataset_directory(base_dir: str, manifest: dict[str, Any], ref_source_path: str) -> str:
    os.makedirs(base_dir, exist_ok=True)

    target_full_hash:  str = manifest["dataset_hash"]
    target_short_hash: str = manifest["short_hash"]
    max_version: int = 0

    # 1) Scan the directories for a suffix match
    for entry in os.listdir(base_dir):
        full_dir_path: str = os.path.join(base_dir, entry)
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
    new_dataset_path: str = os.path.join(base_dir, new_dir_name)
    
    os.makedirs(new_dataset_path, exist_ok=True)

    # Create a manifest
    manifest_file_path: str = os.path.join(new_dataset_path, "_manifest.json")
    with open(manifest_file_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4, ensure_ascii=False)

    # Creating a reference snapshot inside a new folder
    snapshot_file_path: str = os.path.join(new_dataset_path, "reference_snapshot.png")
    shutil.copy2(ref_source_path, snapshot_file_path)

    return new_dataset_path, snapshot_file_path


def main() -> None:
    config_path: str = "config.yaml"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Файл конфигурации не найден: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config: dict[str, Any] = yaml.safe_load(f)

    global_cfg: dict[str, Any] = config["global"]
    optics_cfg: dict[str, Any] = config["optics"]

    manifest: dict[str, Any] = _generate_dataset_manifest(global_cfg, optics_cfg)

    base_datasets_dir: str = optics_cfg["datasets_dir"]
    ref_image_source_path: str = optics_cfg["reference_image_path"]

    target_dataset_dir, target_reference_path = _resolve_dataset_directory(
        base_dir        = base_datasets_dir,
        manifest        = manifest,
        ref_source_path = ref_image_source_path
    )

    print(f"[INFO] Active dataset directory: {target_dataset_dir}")
    print(f"[INFO] Used reference file: {target_reference_path}")

    optics = OpticalSystemModel(
        reference_image_path = target_reference_path,
        step_size            = float(optics_cfg["step_size"]),
        max_distance         = float(optics_cfg["max_distance"]),
        ideal_focus_distance = float(optics_cfg["ideal_focus_distance"]),
        roi_size             = tuple(global_cfg["roi"]),
        blur_sensitivity     = float(optics_cfg["blur_sensitivity"]),
        dataset_dir          = target_dataset_dir
    )

    step_size: float = float(optics_cfg["step_size"])
    max_distance: float = float(optics_cfg["max_distance"])
    num_steps: int = int(round(max_distance / step_size)) + 1

    print(f"[INFO] Starting processing {num_steps} positions...")

    for step in range(num_steps):
        distance: float = step * step_size
        if distance > max_distance:
            break

        _ = optics.get_frame(distance)
        print(f"[STEP {step:02d}/{num_steps - 1}] The coordinate has been processed: {distance:.1f} mm")

    print("[INFO] Done.")


if __name__ == "__main__":
    main()