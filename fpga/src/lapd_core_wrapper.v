`timescale 1ns / 1ps

(* X_INTERFACE_BUS_CONTAINER = "true" *)
module lapd_core_wrapper #(
    parameter COLOR_WIDTH  = 8,
    parameter METRIC_WIDTH = 32,
    parameter IMG_WIDTH    = 1920,
    parameter IMG_HEIGHT   = 1080,
    parameter ROI_WIDTH    = 200,
    parameter ROI_HEIGHT   = 200
) (
    input wire clk,
    input wire rst,

    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis TDATA"  *) input  wire [COLOR_WIDTH*3-1:0] s_axis_data,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis TVALID" *) input  wire                     s_axis_valid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis TREADY" *) output wire                     s_axis_ready,

    output wire [METRIC_WIDTH-1:0] metric_out,
    output wire                    metric_valid
);

    lapd_core #(
        .COLOR_WIDTH  (COLOR_WIDTH),
        .METRIC_WIDTH (METRIC_WIDTH),
        .IMG_WIDTH    (IMG_WIDTH),
        .IMG_HEIGHT   (IMG_HEIGHT),
        .ROI_WIDTH    (ROI_WIDTH),
        .ROI_HEIGHT   (ROI_HEIGHT)
    ) u_lapd_core_inst (
        .clk          (clk),
        .rst          (rst),

        .s_axis_data  (s_axis_data),
        .s_axis_valid (s_axis_valid),
        .s_axis_ready (s_axis_ready),

        .metric_out   (metric_out),
        .metric_valid (metric_valid)
    );

endmodule
