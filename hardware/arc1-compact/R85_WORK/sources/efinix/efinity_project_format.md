# Efinity project, Interface Designer and SDC formats for a Trion T35F400C3

Every fact below comes from a downloaded source listed in `sources.json`. Source IDs are given in [brackets]. **NOT_FOUND** means none of the retrieved sources states the fact. **DERIVED** marks an inference of mine and says what it rests on.

Two public example projects were used:

* **[GH_T35]** `s100projects/ROMWBW_T35` at commit `556f5961c128902d62b195785fe608eec481a0e8`, folder `T35SBCextSD_16/`. This is a third-party project, not an Efinix one. It is a real **T35F400** Trion project saved by Efinity `2024.1.163.1.8`, with `last_run_state="pass"` and `last_run_flow="bitstream"`.
  * https://github.com/s100projects/ROMWBW_T35/blob/556f5961c128902d62b195785fe608eec481a0e8/T35SBCextSD_16/T35SBCextSD_16.xml
  * https://github.com/s100projects/ROMWBW_T35/blob/556f5961c128902d62b195785fe608eec481a0e8/T35SBCextSD_16/T35SBCextSD_16.peri.xml
  * https://github.com/s100projects/ROMWBW_T35/blob/556f5961c128902d62b195785fe608eec481a0e8/T35SBCextSD_16/T35SBCextSD_16_io.isf
  * https://github.com/s100projects/ROMWBW_T35/blob/556f5961c128902d62b195785fe608eec481a0e8/T35SBCextSD_16/T35SBCextSD_16.pt.sdc
