`timescale 1ns/1ps
`default_nettype none
module transform_tb;
    reg clk = 0;
    always #5 clk = ~clk;
    reg reset = 1, in_valid = 0, out_ready = 0;
    wire in_ready, out_valid;
    reg signed [31:0] in_xmin, in_ymin, in_xmax, in_ymax;
    reg signed [31:0] in_m00, in_m01, in_m02, in_m10, in_m11, in_m12;
    reg [15:0] in_viewport_width, in_viewport_height;
    reg [31:0] in_tag;
    wire signed [31:0] out_minx, out_miny, out_maxx, out_maxy;
    wire [2:0] out_flags;
    wire [31:0] out_tag;
    arc1_transform dut (.*);

    localparam MAX_VECTORS = 4096;
    reg [31:0] words [0:18*MAX_VECTORS-1];
    integer queue [0:MAX_VECTORS-1];
    integer n = 0, fd, status, j, qread = 0, qwrite = 0;
    integer accepted = 0, completed = 0, cycles = 0;
    integer input_stalls = 0, output_stalls = 0, simultaneous = 0;
    integer sent, watchdog = 0;
    reg prior_input_stall = 0, prior_output_stall = 0;
    reg [383:0] prior_input;
    reg [162:0] prior_output;
    wire [383:0] input_payload = {in_xmin, in_ymin, in_xmax, in_ymax,
        in_m00, in_m01, in_m02, in_m10, in_m11, in_m12,
        in_viewport_width, in_viewport_height, in_tag};
    wire [162:0] output_payload = {out_tag, out_minx, out_miny, out_maxx, out_maxy, out_flags};
    reg last_accept;
    reg [31:0] random_state = 32'h3a71c05f;
    reg [31:0] scanned_word;
    string vector_path;

    task automatic load_job(input integer index);
        integer base;
        begin
            base = index * 18;
            in_xmin = words[base]; in_ymin = words[base+1];
            in_xmax = words[base+2]; in_ymax = words[base+3];
            in_m00 = words[base+4]; in_m01 = words[base+5]; in_m02 = words[base+6];
            in_m10 = words[base+7]; in_m11 = words[base+8]; in_m12 = words[base+9];
            in_viewport_width = words[base+10][15:0];
            in_viewport_height = words[base+11][15:0];
            in_tag = words[base+12];
        end
    endtask

    // Observe before NBA updates: a transfer occurs only at valid && ready.
    always @(posedge clk) begin
        if (reset) begin
            qread = 0; qwrite = 0; accepted = 0; completed = 0; cycles = 0;
            input_stalls = 0; output_stalls = 0; simultaneous = 0;
            prior_input_stall = 0; prior_output_stall = 0;
        end else begin
            cycles = cycles + 1;
            if (prior_input_stall && (!in_valid || input_payload !== prior_input))
                $fatal(1, "Driver violated input hold contract");
            if (prior_output_stall && (!out_valid || output_payload !== prior_output))
                $fatal(1, "DUT changed a stalled output");
            if (in_valid && !in_ready) input_stalls = input_stalls + 1;
            if (out_valid && !out_ready) output_stalls = output_stalls + 1;
            if (in_valid && in_ready && out_valid && out_ready) simultaneous = simultaneous + 1;
            if (in_valid && in_ready) begin
                if (in_tag >= n || qwrite >= MAX_VECTORS) $fatal(1, "Bad test input tag/queue");
                queue[qwrite] = in_tag;
                qwrite = qwrite + 1;
                accepted = accepted + 1;
            end
            if (out_valid && out_ready) begin
                if (qread >= qwrite) $fatal(1, "Unexpected/duplicate result");
                j = queue[qread] * 18;
                if (out_tag !== words[j+12] || out_minx !== words[j+13] ||
                    out_miny !== words[j+14] || out_maxx !== words[j+15] ||
                    out_maxy !== words[j+16] || {29'b0, out_flags} !== words[j+17]) begin
                    $display("Result tag=%0d got %h %h %h %h flags=%h", out_tag,
                        out_minx, out_miny, out_maxx, out_maxy, out_flags);
                    $display("Expected tag=%0d %h %h %h %h flags=%h", words[j+12],
                        words[j+13], words[j+14], words[j+15], words[j+16], words[j+17]);
                    $fatal(1, "Arithmetic/order comparison failed");
                end
                qread = qread + 1;
                completed = completed + 1;
            end
            prior_input_stall = in_valid && !in_ready;
            prior_output_stall = out_valid && !out_ready;
            prior_input = input_payload;
            prior_output = output_payload;
        end
    end

    task automatic assert_no_ghost;
        integer i;
        begin
            for (i = 0; i < 12; i = i + 1) begin
                @(posedge clk); #1;
                if (out_valid) $fatal(1, "Result leaked across reset");
            end
        end
    endtask

    initial begin
        if (!$value$plusargs("VECTORS=%s", vector_path)) vector_path = "build/vectors.hex";
        fd = $fopen(vector_path, "r");
        if (!fd) $fatal(1, "Cannot open vectors");
        status = $fscanf(fd, "%h", scanned_word);
        while (status == 1) begin
            if (n >= MAX_VECTORS) $fatal(1, "Too many vectors");
            words[n*18] = scanned_word;
            for (j = 1; j < 18; j = j + 1) begin
                status = $fscanf(fd, "%h", scanned_word);
                if (status != 1) $fatal(1, "Truncated vector");
                words[n*18+j] = scanned_word;
            end
            n = n + 1;
            if (n < MAX_VECTORS) status = $fscanf(fd, "%h", scanned_word);
            else status = -1;
        end
        $fclose(fd);
        if (!n) $fatal(1, "No vectors");
        load_job(0);
        repeat (2) @(posedge clk);
        @(negedge clk); reset = 0; in_valid = 1;
        @(posedge clk);
        if (!in_ready) $fatal(1, "Not ready after reset");
        @(negedge clk); in_valid = 0;
        repeat (3) @(posedge clk);
        @(negedge clk); reset = 1;
        @(posedge clk); #1;
        if (out_valid) $fatal(1, "Busy reset did not cancel result");
        @(negedge clk); reset = 0;
        assert_no_ghost();

        // Reset an already completed but backpressured result.
        @(negedge clk); load_job(0); in_valid = 1;
        @(posedge clk);
        if (!in_ready) $fatal(1, "Cannot accept held-result reset test");
        @(negedge clk); in_valid = 0;
        wait (out_valid);
        repeat (4) @(posedge clk);
        @(negedge clk); reset = 1;
        @(posedge clk); #1;
        if (out_valid) $fatal(1, "Held result survived reset");
        @(negedge clk); reset = 0;
        assert_no_ghost();

        // Reproducible random input gaps and output stalls, with queued scoreboard.
        sent = 0;
        last_accept = 0;
        while (completed < n) begin
            @(negedge clk);
            random_state = {random_state[30:0], random_state[31] ^ random_state[21] ^ random_state[1] ^ random_state[0]};
            out_ready = (watchdog % 37 >= 9) && random_state[0];
            if (last_accept) begin sent = sent + 1; in_valid = 0; end
            if (!in_valid && sent < n && (random_state[1] || random_state[2])) begin
                load_job(sent);
                in_valid = 1;
            end
            @(posedge clk);
            last_accept = in_valid && in_ready;
            watchdog = watchdog + 1;
            if (watchdog > 100000) $fatal(1, "Watchdog expired");
            #1;
        end
        @(negedge clk); in_valid = 0; out_ready = 1;
        repeat (12) @(posedge clk);
        #1;
        if (accepted != n || completed != n || qread != qwrite || out_valid)
            $fatal(1, "Dropped, repeated or unconsumed transaction");
        if (!input_stalls || !output_stalls || !simultaneous)
            $fatal(1, "Handshake coverage missing");
        $display("PASS RTL: %0d oracle comparisons; busy/held-output reset cancellation; input stalls=%0d output stalls=%0d simultaneous retire/accept=%0d cycles=%0d",
            completed, input_stalls, output_stalls, simultaneous, cycles);
        $finish;
    end
endmodule
`default_nettype wire
