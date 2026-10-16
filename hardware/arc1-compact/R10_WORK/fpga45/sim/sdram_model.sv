// ARC-1 R10 -- behavioural + protocol-checking model of a 4 x 8192 x 512 x 16 SDR SDRAM (AS4C16M16SA-class).
// SIMULATION ONLY, not vendor IP. Timing limits: the datasheet worst case of both speed grades (see the parameters).
// Checks (each breach prints MODEL_VIOLATION and increments `violations`):
//   init: no command but NOP/INHIBIT before T_INIT_NS; PRECHARGE ALL, >= INIT_REF AUTO REFRESH, MRS before ACTIVE;
//   ACT: bank idle, tRP after PRE, tRC after ACT (same bank), tRRD after any ACT, tRFC after REF;
//   READ/WRITE: bank active, row open, tRCD after ACT; PRE: tRAS after ACT, tWR after last WRITE;
//   REF: all banks idle, tRP, tRFC; refresh: no gap > MAX_REF_GAP_NS between AUTO REFRESH commands after init.
// Data: full 16M-word array; unwritten words read back as 16'hDEAD. BL = 1 only (as programmed).
`timescale 1ns/1ps
module sdram_model #(
    // DOCUMENTED worst case over the -6 and -7 grades: Alliance AS4C16M16SA-C&I Rev 3.0 (March 2015) Table 16
    // (tRCD/tRP 21, tRAS 42, tRC 63, tRRD 14, tWR 14, tRFC 63, tMRD 14 ns; tAC 5.4 ns at CL3 -7, tOH 2.5 ns; init
    // 200 us + >= 2 auto refresh). The controller uses 8 init refreshes, so INIT_REF stays a stricter 8 here.
    parameter real T_INIT_NS = 200000.0, parameter integer INIT_REF = 8,
    parameter real T_RCD = 21.0, T_RP = 21.0, T_RAS = 42.0, T_RC = 63.0, T_RRD = 14.0, T_WR = 14.0, T_RFC = 63.0,
    parameter real T_MRD = 14.0, T_AC = 5.4, T_OH = 2.5,
    parameter real MAX_REF_GAP_NS = 15600.0,      // 2 x tREFI: the controller must never postpone more than one
    // board + FPGA I/O: D_CLK = FPGA clock-out + clock trace, D_CMD = FPGA output + trace for command/address/DQ-out,
    // D_RET = DQ trace back + FPGA input path. Defaults 0 (ideal). Interface timing (datasheet): tIS 1.5, tIH 0.8 ns.
    parameter real D_CLK = 0.0, D_CMD = 0.0, D_RET = 0.0, T_IS = 1.5, T_IH = 0.8
) (
    input  wire        clk, cke, cs_n, ras_n, cas_n, we_n,
    input  wire [1:0]  ba,
    input  wire [12:0] a,
    input  wire [1:0]  dqm,
    inout  wire [15:0] dq
);
    integer violations = 0, n_ref = 0, n_act = 0, n_rd = 0, n_wr = 0, tviol = 0;   // tviol: setup/hold breaches
    // what the SDRAM pins see: everything from the FPGA delayed by the board/I/O paths
    wire clk_d;
    wire cke_d, cs_d, ras_d, cas_d, we_d;
    wire [1:0] ba_d, dqm_d;
    wire [12:0] a_d;
    wire [15:0] dq_d;
    assign #(D_CLK) clk_d = clk;
    assign #(D_CMD) {cke_d, cs_d, ras_d, cas_d, we_d, ba_d, dqm_d, a_d} = {cke, cs_n, ras_n, cas_n, we_n, ba, dqm, a};
    assign #(D_CMD) dq_d = dq;
    realtime t_in_chg = -1.0e9, t_dq_chg = -1.0e9;
    always @(cke_d or cs_d or ras_d or cas_d or we_d or ba_d or dqm_d or a_d) t_in_chg = $realtime;
    always @(dq_d) if (!dq_oe) t_dq_chg = $realtime;
    reg [15:0] mem [0:16777215];                  // X = never written
    reg        active [0:3];
    reg [12:0] row [0:3];
    realtime   t_act [0:3], t_pre [0:3], t_wr [0:3];
    realtime   t_any_act = -1.0e9, t_ref = -1.0e9, t_mrs = -1.0e9, t_last_ref = -1.0, max_gap = 0.0;
    integer    init_refs = 0, cl = 0;
    reg        pre_all_seen = 0, mrs_seen = 0;
    reg [15:0] dq_o; reg dq_oe = 1'b0;
    wire [15:0] dq_drv = dq_oe ? dq_o : 16'hzzzz;
    assign #(D_RET) dq = dq_drv;                       // the FPGA pad sees the SDRAM output D_RET later
    genvar gi;
    generate for (gi = 0; gi < 16; gi = gi + 1) begin : g_keep
        pullup (weak1) pu (dq[gi]);                    // undriven bus reads 1s (deterministic, not z/X)
    end endgenerate
    integer k;
    initial for (k = 0; k < 4; k = k + 1) begin active[k] = 0; t_act[k] = -1.0e9; t_pre[k] = -1.0e9; t_wr[k] = -1.0e9; end
    task automatic viol(input [8*64-1:0] m);
        begin violations = violations + 1; $display("MODEL_VIOLATION t=%0t %0s", $time, m); end
    endtask
    // read pipeline: data for a READ sampled at edge k is driven from edge k+CL + tAC until edge k+CL+1 + tOH
    reg [15:0] rq_d [0:7]; reg [7:0] rq_v = 8'd0;
    always @(posedge clk_d) begin : cmdproc
        reg [3:0] c;
        reg [23:0] wa;
        reg [1:0] s_ba, s_dqm;
        reg [12:0] s_a;
        reg [15:0] s_dq;
        reg s_cke, s_cs;
        realtime te;
        reg ok;
        te = $realtime;
        c = {cs_d, ras_d, cas_d, we_d}; s_cke = cke_d; s_cs = cs_d; s_ba = ba_d; s_dqm = dqm_d; s_a = a_d; s_dq = dq_d;
        // advance the read pipeline (index 0 = due now): old data held until tOH, unknown until tAC, then the new word
        if (rq_v[0]) begin
            dq_o <= #(T_OH) $random; dq_o <= #(T_AC) rq_d[0]; dq_oe <= #(T_AC) 1'b1;   /* garbage, not X: RTL compares must see it */
        end else dq_oe <= #(T_OH) 1'b0;
        for (k = 0; k < 7; k = k + 1) begin rq_d[k] = rq_d[k + 1]; end
        rq_v = {1'b0, rq_v[7:1]};
        // setup (before the edge) and hold (after it): a breached command is decoded as garbage (ignored)
        ok = (te - t_in_chg >= T_IS) && (!(c == 4'b0100) || te - t_dq_chg >= T_IS);
        #(T_IH);
        ok = ok && (t_in_chg <= te) && (!(c == 4'b0100) || t_dq_chg <= te);
        if (!ok && s_cke && !s_cs && c != 4'b0111) begin tviol = tviol + 1; c = 4'b0111; end
        if (s_cke && !s_cs) begin
            if ($realtime < T_INIT_NS && c != 4'b0111) viol("command before the init wait");
            case (c)
            4'b0011: begin                                   // ACTIVE
                n_act = n_act + 1;
                if (!mrs_seen) viol("ACTIVE before MRS");
                if (active[s_ba]) viol("ACTIVE to an active bank");
                if ($realtime - t_pre[s_ba] < T_RP - 0.01) viol("tRP");
                if ($realtime - t_act[s_ba] < T_RC - 0.01) viol("tRC");
                if ($realtime - t_any_act < T_RRD - 0.01) viol("tRRD");
                if ($realtime - t_ref < T_RFC - 0.01) viol("tRFC before ACTIVE");
                if ($realtime - t_mrs < T_MRD - 0.01) viol("tMRD");
                active[s_ba] = 1; row[s_ba] = s_a; t_act[s_ba] = $realtime; t_any_act = $realtime;
            end
            4'b0101, 4'b0100: begin                          // READ / WRITE
                if (!active[s_ba]) viol("READ/WRITE to an idle bank");
                if ($realtime - t_act[s_ba] < T_RCD - 0.01) viol("tRCD");
                if (s_a[10]) viol("auto precharge not expected");
                wa = {s_ba, row[s_ba], s_a[8:0]};
                if (c == 4'b0100) begin
                    n_wr = n_wr + 1;
                    if (s_dqm == 2'b00) mem[wa] = s_dq;
                    else begin
                        if (!s_dqm[0]) mem[wa][7:0] = s_dq[7:0];
                        if (!s_dqm[1]) mem[wa][15:8] = s_dq[15:8];
                    end
                    if (^s_dq === 1'bx && s_dqm != 2'b11) viol("WRITE with undriven/X data");
                    t_wr[s_ba] = $realtime;
                end else begin
                    n_rd = n_rd + 1;
                    if (cl < 2 || cl > 3) viol("READ with CL not programmed");
                    else begin rq_d[cl - 1] = (^mem[wa] === 1'bx) ? 16'hDEAD : mem[wa]; rq_v[cl - 1] = 1'b1; end
                end
            end
            4'b0010: begin                                   // PRECHARGE (A10 = all)
                for (k = 0; k < 4; k = k + 1) if (s_a[10] || k == s_ba) begin
                    if (active[k] && $realtime - t_act[k] < T_RAS - 0.01) viol("tRAS");
                    if (active[k] && $realtime - t_wr[k] < T_WR - 0.01) viol("tWR");
                    active[k] = 0; t_pre[k] = $realtime;
                end
                if (s_a[10]) pre_all_seen = 1;
            end
            4'b0001: begin                                   // AUTO REFRESH
                n_ref = n_ref + 1;
                for (k = 0; k < 4; k = k + 1) begin
                    if (active[k]) viol("REFRESH with an active bank");
                    if ($realtime - t_pre[k] < T_RP - 0.01) viol("tRP before REFRESH");
                end
                if ($realtime - t_ref < T_RFC - 0.01) viol("tRFC");
                if (!pre_all_seen) viol("REFRESH before PRECHARGE ALL");
                if (!mrs_seen) init_refs = init_refs + 1;
                if (mrs_seen && t_last_ref >= 0.0 && $realtime - t_last_ref > max_gap) max_gap = $realtime - t_last_ref;
                t_ref = $realtime; if (mrs_seen) t_last_ref = $realtime;
            end
            4'b0000: begin                                   // LOAD MODE REGISTER
                for (k = 0; k < 4; k = k + 1) if (active[k]) viol("MRS with an active bank");
                if (init_refs < INIT_REF) viol("MRS before the init refreshes");
                if (s_a[2:0] != 3'b000) viol("burst length != 1");
                cl = s_a[6:4]; mrs_seen = 1; t_mrs = $realtime; t_last_ref = $realtime;
                if (cl != 2 && cl != 3) viol("CAS latency not 2/3");
            end
            default: ;
            endcase
        end
        if (mrs_seen && $realtime - t_last_ref > MAX_REF_GAP_NS) begin
            viol("refresh gap"); t_last_ref = $realtime;
        end
    end
endmodule
