"""ARC-OS requirements linked to the existing source-bound Hardware Proof graph."""
import csv,io
from . import hardware_proof


def inspect(root):
    proof=hardware_proof.report(root)
    binding=hardware_proof.bind(root)
    b="hardware/compact-arc1/R10_WORK/"
    def refs(names):
        return [{"path":b+n,"sha256":binding[b+n]} for n in names]
    rows=list(csv.DictReader(io.StringIO((root/(b+"memory/R10_nor_partition.csv")).read_text())))
    requirements=[
        ("rom_boot", "F133 ROM → boot0/DDR → loader → ARC-OS", "UNPROVEN",
         ["memory/R10_nor_partition.csv","memory/R10_memory_owner_map.md","cad/boot_nor.kicad_sch"],
         "Board-qualified ROM format, boot0/DDR training, linker map, recovery and boot logs are missing. Partition boot_rom_reads is a proposal, not proof."),
        ("usb_gamecard", "F133 owns USB/controller/GameCard services", "UNPROVEN",
         ["cad/usb_host.kicad_sch","cad/usb_link.kicad_sch","cad/usb_power.kicad_sch"],
         "Host normalization tested; actual HID descriptor parsing, controller driver, media transport, power switching and USB topology need qualified target evidence."),
        ("d213", "Separate D213 firmware and private RAM", "UNPROVEN",
         ["memory/R10_memory_owner_map.md","memory/R10_nor_partition.csv"],
         "D2FA/B storage does not establish flashless ROM loading. F133 → D213 transport and display startup remain unqualified."),
        ("fpga", "Independent FPGA12 / FPGA45 configuration", "UNPROVEN",
         ["memory/R10_nor_partition.csv","memory/R10_memory_owner_map.md"],
         "Stored bitstream sizes do not prove reset, pins, timing or physical configuration. Use existing G3 findings and trace."),
        ("host_sdk", "Portable game lifecycle, normalized input and service callbacks", "HOST-TESTED",
         ["memory/R10_memory_owner_map.md"],
         "Host ABI runs trusted modules in one host process. No target MMU isolation, live RGMII, USB audio or hardware video is implied."),
    ]
    return {"class":"STATIC_CHECK","contract":"arc-os.dependencies/1",
            "source_binding":binding,"fabrication":"HOLD","kernel_selection":"PENDING",
            "requirements":[dict(id=i,requirement=r,status=s,sources=refs(f),missing_proof=m)
                            for i,r,s,f,m in requirements],
            "nor_partitions":rows,
            "memory":{"f133":"64 MiB volatile DDR2 selected design; target allocation unqualified",
                      "nor":"64 MiB proposed persistent storage; not additional RAM",
                      "d213":"128 MiB private DDR3 selected design; no shared address space",
                      "fpga45":"32 MiB candidate private SDRAM",
                      "fpga12":"4 MiB candidate private PSRAM",
                      "kernel_launcher_game_stack_reserves":"UNALLOCATED pending linked target images and measured high-water marks"},
            "hardware_findings":proof["findings"],
            "transfer_model":{"version":1,"opcode":1,"max_payload":4096,"status":"HOST-MODELED; no physical transport"}}
