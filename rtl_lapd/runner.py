import os
from pathlib import Path
from typing import Final
import numpy as np
from cocotb_tools.runner import get_runner

from src.data.config_checker import GlobalConfig, OpticsConfig

class RtlLapdSimulationRunner:

    def __init__(
        self,
        project_root: str | Path,
        config_path:  str | Path,
        global_cfg: GlobalConfig,
        optics_cfg: OpticsConfig
    ) -> None:
        
        self._project_root:  Final[Path] = Path(project_root).resolve()
        self._config_path:   Final[Path] = Path(config_path). resolve()

        if not self._project_root.exists():
            raise FileNotFoundError(f"The project root directory could not be found: {self._project_root}")
        
        if not self._config_path.exists():
            raise FileNotFoundError(f"No configuration file found for RTL: {self._config_path}")

        self._rtl_dir:       Final[Path] = self._project_root / "rtl_lapd"
        
        cropper_source     = self._rtl_dir / "roi_cropper.sv"
        accumulator_source = self._rtl_dir / "metrics_counter.sv"
        top_source         = self._rtl_dir / "lapd_core.sv"

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
            str(cropper_source.resolve()),
            str(accumulator_source.resolve()),
            str(top_source.resolve())
        ] + [str(src.resolve()) for src in window_sources] 

        self._build_dir:     Final[Path] = self._rtl_dir / "sim_build"
        self._artifact_path: Final[Path] = self._build_dir / "rtl_lapd_results.npy"        
        
        self._global_cfg:    Final[GlobalConfig] = global_cfg
        self._optics_cfg:    Final[OpticsConfig] = optics_cfg



    def run_focus_evaluation(self) -> np.ndarray:
        """executes the hardware simulation pipeline and returns evaluated focus metrics"""
        
        # setup inter-process communication channels  via environment variables
        os.environ["COCOTB_CFG_PATH"]      = str(self._config_path)
        os.environ["COCOTB_ARTIFACT_PATH"] = str(self._artifact_path)

        # inject project root into pythonpath for child verification process
        current_pythonpath: str = os.environ.get("PYTHONPATH", "")
        os.environ["PYTHONPATH"] = f"{self._project_root}:{current_pythonpath}"

        sim_manager = get_runner(self._global_cfg.simulator)

        img_resolution: tuple[int, int] = self._optics_cfg.img_resolution
        roi           : tuple[int, int] = self._optics_cfg.roi 

        lapd_core_parameters = {
            "IMG_WIDTH":  int(img_resolution[0]),
            "IMG_HEIGHT": int(img_resolution[1]),
            "ROI_WIDTH":  int(roi[0]),
            "ROI_HEIGHT": int(roi[1])
        }


        # compile systemverilog sources
        sim_manager.build(
            sources=self._all_sources,
            hdl_toplevel="lapd_core",
            build_dir=self._build_dir,
            includes=[self._window_include],
            parameters=lapd_core_parameters,
            always=True
        )

        # execute verification testbench against compiled design
        sim_manager.test(
            hdl_toplevel="lapd_core",
            test_module="lapd_tb",
            test_dir=self._rtl_dir,
            build_dir=self._build_dir
        )

        # verify that simulation backend successfully generated result array
        if not self._artifact_path.exists():
            raise RuntimeError(
                f"simulation backend '{self._global_cfg.simulator}' finished "
                f"but failed to produce artifact at {self._artifact_path}"
            )

        results: np.ndarray = np.load(self._artifact_path)
        return results