`timescale 1ns / 1ps

module metrics_counter #(
    parameter int DATA_WIDTH = 8
) (
    input  logic                       clk,
    input  logic                       rst,

    // intput AXI-Stream to a sliding window_flat
    input  logic [3*3*DATA_WIDTH-1:0]  s_axis_data,
    input  logic                       s_axis_valid,

    output logic                       s_axis_ready,
    input  logic                       s_axis_last,  // end of ROI frame
    input  logic                       s_axis_user,  // end of ROI line

    output logic [31:0]                metric_out,
    output logic                       metric_valid
);

    logic [DATA_WIDTH-1:0] window_flat [0:3*3-1];

    always_comb begin
        for (int i = 0; i < 3*3; i++) begin
            window_flat[i] = s_axis_data[i*DATA_WIDTH +: DATA_WIDTH];
        end
    end

    logic [DATA_WIDTH+3:0] window_sum;

    always_comb begin
        window_sum = 12'd0;

        for (int i = 0; i < 3*3; i++) begin
            window_sum = window_sum + window_flat[i];
        end
    end
    
    logic [31:0] frame_accumulator;

    assign s_axis_ready = 1'b1;

    // metric calculation stub: sum of squared intensities
    always_ff @(posedge clk) begin
        if (rst) begin
            frame_accumulator <= 0;
            metric_out        <= 0;
            metric_valid      <= 1'b0;
        end
        
        else begin
            // handshake
            if (s_axis_valid && s_axis_ready) begin
                if (s_axis_last) begin
                    // frame completed
                    metric_out        <= frame_accumulator + window_sum;
                    metric_valid      <= 1'b1; 
                    frame_accumulator <= 0;
                end
                
                else begin
                    frame_accumulator <= frame_accumulator + window_sum;
                    metric_valid      <= 1'b0;
                end
            end
            
            else begin
                metric_valid <= 1'b0;
            end
        end
    end

endmodule