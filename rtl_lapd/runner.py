import os
from pathlib import Path
from typing import Final
import numpy as np
import subprocess
from cocotb_tools.runner import get_runner

from src.data.optisc_dataset_manager import OpticsDatasetManager
from src.data.config_checker         import OpticsConfig, FocusFinderConfig

class RtlLapdSimulationRunner:

    def __init__(
        self,
        project_root    : str | Path,
        focus_finder_cfg: FocusFinderConfig,
        optics_cfg      : OpticsConfig
    ) -> None:
        
        self._project_root:   Final[Path] = Path(project_root).resolve()

        if not self._project_root.exists():
            raise FileNotFoundError(f"The project root directory could not be found: {self._project_root}")
        
        self._rtl_dir          : Final[Path]              = self._project_root / "rtl_lapd"
        self._build_dir        : Final[Path]              = self._rtl_dir      / "sim_build"
        self._metrics_path      : Final[Path]              = self._build_dir    / "metrics.txt"        
        self._frames_bins_dir  : Final[Path]              = self._build_dir    / "frames_bins"
        
        self._optics_cfg       : Final[OpticsConfig     ] = optics_cfg
        self._focus_finder_cfg : Final[FocusFinderConfig] = focus_finder_cfg


        cropper_source     = self._rtl_dir / "roi_cropper.sv"
        accumulator_source = self._rtl_dir / "metrics_counter.sv"
        lapd_core_source   = self._rtl_dir / "lapd_core.sv"
        top_source         = self._rtl_dir / "lapd_tb.sv"

        window_dir = (self._rtl_dir / ".." / "window_final").resolve()
        if not window_dir.exists():
            raise FileNotFoundError(f"The window_final directory was not found: {window_dir}")
        
        window_sources = list(window_dir.glob("*.v")) + list(window_dir.glob("*.sv"))
        if not window_sources:
            raise FileNotFoundError(f"No Verilog/SystemVerilog source files found in: {window_dir}")

        self._window_include = (window_dir / "include").resolve()
        if not self._window_include.exists():
            raise FileNotFoundError(f"The sliding window include code was not found in the path: {self._window_include}")

        self._all_sources = [
            str(cropper_source    .resolve()),
            str(accumulator_source.resolve()),
            str(lapd_core_source  .resolve()),
            str(top_source        .resolve())
        ] + [str(src.resolve()) for src in window_sources] 

        
    def run_focus_evaluation(self) -> np.ndarray:
        """executes the hardware simulation pipeline and returns evaluated focus metrics"""

        self._generate_bin_frames()
        self._build_rtl()
        self._run_rtl_simulation()

        if not self._metrics_path.exists():
            raise RuntimeError(
                f"simulation backend 'icarus' finished "
                f"but failed to produce artifact at {self._metrics_path}"
            )

        metrics: np.ndarray = np.loadtxt(self._metrics_path)
        return metrics
    


    def _generate_bin_frames(self) -> None:
        self._frames_bins_dir.mkdir(parents=True, exist_ok=True)

        optics_manager: OpticsDatasetManager = OpticsDatasetManager(
            optics_cfg = self._optics_cfg
        )
        
        num_steps = self._focus_finder_cfg.num_scans
        step_size = float(self._optics_cfg.max_distance) / num_steps

        for step in range(num_steps):
            distance = step * step_size
            
            frame = optics_manager.get_frame(distance)
            binary_data = frame[:, :, :3].astype(np.uint8).tobytes()
            
            with open(f"{self._frames_bins_dir}/frame_{step}.bin", "wb") as f:
                f.write(binary_data)
                    
        print(f"[INFO] Bin frames are ready")


    def _build_rtl(self) -> None:
        sim_manager = get_runner("icarus")

        img_resolution: tuple[int, int] = self._optics_cfg.img_resolution
        roi           : tuple[int, int] = self._optics_cfg.roi 

        lapd_core_parameters = {
            "COLOR_WIDTH"    : int(8),
            "IMG_WIDTH"      : int(img_resolution[0]),
            "IMG_HEIGHT"     : int(img_resolution[1]),
            "ROI_WIDTH"      : int(roi[0]),
            "ROI_HEIGHT"     : int(roi[1]),
            "FRAMES_BINS_DIR": f'"{self._frames_bins_dir}"',
            "NUM_STEPS"      : int(self._focus_finder_cfg.num_scans),
            "METRICS_PATH"   : f'"{self._metrics_path}"'
        }

        sim_manager.build(
            sources      = self._all_sources,
            hdl_toplevel = "lapd_tb",
            build_dir    = self._build_dir,
            includes     = [self._window_include],
            parameters   = lapd_core_parameters,
            always       = True
        )


    def _run_rtl_simulation(self) -> None:
        run_command = [
            "vvp", 
            str(self._build_dir / "sim.vvp")
        ]

        print(f"[INFO] Starting RTL simulation: {' '.join(run_command)}")

        with subprocess.Popen(
            run_command,
            stdout  = subprocess.PIPE,
            stderr  = subprocess.STDOUT,
            text    = True,
            bufsize = 1
        ) as process:
            for line in process.stdout:
                print(line, end='', flush=True)

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, run_command)