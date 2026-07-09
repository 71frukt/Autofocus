import os
from pathlib import Path
from typing import Final
import numpy as np
from cocotb_tools.runner import get_runner

from src.data.config_checker import GlobalConfig

class RtlLapdSimulationRunner:

    def __init__(
        self,
        project_root: str | Path,
        config_path:  str | Path,
        global_cfg: GlobalConfig
    ) -> None:
        
        self._project_root:  Final[Path] = Path(project_root).resolve()
        self._config_path:   Final[Path] = Path(config_path). resolve()

        if not self._project_root.exists():
            raise FileNotFoundError(f"The project root directory could not be found: {self._project_root}")
        
        if not self._config_path.exists():
            raise FileNotFoundError(f"No configuration file found for RTL: {self._config_path}")

        self._rtl_dir:       Final[Path] = self._project_root / "rtl_lapd"
        self._hdl_source:    Final[Path] = self._rtl_dir / "lapd_core.sv"

        if not self._hdl_source.exists():
            raise FileNotFoundError(f"hdl source file not found at {self._hdl_source}")

        self._build_dir:     Final[Path] = self._rtl_dir / "sim_build"
        self._artifact_path: Final[Path] = self._build_dir / "rtl_lapd_results.npy"        
        
        self._global_cfg:    Final[GlobalConfig] = global_cfg



    def run_focus_evaluation(self) -> np.ndarray:
        """executes the hardware simulation pipeline and returns evaluated focus metrics"""
        
        # setup inter-process communication channels  via environment variables
        os.environ["COCOTB_CFG_PATH"]      = str(self._config_path)
        os.environ["COCOTB_ARTIFACT_PATH"] = str(self._artifact_path)

        # inject project root into pythonpath for child verification process
        current_pythonpath: str = os.environ.get("PYTHONPATH", "")
        os.environ["PYTHONPATH"] = f"{self._project_root}:{current_pythonpath}"

        sim_manager = get_runner(self._global_cfg.simulator)

        # compile systemverilog sources
        sim_manager.build(
            sources=[self._hdl_source],
            hdl_toplevel="lapd_core",
            build_dir=self._build_dir,
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