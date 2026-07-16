`timescale 1ns / 1ps

module metrics_counter #(
    parameter DATA_WIDTH   = 8,
    parameter METRIC_WIDTH = 32
) (
    input  logic                       clk,
    input  logic                       rst,

    input  logic [3*3*DATA_WIDTH-1:0]  s_axis_data,
    input  logic                       s_axis_valid,
    output logic                       s_axis_ready,
    input  logic                       s_axis_last,  // ROI  end flag
    input  logic                       s_axis_user,  // line end flag

    output logic [METRIC_WIDTH-1:0]    metric_out,
    output logic                       metric_valid
);

    localparam int COEF_707 = 724;    // 1/sqrt(2) * 2^10

    // [0] [1] [2]
    // [3] [4] [5]
    // [6] [7] [8]
    logic [DATA_WIDTH-1:0] window [0:8];
    always_comb begin
        for (int i = 0; i < 9; i++) begin
            window[i] = s_axis_data[i*DATA_WIDTH +: DATA_WIDTH];
        end
    end

    // --- 4-stage Pipeline ---
    logic v_st1, v_st2, v_st3;  // pipeline valid
    logic l_st1, l_st2, l_st3;  // pipeline last
    
    always_ff @(posedge clk) begin
        v_st1 <= s_axis_valid;  v_st2 <= v_st1;  v_st3 <= v_st2;
        l_st1 <= s_axis_last;   l_st2 <= l_st1;  l_st3 <= l_st2;
    end

    // stage 1
    logic signed [DATA_WIDTH+2:0] res_k_raw;
    logic signed [DATA_WIDTH+2:0] res_kd1_raw;
    logic signed [DATA_WIDTH+2:0] res_kd2_raw;

    always_ff @(posedge clk) begin
        if (s_axis_valid) begin
            //     |  0 -1  0 |
            // K = | -1  4 -1 |
            //     |  0 -1  0 |
            res_k_raw   <= (signed'({1'b0, window[4]}) <<< 2) - 
                            signed'({1'b0, window[1]}) - signed'({1'b0, window[3]}) - 
                            signed'({1'b0, window[5]}) - signed'({1'b0, window[7]});
            
            //       | 0  0  1 |
            // KD1 = | 0 -2  0 |
            //       | 1  0  0 |
            res_kd1_raw <= signed'({1'b0, window[2]}) + signed'({1'b0, window[6]}) - 
                          (signed'({1'b0, window[4]}) <<< 1);
            
            //       | 1  0  0 |
            // KD2 = | 0 -2  0 |
            //       | 0  0  1 |
            res_kd2_raw <= signed'({1'b0, window[0]}) + signed'({1'b0, window[8]}) - 
                          (signed'({1'b0, window[4]}) <<< 1);
        end
    end

    // stage 2
    logic [DATA_WIDTH+2+10:0] abs_k;
    logic [DATA_WIDTH+2+10:0] abs_kd1;
    logic [DATA_WIDTH+2+10:0] abs_kd2;

    always_ff @(posedge clk) begin
        abs_k   <= (res_k_raw   < 0 ? -res_k_raw   : res_k_raw  ) << 10; 
        abs_kd1 <= (res_kd1_raw < 0 ? -res_kd1_raw : res_kd1_raw) * COEF_707;
        abs_kd2 <= (res_kd2_raw < 0 ? -res_kd2_raw : res_kd2_raw) * COEF_707;
    end

    logic [DATA_WIDTH+2+10+2:0] pix_lapd;

    // stage 3
    always_ff @(posedge clk) begin
        pix_lapd <= abs_k + abs_kd1 + abs_kd2;
    end

    // stage 4
    logic [47:0] frame_acc;

    assign s_axis_ready = 1'b1;

    always_ff @(posedge clk) begin
        if (rst) begin
            frame_acc    <= '0;
            metric_out   <= '0;
            metric_valid <= 1'b0;
        end
        
        else begin
            if (v_st3) begin
                if (l_st3) begin
                    // Конец кадра ROI: выдаем результат
                    // Сдвигаем обратно на 10 бит (отмена fixed-point масштаба), 
                    // чтобы результат соответствовал порядку величин в Python
                    metric_out   <= 32'((frame_acc + pix_lapd) >> 10);
                    metric_valid <= 1'b1;
                    frame_acc    <= '0;
                end
                
                else begin
                    frame_acc    <= frame_acc + pix_lapd;
                    metric_valid <= 1'b0;
                end
            end
            
            else begin
                metric_valid <= 1'b0;
            end
        end
    end

endmodule