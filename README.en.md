![PinaBio Paca v.2.0., ChatGPT PCB top view](hardware/PinaBio-v2.0-ChatGPT/PinaBio-v2.0-ChatGPT-top.png)

# PinaBio Paca v2.0 beta

[Español](README.md)

An experimental board for ECG, optical pulse (PPG), skin conductance (GSR), two respiration bands and temperature, with BLE data transmission. It is intended for research and biofeedback, not medical use.

The new **PinaBio Paca v.2.0.** board is in [hardware/PinaBio-v2.0-ChatGPT](hardware/PinaBio-v2.0-ChatGPT/README.en.md). It is an editable **KiCad 9.0.9** project with schematic, four-layer PCB, BOM, Gerbers, drill files and placement file. The outline is **84.50 × 53.11 mm**. KiCad 9.0.9 reports **ERC 0, DRC 0, 0 unrouted connections and 0 schematic/PCB parity issues**. These are prototype manufacturing outputs; an independent footprint review and electrical validation of the first assembled board are still required.

## Architecture

- ESP32-S3-MINI-1U-N8, external U.FL antenna, BLE, Wi-Fi disabled.
- Two ADS122C04 converters: one dedicated to 600 SPS ECG and one for GSR, chest respiration, abdominal respiration and AUX.
- MCP6004, external AD8232 module, external GY-MAX30102 module and external CJMCU-30205 module.
- Protected 1-cell LiPo, BQ24074 power path, TPS63070 for 3V3_SYS and TLV75530PDBVR at 3.0 V solely for temperature.
- One edge-mounted USB-C for charging, programming and data. The external DPDT ON-ON switch sets the BQ24074 mode and TPS63070 enable. With ON and USB attached, the board runs from its battery and charging stops.
- No automatic sensor disconnects or onboard USB isolation. Acquisition with a person connected and USB attached requires a suitable external USB isolator.

## Documents

- [ChatGPT PCB project and connector map](hardware/PinaBio-v2.0-ChatGPT/README.en.md)
- [Hardware specification](docs/en/specification.md)
- [Power and USB](docs/en/power-usb.md)
- [Data protocol](docs/en/protocol.md)
- [V1 comparison](docs/en/v1-comparison.md)
- [Preserved Cursor design for reference](hardware/cursor/PinaBio-v2.0-Cursor/README.md)

**Before ordering assembly:** confirm orientation and dimensions of the USB-C, TPS63070, all connectors and wired switch; measure the actual three external modules; test all ON/OFF/USB transitions and charger and regulator voltages. KiCad reports do not replace these checks.
