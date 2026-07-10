import os
from typing import Final, List, Optional
import numpy as np
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge

from src.data.optisc_dataset_manager import OpticsDatasetManager
from src.data.config_checker         import AppConfig, OpticsConfig, FocusFinderConfig


@cocotb.test()
async def lapd_tb(dut) -> None:
    """Real-time pumping of real frames through the RTL module."""
    
    config_path:   Final[str | None] = os.environ.get("COCOTB_CFG_PATH")
    artifact_path: Final[str | None] = os.environ.get("COCOTB_ARTIFACT_PATH")  # there will be an array of 16 pairs [distance, metric]
    
    if not config_path or not os.path.exists(config_path):
        raise FileNotFoundError(f"The config path was not found in the environment: {config_path}")

    if not artifact_path:
        raise ValueError("The COCOTB_ARTIFACT_PATH environment variable is not set")

    config:           Final[AppConfig]         = AppConfig.load(config_path)
    optics_cfg:       Final[OpticsConfig]      = config.optics_cfg
    focus_finder_cfg: Final[FocusFinderConfig] = config.focus_finder_cfg
    

    optics_manager: OpticsDatasetManager = OpticsDatasetManager(
        optics_cfg=optics_cfg
    )

    max_distance: Final[float] = float(optics_cfg.max_distance)
    num_steps:    Final[int]   = focus_finder_cfg.num_scans
    step_size:    Final[float] = max_distance / num_steps

    # clock generator (100 MHz)
    clock: Clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst         .value = 1
    dut.s_axis_valid.value = 0
    dut.s_axis_data .value = 0
    
    await ClockCycles(dut.clk, 3)
    dut.rst.value = 0
    await FallingEdge(dut.clk)

    # results of metric calculations
    collected_points: List[List[float]] = []

    metric_value: Optional[float] = None

    async def metric_monitor():
        nonlocal metric_value
        while True:
            await FallingEdge(dut.clk)
            if dut.metric_valid.value == 1:
                metric_value = float(dut.metric_out.value)

    cocotb.start_soon(metric_monitor())

    for step in range(num_steps):
        distance: float = step * step_size
        if distance > max_distance:
            break

        frame: np.ndarray = optics_manager.get_frame(distance)       
        r = frame[:, :, 0].astype(np.uint32)
        g = frame[:, :, 1].astype(np.uint32)
        b = frame[:, :, 2].astype(np.uint32)
        
        packed_frame = r | (g << 8) | (b << 16)
        
        flat_pixels = packed_frame.flatten()

        cocotb.log.info(f"Start sending a frame for a distance {distance:.3f} mm...")

        for pixel in flat_pixels:
            dut.s_axis_data.value  = int(pixel)
            dut.s_axis_valid.value = 1

            await FallingEdge(dut.clk)
            
            while not dut.s_axis_ready.value:
                await FallingEdge(dut.clk)

        dut.s_axis_valid.value = 0
        cocotb.log.info("The frame has been fully sent. Waiting for metric calculation...")


        while metric_value is None:
            await FallingEdge(dut.clk)

        cocotb.log.info(f"The metric is received.")
        
        collected_points.append([distance, metric_value])
    
    points: np.ndarray = np.array(collected_points, dtype=np.float32)
    os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
    np.save(artifact_path, points)
    
    cocotb.log.info("The simulation has been successfully completed")



    