* **[GH_XY]** `Efinix-Inc/xyloni` at commit `d28734fb099898a18e8d1fddfd08eb713840a878` (Efinix's own repository). It is a T8F81 Trion project saved by Efinity 2020.1.140, and it confirms the same `efx:project` schema.
  * https://github.com/Efinix-Inc/xyloni/blob/d28734fb099898a18e8d1fddfd08eb713840a878/design/helloworld/efinity/xyloni.xml

## 1. Project file `<name>.xml` (root `efx:project`)

### 1.1 Structure

The element order and names below follow [GH_T35] verbatim. The synthesis and place-and-route parameter lists are cut down to the entries that appear in **both** [GH_T35] and [GH_XY]. A newer Efinity rewrites the full list when it saves the project.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<efx:project name="arc1_t35" description="" sw_version="2024.1.163.1.8"
    xmlns:efx="http://www.efinixinc.com/enf_proj"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.efinixinc.com/enf_proj enf_proj.xsd">
    <efx:device_info>
        <efx:family name="Trion"/>
        <efx:device name="T35F400"/>
        <efx:timing_model name="C3"/>          <!-- [GH_T35] uses "C4" -->
    </efx:device_info>
    <efx:design_info def_veri_version="verilog_2k" def_vhdl_version="vhdl_2008">
        <efx:top_module name="arc1_t35_top"/>
        <efx:design_file name="../top/arc1_t35_top.sv" version="default" library="default"/>
        <!-- one efx:design_file per RTL file -->
        <efx:top_vhdl_arch name=""/>
    </efx:design_info>
    <efx:constraint_info>
        <efx:sdc_file name="arc1_t35.sdc"/>
        <efx:inter_file name=""/>
    </efx:constraint_info>
    <efx:sim_info/>
    <efx:misc_info/>
    <efx:ip_info/>
    <efx:synthesis tool_name="efx_map">
        <efx:param name="work_dir" value="work_syn" value_type="e_string"/>
        <efx:param name="write_efx_verilog" value="on" value_type="e_bool"/>
        <efx:param name="mode" value="speed" value_type="e_option"/>
        <efx:param name="max_ram" value="-1" value_type="e_integer"/>
        <efx:param name="max_mult" value="-1" value_type="e_integer"/>
        <efx:param name="infer-clk-enable" value="3" value_type="e_option"/>
        <efx:param name="infer-sync-set-reset" value="1" value_type="e_option"/>
        <efx:param name="fanout-limit" value="0" value_type="e_integer"/>
    </efx:synthesis>
    <efx:place_and_route tool_name="efx_pnr">
        <efx:param name="work_dir" value="work_pnr" value_type="e_string"/>
        <efx:param name="verbose" value="off" value_type="e_bool"/>
        <efx:param name="load_delaym" value="on" value_type="e_bool"/>
        <efx:param name="optimization_level" value="NULL" value_type="e_option"/>
        <efx:param name="seed" value="1" value_type="e_integer"/>
    </efx:place_and_route>
    <efx:bitstream_generation tool_name="efx_pgm">
        <efx:param name="mode" value="active" value_type="e_option"/>
        <efx:param name="width" value="1" value_type="e_option"/>          <!-- [GH_T35]: 4 -->
        <efx:param name="enable_roms" value="smart" value_type="e_option"/>
        <efx:param name="spi_low_power_mode" value="on" value_type="e_bool"/>
        <efx:param name="io_weak_pullup" value="on" value_type="e_bool"/>
        <efx:param name="oscillator_clock_divider" value="DIV8" value_type="e_option"/>
        <efx:param name="jtag_usercode" value="0xFFFFFFFF" value_type="e_string"/>
        <efx:param name="release_tri_then_reset" value="on" value_type="e_bool"/>
        <efx:param name="four_byte_addressing" value="off" value_type="e_bool"/>
        <efx:param name="generate_bit" value="on" value_type="e_bool"/>
        <efx:param name="generate_hex" value="on" value_type="e_bool"/>
        <efx:param name="cold_boot" value="off" value_type="e_bool"/>
        <efx:param name="cascade" value="off" value_type="e_option"/>
    </efx:bitstream_generation>
    <efx:debugger>
        <efx:param name="work_dir" value="work_dbg" value_type="e_string"/>
        <efx:param name="auto_instantiation" value="off" value_type="e_bool"/>
        <efx:param name="profile" value="NONE" value_type="e_string"/>
    </efx:debugger>
</efx:project>
```

### 1.2 Notes on the example

* **Device name:** both public projects write the device without a speed grade: `T35F400` [GH_T35] and `T8F81` [GH_XY]. The speed grade goes in `timing_model`.
  * The Python API `create()` says `device_name` is the "Name and package for the target FPGA … For example, T20F256. This must be the same name you specified for the project in the Efinity Project Editor" [PYAPI "API Functions: Interface Designer", create()].
  * **DERIVED:** use `T35F400` with `timing_model name="C3"`, not `T35F400C3`. The API example sets `prj_conf.device.timing_model = 'C3'` [PYAPI p.18], which supports "C3" as a valid timing-model value.
* **Design file paths:** [GH_T35] lists files relative to the project directory. Paths the Integrated Python API writes are relative to the project directory, for example `<efx:design_file library="" name="helloworld/helloworld_new.v" version=""/>` [PYAPI p.18].
* **Project-file API:** Efinity 2026.1 adds a "Preliminary" Integrated Python API, run with `efx_py`. It is used as `from Efx.Project import Configuration as PrjConf; conf = PrjConf.New(name, dir)`, then `conf.device.family/device/timing_model`, `conf.design.top_module`, `conf.design.AddRTLFile()`, `conf.constraint.AddTimingConstraintFile()` and `conf.Save()` [PYAPI pp.16-19].
  * It is incompatible with external Python 3.
  * It has "no project validation support"; Efinix recommends "an existing project XML file as a starting point" [PYAPI p.18].

### 1.3 Bitstream parameters

These are documented as `efx_pgm` options [CLI Table 39] and as Project Editor options [SWUG Table 39]:

| Parameter | Meaning |
|---|---|
| `oscillator_clock_divider` | DIV8, DIV4, DIV2 or DIV1 (CLI). AN006 Table 10 lists only DIV4 = 20 MHz and DIV8 = 10 MHz for Trion. Default DIV8. |
| `io_weak_pullup` | "Enable IO weak pullup during configuration." |
| `release_tri_then_reset` | "Release IO tri-states before reset upon entering user mode." Default On. |
| `spi_low_power_mode` | "Power down flash devices after programming." |
| `four_byte_addressing` | Titanium/Topaz only. Trion supports only 3-byte addressing [AN006 p.12]. |
| `enable_roms` | on, off or smart. For Trion, smart has the same effect as on. |
| `width` | 1, 2, 4, 8, 16 or 32 |
| `mode` | active or passive |

## 2. Interface Designer file `<name>.peri.xml` (root `efxpt:design_db`)

### 2.1 Structure

This is a cut-down excerpt of [GH_T35] `T35SBCextSD_16.peri.xml`. It is a T35F400 file; only the element and attribute names are kept verbatim. The file is normally written by the Interface Designer or by `DesignAPI.save()`. It is not meant to be edited by hand.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<efxpt:design_db name="T35SBCextSD_16" device_def="T35F400" version="2024.1.163.1.8" db_version="20241999"
  xmlns:efxpt="http://www.efinixinc.com/peri_design_db" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.efinixinc.com/peri_design_db peri_design_db.xsd ">
  <efxpt:device_info>
    <efxpt:iobank_info>
      <efxpt:iobank name="1A" iostd="3.3 V LVTTL / LVCMOS"/>
      ... 1B 1C 1D 1E 2A 2B 2C 3C_TR 4A 4B (all 3.3 V) ...
      <efxpt:iobank name="BL" iostd="1.2 V"/>
      <efxpt:iobank name="BR" iostd="3.3 V LVTTL / LVCMOS"/>
    </efxpt:iobank_info>
    <efxpt:ctrl_info> <efxpt:ctrl name="cfg" ctrl_def="CONFIG_CTRL0" .../> </efxpt:ctrl_info>
  </efxpt:device_info>
  <efxpt:gpio_info device_def="T35F400">
    <efxpt:gpio name="vgaRed" gpio_def="GPIOL_56" mode="output" bus_name="" is_lvds_gpio="false" io_standard="3.3 V LVTTL / LVCMOS">
      <efxpt:output_config name="vgaRed" name_ddio_lo="" register_option="none" clock_name="" is_clock_inverted="false"
                           is_slew_rate="false" tied_option="none" ddio_type="none" drive_strength="3"/>
    </efxpt:gpio>
    <efxpt:gpio name="biData[0]" gpio_def="GPIOL_20" mode="inout" bus_name="biData" is_lvds_gpio="false" io_standard="3.3 V LVTTL / LVCMOS">
      <efxpt:input_config name="biData_IN[0]" name_ddio_lo="" conn_type="normal" is_register="false" clock_name=""
                          is_clock_inverted="false" pull_option="weak pullup" is_schmitt_trigger="false" ddio_type="none"/>
      <efxpt:output_config name="biData_OUT[0]" ... drive_strength="2"/>
      <efxpt:output_enable_config name="biData_OE[0]" is_register="false" clock_name="" is_clock_inverted="false"/>
    </efxpt:gpio>
    <efxpt:gpio name="clockIn" gpio_def="GPIOR_138" mode="input" bus_name="" is_lvds_gpio="false" io_standard="3.3 V LVTTL / LVCMOS">
      <efxpt:input_config name="clockIn" name_ddio_lo="" conn_type="pll_clkin" is_register="false" ... pull_option="none" .../>
    </efxpt:gpio>
    <efxpt:global_unused_config state="input with weak pullup"/>
    <efxpt:bus name="biData" mode="inout" msb="7" lsb="0"/>
  </efxpt:gpio_info>
  <efxpt:pll_info>
    <efxpt:pll name="pll_inst1" pll_def="PLL_BR0" ref_clock_name="" ref_clock_freq="50.0000" multiplier="20" pre_divider="1"
               post_divider="4" reset_name="" locked_name="pll0_LOCKED" is_ipfrz="false" is_bypass_lock="true">
      <efxpt:output_clock name="pll0_50MHz" number="0" out_divider="5" adv_out_phase_shift="0"/>
      <efxpt:adv_prop ref_clock_mode="external" ref_clock1_name="" ext_ref_clock_id="2" clksel_name=""
                      feedback_clock_name="" feedback_mode="internal"/>
    </efxpt:pll>
  </efxpt:pll_info>
  <efxpt:lvds_info/> <efxpt:jtag_info/> <efxpt:ddr_info/>
</efxpt:design_db>
```

### 2.2 Notes on the example

* In the .peri.xml file, `gpio_def` holds the **GPIO resource name** (`GPIOL_20`), not the ball.
* In the ISF, `assign_pkg_pin` takes the **ball**. In [GH_T35], `assign_pkg_pin("biData[0]","N15")` maps to GPIOL_20, and the local package CSV gives GPIOL_20_CDI5 at ball N15. `clockIn` is assigned to `"T8"`, which is GPIOR_138_PLLIN0 at ball T8.
* An inout GPIO produces three core ports: `<name>_IN`, `<name>_OUT` and `<name>_OE`. These are the names to use in RTL and SDC [GH_T35]. The Trion Interfaces UG states: "Setting the output enable signal to high ("1") in your RTL design enables the output buffer" [TINTF p.53].

## 3. Interface Scripting File (.isf) and the `DesignAPI` Python API

Source: Efinity Python API UG v8.7, May 2026 [PYAPI].

* The .isf "contains all of the Python API commands to re-create your interface". It can be exported and imported from the GUI with Import GPIO / Export GPIO, choosing "Interface Scripting File (.isf)" [PYAPI p.6].
* An .isf file is a sequence of `design.<call>` lines with no imports. [GH_T35] `T35SBCextSD_16_io.isf` begins with the header `# Device: T35F400`, `# Package: 400-ball FBGA (final)`, `# Configuration mode: active (x4)` and `# Timing Model: C4 (final)`.

### 3.1 Script boilerplate

This is verbatim from `build_ptdemo.py` [PYAPI p.12]. Run it after `source bin/setup.sh` with `python3 my_script.py` (Linux). On Windows use `efx_run_pt_script.bat my_script.py` [PYAPI p.13].

```python
import os, sys
pt_home = os.environ['EFXPT_HOME']
sys.path.append(pt_home + "/bin")
from api_service.design import DesignAPI
from api_service.device import DeviceAPI
import api_service.excp.design_excp as APIExcp
design = DesignAPI(is_verbose)        # e.g. DesignAPI(True)
design.create(project_name, device_name, output_dir)
...
design.generate(enable_bitstream=False)
design.save()
```

### 3.2 Signatures

These are copied from the "Usage" rows [PYAPI pp.25-44].

| Call | Notes from the guide |
|---|---|
| `create(design_name, device_name, path, auto_save, overwrite)` | `device_name` is e.g. "T20F256", matching the Project Editor. Call `save()` afterwards. |
| `load(design_file)` | Loads a `.peri.xml` file. |
| `save()` | Saves to the file given in `create()`. |
| `create_input_gpio(name, msb, lsb)` | msb/lsb default None; give them to create a bus. |
| `create_output_gpio(name, msb, lsb)` | |
| `create_inout_gpio(name, msb, lsb)` | |
| `create_open_drain_output_gpio(name)` | "inout GPIO in open drain output configuration; the output is grounded. Constant output is set to 0 (GND)." |
| `create_input_clock_gpio(name)` | Connection type **GCLK**. |
| `create_pll_input_clock_gpio(name)` | Connection type **PLL_CLKIN**. |
| `create_global_control_gpio(name)` | Connection type GCTRL. |
| `create_clockout_gpio(name)` | Used in the example ISF. |
| `create_unused_gpio(name)` | |
| `create_block(name, block_type, **kwargs)` | For example `create_block("pll_inst1","PLL")` [GH_T35]. Not for GPIO. |
| `set_property(inst, prop_name, prop_value, block_type)` | `block_type` defaults to GPIO. "Do not use set_property() for resources or pins, instead use assign_resource() and assign_pkg_pin()". |
| `assign_pkg_pin(inst, pin_name)` | `pin_name` is the package ball, e.g. "K19". |
| `assign_resource(inst, res_name, block_type)` | For example `assign_resource("pll_inst1","PLL_BR0","PLL")` [GH_T35]. |
| `set_iobank_voltage(bank_name, voltage)` | Voltage as a string. |
| `set_device_property(inst, prop_name, prop_value, devset_type)` | [GH_T35] uses `design.set_device_property("1C","VOLTAGE","3.3","IOBANK")`. |
| `get_all_iobank_name()` | |
| `check_design()` | Returns True or False. |
| `generate(enable_bitstream, outdir)` | Runs design checks and writes constraints and reports. |
| `auto_calc_pll_clock(inst, target_freq=None, apply_optimal=True, result_len)` | `target_freq` is a map such as `CLKOUTn_FREQ`. |
| `calc_pll_clock(inst)` | |

### 3.3 GPIO properties valid for Trion

The Trion column was checked on the rendered PDF pages 71-75 [PYAPI Tables 57, 58, 60, 61].

* **Input:**
  * `IN_PIN`, `IN_HI_PIN`, `IN_LO_PIN`, `IN_CLK_PIN`, `IS_INCLK_INVERTED`
  * `IN_REG`: `BYPASS`, `REG`, `DDIO` or `DDIO_RESYNC`
* **Output:**
  * `OUT_PIN`, `OUT_HI_PIN`, `OUT_LO_PIN`, `OUT_CLK_PIN`, `IS_OUTCLK_INVERTED`
  * `OUT_REG`: `BYPASS`, `REG`, `INVREG`, `DDIO` or `DDIO_RESYNC`
  * `OE_PIN`
  * `OE_REG`: `BYPASS` or `REG`
  * `OEN_PIN` is **not** available on Trion.
* **Set at creation:**
  * `CONN_TYPE`: `GCLK`, `GCTRL`, `PLL_CLKIN` or `MIPI_CLKIN`
  * `MODE`: `INPUT`, `OUTPUT`, `INOUT`, `CLKOUT` or `NONE`
* **Changeable:**

| Property | Trion values |
|---|---|
| `IO_STANDARD` | `3.3_V_LVTTL_/_LVCMOS`, `2.5_V_LVCMOS`, `1.8_V_LVCMOS` |
| `PULL_OPTION` | `NONE`, `WEAK_PULLUP`, `WEAK_PULLDOWN` (the `DYNAMIC` value is not available on Trion) |
| `DRIVE_STRENGTH` | `1`, `2`, `3`, `4` |
| `SLEW_RATE` | `0`, `1` |
| `SCHMITT_TRIGGER` | `0`, `1` |
| `CONST_OUTPUT` | `NONE`, `0`, `1` |
| `RESOURCE` | resource name |
| `UNUSED_STATE` | `INPUT_WITH_WEAK_PULLUP`, `INPUT_WITH_WEAK_PULLDOWN` |

* `BUS_HOLD` is not available on Trion.
* The I/O bank device setting `IOBANK` has the properties `NAME` and `VOLTAGE` on Trion. `DYNAMIC_VOLTAGE` and `MODE_SEL_PIN` are not available on Trion [PYAPI Table 63].
* For the drive-strength currents, see the T35 data sheet Table 68. At 3.3 V, the IOH/IOL figures are: DS1 14.4/8.0 mA, DS2 19.1/10.5 mA, DS3 23.9/13.3 mA, DS4 28.7/15.8 mA.
* The weak pull-up is 27/40/65 kΩ (min/typ/max) at 3.3 V [DS Table 69].

### 3.4 PLL via ISF

These calls are verbatim from [GH_T35]. Trion uses PLL_V2, the "Advanced PLL", on T35 [PYAPI Table 113; TINTF interface table].

```python
design.create_block("pll_inst1","PLL")
design.set_property("pll_inst1","REFCLK_SOURCE","EXTERNAL","PLL")
design.set_property("pll_inst1","EXT_CLK","EXT_CLK0","PLL")
design.set_property("pll_inst1","REFCLK_FREQ","50.0","PLL")
design.set_property("pll_inst1","M","20","PLL"); design.set_property("pll_inst1","N","1","PLL"); design.set_property("pll_inst1","O","4","PLL")
design.set_property("pll_inst1","CLKOUT0_EN","1","PLL"); design.set_property("pll_inst1","CLKOUT0_DIV","10","PLL")
design.set_property("pll_inst1","CLKOUT0_PIN","pll0_25MHz","PLL")
design.set_property("pll_inst1","LOCKED_PIN","pll0_LOCKED","PLL"); design.set_property("pll_inst1","RSTN_PIN","","PLL")
design.set_property("pll_inst1","FEEDBACK_MODE","INTERNAL","PLL")
design.assign_resource("pll_inst1","PLL_BR0","PLL")
```

The legal values for `REFCLK_SOURCE` beyond `EXTERNAL` are not documented in the sources: **NOT_FOUND**. The data sheet GUI table lists the Clock Source choices as External, Dynamic and Core [DS Table 14].

### 3.5 Issues in the existing local R06 files

`R06_WORK/fpga/efinity/*` was read only and not modified.

1. **Device name.** `arc1_t35_r06_isf.py` calls `design.create('arc1_t35_r06', 'T35F400C3', …)`. Every public example uses `T35F400` with the grade in the timing model (see 1.2).
2. **API path.** The script appends `$EFINITY_HOME/pt/bin`. The documented path is `os.environ['EFXPT_HOME'] + "/bin"` after `source bin/setup.sh` [PYAPI p.12]. Whether `$EFINITY_HOME/pt` equals `EFXPT_HOME` is **NOT_FOUND** in the sources.
3. **Bank voltages.** No bank voltage is set. Add `design.set_device_property("1C","VOLTAGE","3.3","IOBANK")` and the same for `"1D"`, as [GH_T35] does, or use `set_iobank_voltage("1C","3.3")`.
4. **Pull-up on SS_N.** The pin CSV asks for a weak pull-up on `t35_ss_n`, but the script never sets it. It needs `design.set_property("t35_ss_n","PULL_OPTION","WEAK_PULLUP")`.
5. **Inout pins.** For `t35_miso` and `t35_irq_n`, the script never sets `IN_PIN`, `OUT_PIN` or `OE_PIN`. The defaults follow the `<name>_IN/_OUT/_OE` pattern seen in [GH_T35]. Whether those defaults apply to API-created blocks is **NOT_FOUND**.
6. **PLL reference clock.** `osc_25m` is on GPIOL_66_CLK0 (D20), created as GCLK. Ball D20 is **not** in DS Table 18 (PLL Reference Clock Resource Assignments, BGA400).
   * The external REFCLK pins are GPIOL_15_PLLIN0 (R16) and GPIOL_19_PLLIN1 (P16) for PLL_BL0; GPIOR_138/139/140 (BR); GPIOR_118/119/120 (TR); and the GPIOB/GPIOT CLK pins.
   * The alternative is PLL Clock Source "Core", fed from the core clock tree. FIN from core is 10-330 MHz [DS Tables 14, 90].
   * The constraints for a 25 MHz reference are FPFD 10-100 MHz, FVCO 500-1600 MHz with internal feedback, M 1-255, N 1-15, and O in {1,2,4,8} [DS Tables 15, 90]. A PLL plan must be checked against these.
7. **SDC clock names.** In `arc1_t35_r06.sdc`, `create_clock … [get_ports {sys_clk}]` is applied to PLL outputs. The Interface Designer instead generates `create_clock -period 20.0000 pll0_50MHz`, with no `get_ports`, in `<project>.pt.sdc` [GH_T35 pt.sdc; TIMING p.12 "copy the constraints from <project>.pt.sdc into your SDC file"].

## 4. Command line: `efx_run.py`

Source: Efinity Command-Line Interface UG v1.1 [CLI pp.4-7].

* **Setup and help (Linux):** `source bin/setup.sh`, then `efx_run.py <project name>.xml`. For help, run `efx_run.py --help`.
* **Synopsis:**
  ```
  efx_run.py design [--help] [--prj PRJ] [--flow FLOW] [--tcl_script TCL SCRIPT]
      [-v EXTRA_FILES ...| --flist FLIST] [--tb ...] [--tb_top ...] [--dir SOURCE_DIR]
      [--map_opts ...] [--pt_opts ...] [--pnr_opts ...] [--pgm_opts ...]
      [--modelsim] [--aldec] [--ncsim] [--res_compare] [--output_dir OUTPUT_DIR]
      [--work_dir WORK_DIR] [--timeout TIMEOUT] [--un_flow] [--physical_syn_input ...]
  ```
  * `design` is the positional argument: the "Efinity project XML file name".
  * `--prj` means "Utilize alternate project XML file" and takes no listed input.
* **`--flow` / `-f` values:**

| Value | Action |
|---|---|
| `compile` (default) | Synthesis, place-and-route and bitstream hex |
| `map` | Synthesis |
| `interface` | Generate interface constraint files |
| `pnr` | Place-and-route |
| `pgm` | Create the bitstream hex |
| `program` | Program the device |
| `full` | Full flow, including RTL and post-synthesis simulation |
| `sta_tclsh` | Timing analysis; with `--tcl_script`, runs the script and exits |
| Simulation | `rtlsim`, `mapsim`, `pnrsim`, `ptsimrtl`, `ptsimfc` |
| Library | `setup_efxlib` |

* **Examples:**
  * `efx_run.py helloworld.xml --flow full`
  * `efx_run.py --flow sta_tclsh --tcl_script example_report.tcl`
  * `efx_run.py --prj helloworld_new.xml` [PYAPI p.19]
* **Step-by-step DERIVED order:** `--flow map`, then `--flow interface`, then `--flow pnr`, then `--flow pgm`. This order is not stated in the guide; it comes from the flow descriptions above.

## 5. SDC subset Efinity supports

Source: Efinity Timing Closure UG v7.6, "SDC Constraints (Alphabetical)" pp.53-63 [TIMING].

* **Commands:**
  * check_timing, report_sdc
  * create_clock, create_generated_clock
  * get_fanins, get_fanouts
  * set_bus_syntax_mode (the list writes it `set_bus_syntax`), set_bus_skew
  * set_clock_groups, set_clock_latency, set_clock_uncertainty
  * set_false_path, set_multicycle_path
  * set_input_delay, set_output_delay
  * set_max_delay, set_min_delay
* **Object specifiers:** `all_clocks`, `all_inputs`, `all_outputs`, `all_registers`, `get_cells`, `get_clocks`, `get_nets`, `get_pins` (format `<cell>|<port>`) and `get_ports`, each with an optional `-regexp`.
* **Syntax as documented:**
  ```
  create_clock -period <float> [-waveform {rise fall}] [-name <clock name>] [<targets>] [-add]
  create_generated_clock -source <src> [-divide_by n | -multiply_by n] [-duty_cycle %] [-invert] [-name n] <target>
       [-master_clock c] [-phase deg] [-offset ns] [-edges {n1 n2 n3}] [-edge_shift {..}] [-add]
  set_clock_groups [-exclusive | -asynchronous] -group {<clock>} [-group {...}]   (default -exclusive)
  set_false_path [-setup] [-hold] -from <start> -through <names> -to <end>
  set_input_delay  -clock <clock> [-clock_fall] [-max] [-min] <delay> [-reference_pin] <ports> [-add_delay]
  set_output_delay -clock <clock> [-clock_fall] [-max] [-min] <delay> [-reference_pin] <ports> [-add_delay]
  set_max_delay / set_min_delay -from <start> -through <names> -to <end> <delay>
  set_multicycle_path [-setup] [-start] [-hold] [-end] -from <start> -through <names> -to <end> <value>
  set_clock_uncertainty [-setup] [-hold] [-from c] [-to c] ... <uncertainty>
  set_clock_latency -source [-rise] [-fall] [-setup] [-hold] [-clock <names>] <latency> <target>
  ```
* **Notes:**
  * `-reference_pin` applies to Titanium and Topaz only.
  * Without `set_input_delay` or `set_output_delay`, paths to and from I/Os are not analyzed.
  * Square brackets in bus names are natural by default. With `-regexp`, brackets must be escaped.
  * Using `-name` with no target creates a virtual clock.
  * GPIO GCLK clocks get commented `create_clock` templates in `<project>.pt.sdc`. PLL clocks are generated with their real values.
  * For an inout GPIO, the I/O ports are `<pin>_IN`, `<pin>_OUT` and `<pin>_OE`, for example `create_clock -period 10 -name bclk [get_ports bclk_IN]` [TIMING "Using the create_clock Constraint" GPIO example].
  * The local draft `arc1_t35_r06.sdc` uses only supported commands: `create_clock`, `set_clock_groups -asynchronous`, `set_input_delay`, `set_output_delay` with `-max`/`-min`, and `set_false_path -from/-to [get_ports …]`. Its clock targets need correcting (see 3.5, item 7).
