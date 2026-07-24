// ЗАГЛУШКА


`timescale 1ns / 1ps

(* X_INTERFACE_BUS_CONTAINER = "true" *)
module pixel_throw (
    input wire clk,

    // Единый 72-битный вход матрицы от VIO (9 элементов x 8 бит)
    input wire [71:0] matrix_coeffs,

    // --- Входной интерфейс RGB ---
    (* X_INTERFACE_INFO = "xilinx.com:interface:vid_io_rtl:1.0 RGB_IN DATA"          *) input wire [23:0] rgb_in_data,
    (* X_INTERFACE_INFO = "xilinx.com:interface:vid_io_rtl:1.0 RGB_IN ACTIVE_VIDEO"  *) input wire        rgb_in_vde,
    (* X_INTERFACE_INFO = "xilinx.com:interface:vid_io_rtl:1.0 RGB_IN HSYNC"         *) input wire        rgb_in_hsync,
    (* X_INTERFACE_INFO = "xilinx.com:interface:vid_io_rtl:1.0 RGB_IN VSYNC"         *) input wire        rgb_in_vsync,

    // --- Выходной интерфейс RGB ---
    (* X_INTERFACE_INFO = "xilinx.com:interface:vid_io_rtl:1.0 RGB_OUT DATA"         *) output reg [23:0] rgb_out_data,
    (* X_INTERFACE_INFO = "xilinx.com:interface:vid_io_rtl:1.0 RGB_OUT ACTIVE_VIDEO" *) output reg        rgb_out_vde,
    (* X_INTERFACE_INFO = "xilinx.com:interface:vid_io_rtl:1.0 RGB_OUT HSYNC"        *) output reg        rgb_out_hsync,
    (* X_INTERFACE_INFO = "xilinx.com:interface:vid_io_rtl:1.0 RGB_OUT VSYNC"        *) output reg        rgb_out_vsync
);

    // Распаковываем 72-битную шину на 9 коэффициентов (по 8 бит каждый)
    wire [7:0] m11 = matrix_coeffs[7:0];
    wire [7:0] m12 = matrix_coeffs[15:8];
    wire [7:0] m13 = matrix_coeffs[23:16];

    wire [7:0] m21 = matrix_coeffs[31:24];
    wire [7:0] m22 = matrix_coeffs[39:32];
    wire [7:0] m23 = matrix_coeffs[47:40];

    wire [7:0] m31 = matrix_coeffs[55:48];
    wire [7:0] m32 = matrix_coeffs[63:56];
    wire [7:0] m33 = matrix_coeffs[71:64];

    // Выделяем входные цвета R, G, B
    wire [7:0] r_in = rgb_in_data[23:16];
    wire [7:0] g_in = rgb_in_data[15:8];
    wire [7:0] b_in = rgb_in_data[7:0];

    // --- ТАКТ 1: Умножение и сложение ---
    reg [16:0] r_sum, g_sum, b_sum;
    reg vde_st1, hsync_st1, vsync_st1;

    always @(posedge clk) begin
        r_sum <= (r_in  * m11) + (g_in * m12) + (b_in * m13);
        g_sum <= (r_sum * m21) + (g_in * m22) + (b_in * m23);
        b_sum <= (r_in  * m31) + (g_in * m32) + (b_in * m33);

        vde_st1   <= rgb_in_vde;
        hsync_st1 <= rgb_in_hsync;
        vsync_st1 <= rgb_in_vsync;
    end

    // --- ТАКТ 2: Масштабирование (>> 7) и Ограничение (Clamping) ---
    wire [9:0] r_scaled = r_sum >> 7;
    wire [9:0] g_scaled = g_sum >> 7;
    wire [9:0] b_scaled = b_sum >> 7;

    always @(posedge clk) begin
        if (vde_st1) begin
            rgb_out_data[23:16] <= (r_scaled > 255) ? 8'd255 : r_scaled[7:0];
            rgb_out_data[15:8]  <= (g_scaled > 255) ? 8'd255 : g_scaled[7:0];
            rgb_out_data[7:0]   <= (b_scaled > 255) ? 8'd255 : b_scaled[7:0];
        end
        
        else begin
            rgb_out_data <= 24'b0; // Во время пауз гашения держим 0!
        end

        rgb_out_vde   <= vde_st1;
        rgb_out_hsync <= hsync_st1;
        rgb_out_vsync <= vsync_st1;
    end

endmodule