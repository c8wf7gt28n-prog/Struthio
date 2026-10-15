// ARC-1 Compact R08 -- PSRAM power guard (new in R08; R06 controller RTL unchanged).
//
// Evidence level: RTL_SIMULATED only (tb/tb_psram_r08.sv). Not NATIVE_EDA_VERIFIED,
// not PROTOTYPE_MEASURED.
//
// Board context (R08 board plan, docs/PSRAM_POWER_R08.md):
//   * PSRAM VDD comes from a load switch (PSRAM_VDD). Its EN is
//     F133 PSRAM_PWR_REQ AND T35 CDONE, so the PSRAM is never powered while the
//     T35 is unconfigured (weak pull-ups active).
//   * A voltage supervisor on PSRAM_VDD drives PSRAM_PG (open drain, low = bad).
//     Its reset-timeout keeps PG low for the timeout after VDD returns, so every
//     dip produces a long low pulse.
//   * CE# has its pull-up to PSRAM_VDD (tracks the ramp). Pull-downs on CE#,
//     SCLK and SIO[3:0] are switched in only while CDONE is low (open-drain
//     buffer), plus 100 kOhm static pull-downs on SCLK/SIO.
//
// Function (mclk domain):
//   OFF  (PG low, or PG high for fewer than PG_STABLE cycles):
//        controller held in reset (mrst); CE# pad NOT driven (pull-up to the
//        switched rail tracks VDD, and nothing back-powers the unpowered PSRAM);
//        SCLK and SIO[3:0] driven LOW. So during the VDD ramp: CE# = VDD,
//        CLK low, SIO low, as APS6404L DS Rev 2.7 section 8 requires.
//   ON   controller released; it runs its own tPU (150 us) counter, then
//        RSTEN/RST, Read ID, QPI entry. Pads follow the controller.
//   Any PG low sample in ON -> OFF immediately; the in-flight user request ends
//        with CORE_FAULT (user-port memory-side reset semantics, R06), and
//        `power_lost` is raised for the system domain.
//   PG is synchronised (2 FF). OFF is held for at least PG_STABLE cycles, so a
//   glitch of any length is stretched to a full re-initialisation (fail-safe).
module psram_power_guard #(
    parameter integer PG_STABLE = 64     // mclk cycles of continuous PG high before ON
) (
    input  wire       mclk,
    input  wire       rst,               // system reset in the mclk domain
    input  wire       pg_raw,            // PSRAM_PG pad (asynchronous)
    output reg        on,                // registered: power guard released the controller
    output wire       core_rst,          // to psram_user_port.mrst (OR with system reset inside)
    // controller side
    input  wire       c_ce_n,
    input  wire       c_sclk,
    input  wire [3:0] c_dq_o,
    input  wire [3:0] c_dq_oe,
    // pad side
    output wire       p_ce_n_o,
    output wire       p_ce_n_oe,
    output wire       p_sclk_o,
    output wire [3:0] p_dq_o,
    output wire [3:0] p_dq_oe
);
    localparam integer CW = (PG_STABLE < 2) ? 1 : $clog2(PG_STABLE + 1);
    reg pg_s1 = 1'b0, pg_s2 = 1'b0;
    always @(posedge mclk) begin
        pg_s1 <= pg_raw;
        pg_s2 <= pg_s1;
    end

    reg [CW-1:0] stable_cnt;
    always @(posedge mclk) begin
        if (rst || !pg_s2) begin
            on         <= 1'b0;
            stable_cnt <= {CW{1'b0}};
        end else if (!on) begin
            if (stable_cnt == PG_STABLE[CW-1:0]) on <= 1'b1;
            else stable_cnt <= stable_cnt + {{(CW-1){1'b0}}, 1'b1};
        end
    end
    // `on` drops in the same cycle as the synchronised PG; pads are combinational
    // on `on` so they go safe at that clock edge.
    assign core_rst  = rst | ~on;
    assign p_ce_n_o  = on ? c_ce_n   : 1'b1;
    assign p_ce_n_oe = on;                       // OFF: released to the switched-rail pull-up
    assign p_sclk_o  = on ? c_sclk   : 1'b0;
    assign p_dq_o    = on ? c_dq_o   : 4'b0000;
    assign p_dq_oe   = on ? c_dq_oe  : 4'b1111;  // OFF: drive low (no back-power, SIO low during tPU)
endmodule
