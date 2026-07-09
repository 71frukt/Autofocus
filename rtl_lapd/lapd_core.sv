`timescale 1ns / 1ps

module lapd_core (
    input  logic        clk,
    input  logic        rstn,
    input  logic        frame_strobe,
    output logic [31:0] metric_out
);

    logic signed [31:0] step_cnt;
    logic signed [31:0] diff;

    always_ff @(posedge clk)
    begin
        if (!rstn)
        begin
            step_cnt   <= 32'sd0;
            metric_out <= 32'd0;
        end

        else begin
            if (frame_strobe)
            begin
                // calculate distance from ideal focus step (assuming step 8 is ideal)
                // parabola: S = 20000 - 150 * (step - 8)^2
                
                diff = step_cnt - 32'sd8;
                metric_out <= 32'(32'sd20000 - (diff * diff * 32'sd150));

                step_cnt <= step_cnt + 32'sd1;
            end
        end
    end

endmodule