`timescale 1ns / 1ps

(* X_INTERFACE_BUS_CONTAINER = "true" *)
module rgb2axis (
    input wire clk,

    (* X_INTERFACE_INFO = "xilinx.com:interface:vid_io_rtl:1.0 RGB_IN DATA"          *) input wire [23:0] rgb_in_data,
    (* X_INTERFACE_INFO = "xilinx.com:interface:vid_io_rtl:1.0 RGB_IN ACTIVE_VIDEO"  *) input wire        rgb_in_vde,
    (* X_INTERFACE_INFO = "xilinx.com:interface:vid_io_rtl:1.0 RGB_IN HSYNC"         *) input wire        rgb_in_hsync,
    (* X_INTERFACE_INFO = "xilinx.com:interface:vid_io_rtl:1.0 RGB_IN VSYNC"         *) input wire        rgb_in_vsync,

    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis TDATA"  *) output reg [23:0] m_axis_data,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis TVALID" *) output reg        m_axis_valid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis TREADY" *) input  wire       m_axis_ready,

    // Импульс сброса перед началом кадра
    output reg frame_rst
);

    reg vsync_d1;

    always @(posedge clk) begin
        m_axis_data  <= rgb_in_data;
        m_axis_valid <= rgb_in_vde;

        vsync_d1  <= rgb_in_vsync;
        frame_rst <= rgb_in_vsync && !vsync_d1;
    end

endmodule
