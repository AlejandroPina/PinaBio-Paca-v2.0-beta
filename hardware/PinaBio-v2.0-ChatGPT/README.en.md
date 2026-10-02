# PinaBio v2.0 ChatGPT — KiCad 9 project

[Español](README.md) · [Hardware specification](../../docs/en/specification.md) · [Power and USB](../../docs/en/power-usb.md)

**Status: engineering prototype for review. Do not release for manufacture or connect a person until the pending checks are complete.** The schematic, PCB and BOM are editable KiCad 9.0.6 files. Revision H1 uses **four layers and measures 96 × 96 mm**: signals and local copper on the outer faces, continuous ground on In1 and `3V3_SYS` distribution on In2. The existing outer ground and power pours remain. Both TPS63070–inductor switch connections remain on the component side without vias.

H1 deliberately keeps a **continuous inner ground plane**, whereas `SPEC-0.9` and Cursor use a split ground. The ADC digital bus and other signals cross between the digital and analogue areas; a continuous return plane avoids routing their return current around a ground slot. This is a layout proposal to compare and measure, not a proven performance claim. The board is larger than Cursor's; only an actual JLCPCB quotation can settle the cost difference.

## Files

- [`PinaBio-v2.0-ChatGPT.kicad_pro`](PinaBio-v2.0-ChatGPT.kicad_pro): project.
- [`PinaBio-v2.0-ChatGPT.kicad_sch`](PinaBio-v2.0-ChatGPT.kicad_sch): schematic.
- [`PinaBio-v2.0-ChatGPT.kicad_pcb`](PinaBio-v2.0-ChatGPT.kicad_pcb): routed PCB.
- [`PinaBio-v2.0-ChatGPT-BOM.csv`](PinaBio-v2.0-ChatGPT-BOM.csv): per-reference BOM; [grouped BOM](PinaBio-v2.0-ChatGPT-BOM-grouped.csv): 93 placements and 54 groups. **This is not a JLCPCB purchasing BOM**: LCSC numbers and specific manufacturers for generic parts remain to be selected.
- [`PinaBio-v2.0-ChatGPT-PinNets.csv`](PinaBio-v2.0-ChatGPT-PinNets.csv): numbered schematic pin connections.
- [`ERC-H1.txt`](ERC-H1.txt), [`DRC-H1.txt`](DRC-H1.txt), the [schematic PDF](preview/PinaBio-v2.0-ChatGPT.pdf) and the [H1 front view](preview/pcb-front-H1.pdf) for review.
- Local symbols, footprints and the ESP32 3D model are included; see [library licences](LIBRARY-LICENSE.md).

## Circuits and connectors

| Reference | Planned connection |
| --- | --- |
| J1 | USB-C 2.0 for data and charging, two 5.1 kΩ CC resistors, ESD and TVS protection. |
| J2 | Protected 1S LiPo with 10 kΩ NTC: 1 `BAT_PROT`, 2 `GND`, 3 `BAT_NTC`. Check the actual cable polarity. |
| SW1 | Physical DPDT switch. OFF+USB enables charging/programming; ON+USB sets BQ24074 standby, stops charging and permits battery-powered USB data. |
| J3 | External AD8232: 1 `3V3_A`, 2 `GND`, 3 `OUTPUT`, 4 `LO+`, 5 `LO−`, 6 `SDN`. Electrode jack is on the module. |
| J4/J5/J6 | Two-wire GSR/thorax/abdomen connections. Pin 1 is driven through 100 kΩ; pin 2 is ground. The sense node enters MCP6004 through another 100 kΩ. |
| J7 | MAX30102 breakout: 1 VIN `3V3_SYS`, 2 GND, 3 SCL, 4 SDA, 5 INT. |
| J8 | MAX30205 breakout: 1 VCC `3V0_TEMP`, 2 GND, 3 SDA, 4 SCL, 5 OS, 6 A0, 7 A1, 8 A2; address pins are grounded. **Contact count and order are provisional pending inspection of the actual breakout.** |
| J9 | UART debug: 1 GND, 2 `3V3_SYS`, 3 TX, 4 RX; never use as a power input. |

TPS63070 uses 49.9 kΩ/16.0 kΩ, 0.1 %, for a nominal 3.295 V set point. TLV75530PDBVR supplies 3.0 V to J8 only. AD8232 output passes through a 33.2 kΩ/47.5 kΩ divider into its dedicated ADS122C04. The other ADS122C04 uses three single-ended inputs for GSR and both respiration bands; its fourth input is tied to the 0.5 V excitation and is not a free AUX channel. PGA bypass, sampling and I²C addressing are described in the [specification](../../docs/en/specification.md).

Sensor connectors remain continuously wired to their front ends: **there are no relays, MOSFETs or switches to disconnect sensors**. When a person is connected, USB may be used only through a host-powered external isolator. No person may be connected during OFF+USB charging/programming. This PCB contains no galvanic isolation.

## Checks completed

- KiCad 9 ERC: **0 violations**.
- KiCad 9 DRC: **0 violations and 0 unconnected items**.
- Comparison of 329 connected schematic pins with PCB pad nets: **0 differences**.
- Both TPS63070–inductor traces are approximately 4.7 mm, with no via. Thirteen `BAT_PROT`, `VBUS_RAW` and `SYS` segments were widened where DRC allowed; tight sections by pins and vias retain their original widths. Two local return vias were added near the ESP32 and ADCs. Voltage drop still requires measurement under real load.
- The inner layers contain no signal tracks. In1 ground remains continuous and In2 distributes 3.3 V.

These checks do not validate component choice, current, temperature, analogue noise, EMC or use on a person.

## Gates before ordering from JLCPCB

1. Check the **three actual breakout boards** for pin order, voltage limits, I²C pull-ups, peak current and connector orientation; revise J3/J7/J8 as needed. J8 is particularly provisional.
2. Independently review the local `TPS63070_RNM0015A` footprint, all package orientations, drill sizes, BQ24074 thermal pad, U.FL connector area and the selected parts' JLCPCB assembly compatibility.
3. Measure ESP32/PPG peak load, `3V3_SYS`, `3V0_TEMP`, startup and ON/OFF/USB transitions, no charging in ON+USB, temperatures and voltage drops. Validate the protected LiPo and cable.
4. Measure ECG, GSR, respiration and 50/60 Hz pickup with actual modules and electrodes; test the external USB isolator in ON+USB mode.
5. Select exact manufacturer and LCSC part numbers, check assembly, add fiducials, then generate Gerbers, drill files and placement files **after** the preceding checks are closed.

ERC and DRC detect CAD errors but do not certify a body-connected circuit. Accordingly, this directory does not yet contain a released manufacturing Gerber package.
