import os
from typing import Any, Final, List
import yaml
import numpy as np
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge

from src.data.optisc_dataset_manager import OpticsDatasetManager
from src.data.config_checker         import AppConfig, GlobalConfig, OpticsConfig, FocusFinderConfig


@cocotb.test()
async def lapd_tb(dut) -> None:
    """Real-time pumping of real frames through the RTL module."""
    
    config_path:   Final[str | None] = os.environ.get("COCOTB_CFG_PATH")
    artifact_path: Final[str | None] = os.environ.get("COCOTB_ARTIFACT_PATH")  # there will be an array of 16 pairs [distance, metric]
    
    if not config_path or not os.path.exists(config_path):
        raise FileNotFoundError(f"The config path was not found in the environment: {config_path}")

    if not artifact_path:
        raise ValueError("The COCOTB_ARTIFACT_PATH environment variable is not set")

    config: Final[AppConfig] = AppConfig.load(config_path)

    global_cfg:       GlobalConfig      = config.global_cfg
    optics_cfg:       OpticsConfig      = config.optics_cfg
    focus_finder_cfg: FocusFinderConfig = config.focus_finder_cfg
    

    optics_manager: OpticsDatasetManager = OpticsDatasetManager(
        optics_cfg=optics_cfg
    )

    max_distance: Final[float] = float(optics_cfg.max_distance)
    num_steps:    Final[int]   = focus_finder_cfg.num_scans
    step_size:    Final[float] = max_distance / num_steps

    # clock generator (100 MHz)
    clock: Clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rstn       .value = 0
    dut.frame_strobe.value = 0
    
    await ClockCycles(dut.clk, 3)
    dut.rstn.value = 1
    await FallingEdge(dut.clk)

    # results of metric calculations
    collected_points: List[List[float]] = []


    for step in range(num_steps):
        distance: float = step * step_size
        if distance > max_distance:
            break

        _ = optics_manager.get_frame(distance)       

        dut.frame_strobe.value = 1
        await FallingEdge(dut.clk)
        dut.frame_strobe.value = 0
        await FallingEdge(dut.clk)
        
        lapd_score: float = float(dut.metric_out.value)
        collected_points.append([distance, lapd_score])
    
    points: np.ndarray = np.array(collected_points, dtype=np.float32)
    os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
    np.save(artifact_path, points)