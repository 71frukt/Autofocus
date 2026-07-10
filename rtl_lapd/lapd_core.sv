`timescale 1ns / 1ps

module lapd_core  #(
    parameter int COLOR_WIDTH = 8,
    parameter int IMG_WIDTH   = 1920,
    parameter int IMG_HEIGHT  = 1080,
    parameter int ROI_WIDTH   = 200,
    parameter int ROI_HEIGHT  = 200
) (
    input  logic        clk,
    input  logic        rst,

    // input AXI-Stream from the camera
    input  logic [COLOR_WIDTH*3-1:0] s_axis_data,
    input  logic                     s_axis_valid,
    output logic                     s_axis_ready,

    output logic [31:0]              metric_out,
    output logic                     metric_valid
);

    localparam int FRAME_H_WIDTH  = $clog2(ROI_WIDTH);
    localparam int FRAME_V_WIDTH  = $clog2(ROI_HEIGHT);
    localparam int SCALED_H_WIDTH = FRAME_H_WIDTH;
    localparam int SCALED_V_WIDTH = FRAME_V_WIDTH;

    // cropper --> sliding window
    logic [COLOR_WIDTH*3-1:0]  cropper_data;
    logic                      cropper_valid;
    logic                      cropper_ready;
    logic                      cropper_last;
    logic                      cropper_user;

    // sliding window --> metrics counter
    logic [3*3*COLOR_WIDTH-1:0] window_data; 
    logic                       window_valid;
    logic                       window_ready;
    logic                       window_last;
    logic                       window_user;

    //---------------------------------------------------------------

    roi_cropper #(
        .DATA_WIDTH (COLOR_WIDTH * 3),
        .IMG_WIDTH  (IMG_WIDTH),
        .IMG_HEIGHT (IMG_HEIGHT),
        .ROI_WIDTH  (ROI_WIDTH),
        .ROI_HEIGHT (ROI_HEIGHT)
    ) u_cropper (
        .clk          (clk),
        .rst          (rst),
        
        .s_axis_data  (s_axis_data),
        .s_axis_valid (s_axis_valid),
        .s_axis_ready (s_axis_ready),
        
        .m_axis_data  (cropper_data),
        .m_axis_valid (cropper_valid),
        .m_axis_ready (cropper_ready),
        .m_axis_last  (cropper_last),
        .m_axis_user  (cropper_user)
    );

    //---------------------------------------------------------------

    logic [COLOR_WIDTH+1:0] rgb_sum;
    logic [COLOR_WIDTH:0]   intensity_data;

    assign rgb_sum =  cropper_data[COLOR_WIDTH-1:0]
                    + (cropper_data[2*COLOR_WIDTH-1:COLOR_WIDTH] << 1)
                    +  cropper_data[3*COLOR_WIDTH-1:2*COLOR_WIDTH];
    
    assign intensity_data = rgb_sum[COLOR_WIDTH+1:2];


    window #(
        .DATA_WIDTH      (COLOR_WIDTH),
        .N               (3),
        .M               (3),
        .ANCHOR_I        (1),
        .ANCHOR_J        (1),
        .MASK_MODE       (1),            // edge duplicate
        .MAX_HEIGHT      (ROI_HEIGHT),
        .MAX_WIDTH       (ROI_WIDTH),
        .FRAME_H_WIDTH   (FRAME_H_WIDTH),
        .FRAME_V_WIDTH   (FRAME_V_WIDTH),
        .SCALED_H_WIDTH  (SCALED_H_WIDTH),
        .SCALED_V_WIDTH  (SCALED_V_WIDTH),
        .INPUT_BUF_DEPTH (4)
    ) u_sliding_window (
        .clk             (clk),
        .rst             (rst),
        .enable          (1'b1),

        // Настройки геометрии (200х200)
        .frame_height_i  (FRAME_V_WIDTH'(ROI_HEIGHT)),
        .frame_width_i   (FRAME_H_WIDTH'(ROI_WIDTH)),
        .scaled_height_i (SCALED_V_WIDTH'(ROI_HEIGHT)),
        .scaled_width_i  (SCALED_H_WIDTH'(ROI_WIDTH)),

        // Входной поток от кроппера
        .s_axis_data     (intensity_data),
        .s_axis_valid    (cropper_valid),
        .s_axis_ready    (cropper_ready),
        .s_axis_last     (cropper_last),
        .s_axis_user     (cropper_user),

        // Выходной поток окон к сумматору
        .m_axis_data     (window_data),
        .m_axis_valid    (window_valid),
        .m_axis_ready    (window_ready),
        .m_axis_last     (window_last),
        .m_axis_user     (window_user)
    );

    //---------------------------------------------------------------

    metrics_counter #(
        .DATA_WIDTH   (COLOR_WIDTH)
    ) u_metrics_counter (
        .clk          (clk),
        .rst          (rst),

        .s_axis_data  (window_data),
        .s_axis_valid (window_valid),
        .s_axis_ready (window_ready),
        .s_axis_last  (window_last),
        .s_axis_user  (window_user),

        .metric_out    (metric_out),
        .metric_valid  (metric_valid)
    );

endmodule