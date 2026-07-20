`timescale 1ns / 1ps

module roi_cropper #(
    parameter int DATA_WIDTH = 8,
    parameter int IMG_WIDTH  = 1920,
    parameter int IMG_HEIGHT = 1080,
    parameter int ROI_WIDTH  = 200,
    parameter int ROI_HEIGHT = 200
) (
    input  logic                    clk,
    input  logic                    rst,

    // input AXI-Stream from the camera
    input  logic [DATA_WIDTH-1:0]   s_axis_data,
    input  logic                    s_axis_valid,
    output logic                    s_axis_ready,

    // output AXI-Stream to a sliding window
    input  logic                    m_axis_ready,
    output logic [DATA_WIDTH-1:0]   m_axis_data,
    output logic                    m_axis_valid,
    output logic                    m_axis_last, // end of ROI frame
    output logic                    m_axis_user  // end of ROI line
);

    // ROI boundares
    localparam int X_START = (IMG_WIDTH  - ROI_WIDTH ) / 2;
    localparam int Y_START = (IMG_HEIGHT - ROI_HEIGHT) / 2;
    localparam int X_END   = X_START + ROI_WIDTH  - 1;
    localparam int Y_END   = Y_START + ROI_HEIGHT - 1;

    logic [$clog2(IMG_WIDTH)-1:0]  x_cnt;
    logic [$clog2(IMG_HEIGHT)-1:0] y_cnt;

    logic  in_roi;
    assign in_roi = (x_cnt >= X_START && x_cnt <= X_END) && 
                    (y_cnt >= Y_START && y_cnt <= Y_END);

    assign s_axis_ready = in_roi ? m_axis_ready : 1'b1;
    assign m_axis_valid = s_axis_valid && in_roi;
    assign m_axis_data  = s_axis_data;
    
    assign m_axis_user = in_roi && (x_cnt == X_END);
    assign m_axis_last = in_roi && (x_cnt == X_END) && (y_cnt == Y_END);

    always_ff @(posedge clk) begin
        if (rst) begin
            x_cnt <= 0;
            y_cnt <= 0;
        end 
        
        else begin
            // handshake
            if (s_axis_valid && s_axis_ready) begin
                if (x_cnt == IMG_WIDTH - 1) begin
                    x_cnt <= 0;
                    
                    if (y_cnt == IMG_HEIGHT - 1)
                        y_cnt <= 0;
                    
                    else
                        y_cnt <= y_cnt + 1;
                end
                
                else
                    x_cnt <= x_cnt + 1;
            end
        end
    end

endmodule