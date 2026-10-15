---
title: ARC-1 Compact — architecture recommendation R0.3
date: 14 October 2026
---

**Recommended combination: Allwinner F133-B + Efinix T35F400C3 + Bridgetek BT820B.** Use this as the leading prototype for the handoff’s rich 2D and selective 2.5D goal. Keep F133 + T35 + BT817 as the simpler comparison, and TH1520 module + FPGA + integrated GPU as the alternative if general textured polygons become essential.

This recommendation preserves the three locked roles. It introduces a new graphics candidate rather than freezing parts. Vendor capabilities have been checked against documentation; the proposed interfaces still require implementation and hardware qualification. STRUTHIO performance, FPGA timing closure and complete system cost have not been measured. This is exploratory engineering, not a schematic or fabrication release. The reference is the supplied ARC1_Handoff R0.2; ARC-1 Tabletop and SLIM4 remain separate.

## Why this combination leads

STRUTHIO primarily needs animated bitmap objects, transparency, independent background layers, scaling/rotation and selected perspective effects. A dedicated command renderer fits those needs, while the FPGA provides programmable arithmetic, rendering experiments and precise peripheral timing. F133’s integrated 64 MB DDR avoids a separate CPU memory layout. Its suitability assumes a purpose-built game runtime; a general desktop engine and its memory demands require a separate assessment. [Allwinner F133 brief](https://www.allwinnertech.com/uploads/pdf/20211016141154e7.pdf)

BT820B addresses important BT817 limitations: larger asset memory, more drawing commands and an actual FPGA video-input option. Its cost in complexity is external graphics DDR, a 329-ball BGA and LVDS display output. It is not a pin-compatible or software-compatible replacement.

| Property | BT817 baseline | BT820B candidate |
|---|---|---|
| Graphics memory | 1 MiB internal RAM_G | External DDR; MN820 module supplies 128 MiB |
| Display list | 8 KiB | 16 KiB |
| Command FIFO | 4 KiB | 16 KiB |
| Maximum host QSPI clock | 30 MHz | 60 MHz |
| Display output | Parallel RGB | LVDS |
| Live video input | No normal live-video input | LVDS capture |
| Rendering approach | Scanline object rendering | DDR framebuffer rendering |

Specifications: [BT817 datasheet](https://brtchip.com/wp-content/uploads/2022/04/DS_BT817_8.pdf), [BT820 datasheet v1.1](https://brtchip.com/wp-content/uploads/2025/01/DS_BT820-1.pdf), [BT82X programming guide v1.4](https://brtchip.com/wp-content/uploads/2026/09/BRT_AN_086_BT82X-Series-Programming-Guide-1.pdf), [MN820 module](https://brtchip.com/product/mn820/).

Both EVE generations provide affine bitmap transforms, not a general perspective-correct textured-triangle pipeline. Perspective floors can use transformed strips, pre-rendered assets or FPGA-generated imagery. BT820 assets render from DDR after loading from storage; preserve that distinction when planning animation and asset updates.

## Proposed ownership and connections

**F133-B → SPI0 scene mailbox → T35F400C3 → QSPI commands → BT820B → LVDS display.**

| Element | Initial responsibility | Private memory/storage |
|---|---|---|
| F133-B | Fixed-tick game simulation, game state, loading and CPU-side services | Its embedded DDR; boot/game storage |
| T35F400C3 | Calculate transform coefficients from scene inputs, construct/schedule drawing commands, sample timed inputs | Block RAM initially; its own DDR if pixel effects are retained |
| BT820B | Active sprite drawing, affine transformations, alpha composition and display presentation | Its own DDR3L and asset storage |

The FPGA is the sole master of the accelerator’s host bus. Define an explicit scene packet, frame sequence, bounded queue, ready/interrupt signals and asset-transfer operation. Keep input timestamps and display completion feedback available to the CPU. Benchmark the FPGA kernel against CPU execution so its value is demonstrated.

F133 SPI0’s PC2–PC7 pin group supports quad operation and overlaps SD/MMC2. Using SD0 for initial boot/storage leaves that group available. PC4/PC5 also serve as boot-selection pins: preserve the required straps and keep FPGA data pins high impedance during reset/boot and whenever the slave is not selected. SPI1 overlaps CPU LCD pins, but this topology does not require CPU video output. Actual DMA behavior, board pin availability, reset states, signal levels and throughput still need validation. [Allwinner-authored F133 datasheet v2.3, distributor mirror](https://cdn.semikey.com/upload/pdfs/4c/5e/4c5e315c6bb9cc2f9ecf223359e639c3.pdf)

T35F400C3 has 31,680 logic elements, 120 multipliers, 230 GPIO and hardened x8/x16 DDR. Its LVDS transmit capability makes a video-output implementation plausible, but does not supply an already-validated LVDS video transmitter. F256 cannot substitute into the hardened-DDR design. [Efinix T35 selector](https://www.efinixinc.com/shop/t35.php)

For a fixed board intended to support future pixel effects, retain FPGA-local DDR and route an optional **FPGA LVDS output → BT820 LVDS input**. Start with command-generated effects. Promote the live-video route only after testing synchronization, image quality and input-to-display latency. BT820 can consume captured video as a bitmap, but buffering may add frames of latency. Use an opaque procedural/background plane; captured RGB video does not provide a per-pixel alpha channel. CPU RAM, FPGA DDR and graphics DDR remain three separately owned memory systems.

BT820 output requires an LVDS panel or an explicitly designed receiver/bridge. A parallel-RGB panel cannot connect directly. The panel, orientation, connector and backlight remain open. Preserve the authoritative game’s camera and logical viewport while evaluating framing.

## Budgets that make the proposal credible

These calculations establish useful bounds, not measured performance:

- A 16 KiB display list holds 4,096 32-bit instruction words, versus 2,048 for BT817. State changes, transforms and backgrounds all consume that space; 256 instances are not a guaranteed capacity.
- Sending 16 KiB once per 60 Hz frame requires 0.983 MB/s of payload. CPU-to-FPGA scene descriptors may be smaller. Coprocessor commands, framing, asset uploads and effect updates add traffic.
- At an illustrative 24 MHz single-bit SPI rate, that list alone consumes about 5.46 ms before overhead. Quad operation may improve margin, but must be measured. Double-buffer queues allow different stages to overlap only when frame ownership is correct.
- BT820’s 60 MHz quad-SPI raw ceiling is 30 MB/s. A 480×800 RGB565 frame at 60 Hz requires 46.08 MB/s. Full-frame host streaming is therefore unsuitable; keep assets and rendering local to the accelerator.
- One 1-Gbit memory device contains 128 MiB. BT820 reserves the upper 2.5 MiB of DDR; exclude that region, then allocate atlases, render targets, capture buffers and alignment. The FPGA’s future memory size requires its own bandwidth and capacity budget. [BT82X guide, §2.1](https://brtchip.com/wp-content/uploads/2026/09/BRT_AN_086_BT82X-Series-Programming-Guide-1.pdf)

A large transparent sprite covering the screen can be more expensive than many small sprites. The benchmark must vary covered pixels, overlap, transformations and asset changes, rather than treating object count as the complete workload.

## What the checked prices establish

Public USD listings checked on 14 October 2026:

| Item | Listed single-unit price | Source/qualification |
|---|---:|---|
| F133-B | $12.05 | [LCSC](https://www.lcsc.com/product-detail/Microcontrollers-MCU-MPU-SOC_Allwinner-Tech-F133-B_C22438485.html); page reported 101 in stock |
| T35F400C3 | $33.84 | [DigiKey](https://www.digikey.com/en/products/detail/efinix-inc/T35F400C3/15861258); page reported 3,817 in stock, with 45-week standard replenishment lead time |
| BT820B | $11.50 | [Bridgetek](https://brtchip.com/product/bt820b/); manufacturer price table, shipment availability requires checking |
| MN820 graphics module | $52 | [Bridgetek](https://brtchip.com/product/mn820/); BT820 and 128 MiB DDR3L included |
| VM820C development assembly | $99 | [Bridgetek](https://brtchip.com/product/vm820c/); MN820 included, display excluded |

The three bare core ICs total approximately **$57.39**, mixing vendors at their displayed one-unit tiers. The module and development assembly are alternatives, not additional entries in that subtotal. Neither this subtotal nor the historical $100 semiconductor reference covers the complete system. Add graphics DDR and FPGA DDR if retained for the pixel-effects board, plus storage, power, clocks, resets, audio amplification, display support and any bridges; cost PCB/assembly and mechanics separately. Prices exclude shipping, tax and tariffs and are not purchase quotes.

Efinity licenses are currently free to request; retain the exact installer, license process and project versions. [Efinity license request](https://www.efinixinc.com/products-efinity.html), [Efinix licensing terms](https://www.efinixinc.com/support/sw-maintenance.php). An official T35 development kit was not verified. Other Efinix boards can prove portions of the RTL, but their resources and DDR implementation do not validate the final T35 board.

## When to choose the GPU alternative

If future games need general textured polygons, depth testing and shaders, qualify **TH1520 on a Lichee Module 4A + T35 + the SoC’s integrated BXM-4-64 GPU**. This satisfies the distinct accelerator role without an external EVE device. The module integrates the SoC, RAM and storage, reducing initial memory-layout work. [Sipeed module documentation](https://wiki.sipeed.com/hardware/en/lichee/th1520/lm4a.html)

Mesa currently lists the TH1520 GPU’s exact 36.52.104.182 variant as Vulkan 1.2 conformant. Sipeed documents an upstream graphics path and distinguishes it from older vendor images. This gives it a stronger software basis to investigate than selecting JH7110 or K1 from advertised API support alone. Mesa still lists their respective BXE variants as unsupported in that driver; that does not mean their vendor graphics stacks are unusable. [Mesa support matrix](https://docs.mesa3d.org/drivers/powervr.html), [Sipeed graphics guidance](https://wiki.sipeed.com/hardware/en/lichee/th1520/lpi4a/5_desktop.html)

Use **CPU/GPU → SoC display controller → HDMI or qualified panel interface**, with the FPGA on a separate control/math/audio link. Verify exposed module pins before selecting that link. This branch requires an actual power/thermal/BOM comparison and a pinned accelerated software stack; API conformance does not prove STRUTHIO frame time.

## Qualification sequence and decision rule

1. **Recover the authoritative STRUTHIO build and render trace.** Record simulation rules, viewport, sprite dimensions, atlases, blending, transformed objects and worst scenes. The historical 256×384 manual is a comparison, not automatic authority.
2. **Evaluate BT820 graphics first on VM820C.** Its USB-QSPI bridge permits a computer-driven scene test before the final CPU/FPGA integration. Match the intended output resolution and constrain command delivery to the planned embedded link budget. Include the handoff’s 256-instance/four-layer/64-transform challenge and a convincing perspective effect.
3. **Measure genuine presentation.** Run the scene for 30 minutes at 60 Hz. Record unique frames, deadline misses, worst and percentile frame times, display-list/FIFO high-water marks, transfer bursts, visual artifacts and input-to-photon latency. A panel refreshing at 60 Hz while repeating frames is not a pass.
4. **Integrate F133 and FPGA.** Re-run with actual game simulation, audio and input traffic. Demonstrate the selected FPGA acceleration kernel, queued bus protocol and recovery behavior. Compile/place/route against the exact T35 package and close timing. Validate DDR and optional LVDS effects on actual hardware.
5. **Complete the system evidence.** Verify the selected display, power sequence, recovery/update path, thermals, package procurement, full pin allocation and costed BOM before parts freeze or PCB release.

Advance the F133/T35/BT820 combination when the representative scene meets fidelity, cadence and agreed latency targets with useful resource margin. Use BT817 when its measured scene is sufficient and simpler RGB/no-graphics-DDR hardware matters more. Switch to the TH1520/GPU branch when the desired visual language depends on general polygons/shaders or the EVE model cannot produce the required scene efficiently. Change FPGA size/package only in response to measured resource fit, timing or sourcing.

The next useful investment is one representative STRUTHIO renderer running on the leading accelerator, followed by the actual command chain. That test can turn this recommendation into a defensible hardware selection.
