module lapd_top #(
    parameter COLOR_WIDTH    = 8,
    parameter IMG_WIDTH      = 1920,
    parameter IMG_HEIGHT     = 1080,
    parameter ROI_WIDTH      = 128,
    parameter ROI_HEIGHT     = 128,
    parameter FRAME_BIN_PATH = "input_frame.bin"
)(
    input logic clk,
    input logic rst,
    input logic frame_start,
    
    output logic metric_valid,
    output logic [31:0] metric_out
);

    logic [COLOR_WIDTH*3-1:0] s_axis_data;
    logic                     s_axis_valid;
    logic                     s_axis_ready;

    frame_reader #(
        .FRAME_BIN_PATH(FRAME_BIN_PATH),
        .WIDTH         (IMG_WIDTH),
        .HEIGHT        (IMG_HEIGHT),
        .DATA_WIDTH    (COLOR_WIDTH * 3)
    ) u_frame_reader (
        .clk           (clk),
        .rst           (rst),
        .frame_start   (frame_start),
        .m_axis_data   (s_axis_data),
        .m_axis_valid  (s_axis_valid),
        .m_axis_ready  (s_axis_ready)
    );

    lapd_core #(
        .COLOR_WIDTH   (COLOR_WIDTH),
        .IMG_WIDTH     (IMG_WIDTH),
        .IMG_HEIGHT    (IMG_HEIGHT),
        .ROI_WIDTH     (ROI_WIDTH),
        .ROI_HEIGHT    (ROI_HEIGHT)
    ) u_core (
        .clk           (clk),
        .rst           (rst),
        
        .s_axis_data   (s_axis_data),
        .s_axis_valid  (s_axis_valid),
        .s_axis_ready  (s_axis_ready),
        
        .metric_valid  (metric_valid),
        .metric_out    (metric_out)
    );

endmodule