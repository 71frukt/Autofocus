`timescale 1ns / 1ps

module lapd_tb #(
    parameter COLOR_WIDTH     = 8,
    parameter METRIC_WIDTH   = 32,

    parameter IMG_WIDTH       = 1920,
    parameter IMG_HEIGHT      = 1080,
    parameter ROI_WIDTH       = 200,
    parameter ROI_HEIGHT      = 200,

    parameter FRAMES_BINS_DIR = "sim_build",
    parameter METRICS_PATH    = "metrics.txt",
    parameter NUM_STEPS       = 16
);

    logic                     clk = 0;
    logic                     rst;

    logic [COLOR_WIDTH*3-1:0] pixel_data;
    logic                     pixel_valid = 0;
    logic                     pixel_ready;

    logic [METRIC_WIDTH-1:0]  metrics_data;
    logic                     metrics_valid;
    

    lapd_core #(
        .METRIC_WIDTH (METRIC_WIDTH),
        .COLOR_WIDTH   (COLOR_WIDTH),
        .IMG_WIDTH     (IMG_WIDTH  ),
        .IMG_HEIGHT    (IMG_HEIGHT ),
        .ROI_WIDTH     (ROI_WIDTH  ),
        .ROI_HEIGHT    (ROI_HEIGHT )
    ) dut (
        .clk           (clk),
        .rst           (rst),
        .s_axis_data   (pixel_data),
        .s_axis_valid  (pixel_valid),
        .s_axis_ready  (pixel_ready),
        .metric_out    (metrics_data),
        .metric_valid  (metrics_valid)
    );


    // 100 MHz
    always #5 clk = ~clk;

    int metrics_fd;
    int metrics_received = 0;

    string frame_path;
    int frame_fd;
    int bytes_read;

    initial begin
        rst = 1;
        repeat (3) @(posedge clk);
        rst = 0;

        metrics_fd = $fopen(METRICS_PATH, "w");
        if (metrics_fd == 0) begin
            $fatal(1, "[TB ERROR] Could not open file: %s", METRICS_PATH);
        end

        for (int frame_num = 0; frame_num < NUM_STEPS; ++frame_num) begin
            $display("[INFO] Running frame %0d", frame_num);
            $fflush();

            frame_path = $sformatf("%s/frame_%0d.bin", FRAMES_BINS_DIR, frame_num);

            frame_fd = $fopen(frame_path, "rb");
            if (frame_fd == 0) begin
                $fatal(1, "[TB ERROR] Could not open file: %s", frame_path);
            end

            for (int y = 0; y < IMG_HEIGHT; ++y) begin
                for (int x = 0; x < IMG_WIDTH; ++x) begin
                   
                    bytes_read = $fread(pixel_data, frame_fd);
                    if (bytes_read != 3) begin
                        $display("[TB ERROR] Failed to read pixel. Expected 3 bytes, got %0d", bytes_read);
                        $fatal(1, "File ended prematurely or read error at frame %0d", frame_num);
                    end

                    pixel_valid = 1;

                    do begin
                        @(posedge clk);
                    end while (!pixel_ready);
                end
            end

            $fclose(frame_fd);
        end

        if (metrics_received < NUM_STEPS) begin
            $display("[TB] Waiting for remaining %0d metrics...", NUM_STEPS - metrics_received);
            wait(metrics_received == NUM_STEPS);
        end

        $fclose(metrics_fd);

        $display("[TB] Simulation Finished");
        $finish;
    end


    always @(posedge clk) begin
        if (metrics_valid) begin
            $fdisplay(metrics_fd, "%d", metrics_data);
            ++metrics_received;
        end
    end

endmodule