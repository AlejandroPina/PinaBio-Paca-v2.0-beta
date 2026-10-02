# PinaBio Paca v2.0 beta — hardware specification `SPEC-0.9`

This design specification now has a KiCad 9.0.9 prototype implementation. ERC, DRC and schematic/PCB parity are zero; independent footprint review and tests on an assembled board are still required. PinaBio is for experimental research and biofeedback, not medical use or diagnosis.

## Scope and power architecture

The ESP32-S3-MINI-1U-N8 acquires ECG, PPG, GSR, thoracic and abdominal respiration bands, local temperature and battery voltage, then sends raw data over BLE with Wi‑Fi disabled. One ADS122C04 is dedicated to ECG; the other serves GSR and both bands. MAX30102 and MAX30205 are external I²C modules.

LiPo 1S protected → BQ24074 → TPS63070 → nominal 3.295 V `3V3_SYS` (49.9 kΩ / 16.0 kΩ, 0.1 %, forced PWM). An initially 0 Ω link may feed a `3V3_A` analogue island. A TLV75530PDBVR makes `3V0_TEMP` only for the CJMCU-30205, with 2.2 µF X7R 0805 at input and output. There is **no 2.9 V rail, TPS7A20 or TCA9801**.

## USB, switch and body connections

USB-C is a USB 2.0 sink: CC1/CC2 have 5.1 kΩ Rd resistors. D+ and D− pass through a USBLC6-2SC6 in SOT-23-6 (the same pinout as the USBLC6-2P6: connector on one side, ESP32 on the other, GND and VBUS as on that symbol) and then through 22 Ω in series: D− to GPIO19 and D+ to GPIO20. Protected VBUS reaches BQ24074 IN in both switch positions. There is no external VBUS-cutoff MOSFET. The physical switch sets the charger mode pins and regulator enable independently of the ESP32.

The switch is not on the board: it mounts in the enclosure. The part is a C&K 7201SYZQE (7000 series, DPDT, two maintained ON-ON positions, threaded panel bushing, six solder-lug terminals). It is not momentary, not a three-position switch, and it is not the JS202011JCQN. The datasheet is *7000 Series Miniature Toggle Switches* ([PDF](https://media.digikey.com/pdf/Data%20Sheets/C&K/7000%20Mini%20Toggle%20Series.pdf)); the DPDT figure on page 2 names 7201SYZQE. The code reads: 7201 = DP On-None-On, S = 0.420 in actuator, Y = 0.350 in bushing with keyway and 1/4-40 thread, Z = six solder lugs, Q = contact material, E = epoxy seal. Commons are terminals 2 and 5. ON is the lever away from the keyway (datasheet position 3): it closes 2-1 and 5-4. OFF is the lever toward the keyway (position 1): it closes 2-3 and 5-6. The cable is one-to-one: board pad 1 `VLOG` to terminal 1, pad 2 `EN2_CE` to terminal 2, pad 3 `GND` to terminal 3, pad 4 `BAT_PROT` to terminal 4, pad 5 `TPS_EN` to terminal 5, and pad 6 `VLOG` to terminal 6. ON therefore ties `EN2_CE` to `VLOG` and `TPS_EN` to `BAT_PROT`; OFF ties `EN2_CE` to `GND` and `TPS_EN` to `VLOG`. The six board holes have no orderable code; the code belongs to the enclosure switch.


With OFF and valid VBUS, `EN1=high`, `EN2=low` and `CE=low` allow charging and USB-powered OUT; USB500 is permitted only when the source supports that current. With ON and valid VBUS, `EN1=EN2=high` select standby/USB suspend: internal `Q1` (IN→OUT) is open, `Q2` (BAT→OUT) is closed and charging stops. `CE=high` adds charge inhibition but cannot alone prevent USB from powering OUT. EN1, EN2 and CE must be driven by the physical switch and VBUS, remain defined with no battery, and never rely on firmware. ILIM, ISET and ITERM are sized for the actual USB source, cell and initial ≈300 mA charge target. TMR is 46.4 kΩ, 1 %, to ground. TS connects to the cell NTC. GPIO0 is reserved for BOOT, with a 10 kΩ pull-up to `3V3_SYS`; the BOOT button takes it to ground.

The VBUS-derived logic must meet these limits at each EN1, EN2 and CE pin: low **0–0.4 V**, high **1.4–6 V**, absolute maximum **−0.3 to 7 V**, including transients. The schematic must provide the necessary voltage limiting/protection and operating margin below 6 V; 7 V is not a design target. The higher voltage tolerance at IN does not extend to these pins. See [power and USB](power-usb.md).

The TPS63070 hardware enable must implement `(OFF and valid VBUS) or (ON and valid battery)`. This permits OFF+USB programming without a battery while preventing ON+USB from starting without one. The schematic must define the battery-valid condition and verify source transitions on an ON→OFF switch movement. [TI BQ24074 datasheet](https://www.ti.com/lit/ds/symlink/bq24074.pdf), Table 7-2 and Section 9.3.2.

| Switch | USB | BQ24074 mode | Board source | LiPo charge | USB data | Person-connected use |
|---|---:|---|---|---|---|---|
| OFF | no | invalid input | none | no | no | no acquisition |
| OFF | yes | USB500 if source permits | USB through BQ24074 | yes | yes, programming | no person connected |
| ON | no | invalid input | LiPo | no | no | battery acquisition |
| ON | yes | standby, `EN1=EN2=high` | LiPo | no | yes | external USB isolator required |

With OFF, USB powers the ESP for programming and charges the cell; removing USB powers the board down. With ON, D+/D− remain available and OUT is battery powered even though VBUS remains at charger IN. ECG, PPG, temperature, GSR and respiration connectors connect directly to their respective front ends, without automatic cutoff relays or switches. OFF+USB can therefore energize sensor connectors; direct-USB charging and programming require removing all sensors from the person.

An external host-powered USB isolator is mandatory for use with a person while USB is connected. The board USB ground is not cut; isolation belongs in the external cable. Firmware can report USB presence but cannot prove that an isolator is fitted. A normal USB cable must not be used on a person.

## Acquisition front ends

| Signal | Implementation and initial configuration |
|---|---|
| ECG | External AD8232, dedicated ADS122C04, internal 2.048 V reference, PGA bypass, gain 1, 600 SPS. Divider: 33.2 kΩ from OUTPUT and 47.5 kΩ to ground, 1 %. At a 3.30 V full-scale output the ADC sees 1.94 V; at 3.40 V it sees 2.00 V, under the 2.048 V reference. Do not use 20.0/40.2 kΩ. Measure the real swing to confirm the module does not clip before the divider. A divider cannot repair an OUTPUT that is already clipped. |
| GSR | MCP6004-buffered ≈0.50 V excitation; a physical 100 kΩ series resistor limits normal short-circuit current to ≈5 µA. |
| Thorax / abdomen | One identical buffered front end each; measure real band ranges before freezing 100 kΩ and filters. |
| PPG | External MAX30102/GY-30102, 3.3 V, I²C plus INT; validate its actual regulators, pull-ups, LED current and voltage levels. |
| Temperature | CJMCU-30205 from `3V0_TEMP` only, on a 4-pin connector (3V0_TEMP, GND, SDA, SCL). Module VCC ties straight to the chip. A0, A1 and A2 of the module are tied to GND on the module itself (solder or a short wire), not through the cable, and set address 0x48. The module's OS is left unconnected (the module carries its own 10 kΩ pull-up). |

The slow ADS initially samples GSR, thorax and abdomen at 20 SPS each. Report OPEN, SHORT, OUT_OF_RANGE and UNCALIBRATED rather than false values. Bands provide resistance and a derived respiratory curve, not lung volume. ADS IDACs remain disabled and never connect to body paths.

## Board

Four layers. The ChatGPT implementation is **84.50 × 53.11 mm**; the modest width increase provides room for J3 labels outside the connector. USB-C is at the lower edge with its mouth extending past the outline. The ESP32-S3-MINI-1U has no printed antenna: it has a U.FL connector. That end of the module sits at the upper board edge, as far out as it will go, so the external antenna is outside the copper. On every layer, under that end and a little past the module edge outward, there is no copper, no track, no via and no plane. USB and the buck do not sit under that zone.

There are two ground planes. Digital ground covers the ESP32, USB, the BQ24074 and the TPS63070. Analogue ground covers the ADS122C04 devices, the MCP6004, the ECG divider, GSR and the bands. They join in one place, short and wide, next to the ADCs and the 0 Ω link between `3V3_SYS` and `3V3_A`, so the supply and the return meet at the same point. There are no extra joins and no thin track crossing the board. Analogue signals do not cross digital ground. In1 is ground, split into those two zones. F.Cu carries the same split, stitched with vias to its own zone. In2 is `3V3_SYS` and carries no data signals. B.Cu carries the signals.

Both TPS63070 inductor nodes stay on F.Cu, with no via, at 0.40 mm for the whole run.

## Mandatory verification

Measure every breakout; test all four USB/switch states including no battery; prove ON+USB leaves OUT on BAT with zero charge current and VBUS/D+/D− cannot back-power ON-without-battery. Capture EN1, EN2 and CE during steady states and switch/USB transients to check their voltage limits. With OFF+USB, document voltage at the sensor connectors. Measure 3.3 V ripple and load, GSR fault current, ECG range/noise, external buses and USB-isolator behaviour. KiCad 9.0.9 schematic, PCB, BOM, Gerbers, drill and placement outputs exist with ERC, DRC and schematic/PCB parity at zero. Footprint checks, body-connected-path review and these bench results remain necessary before a production order.

## ChatGPT implementation contract

- J3, external AD8232 module: pin 1 AGND/GND, 2 3V3_A/3.3V, 3 ECG_OUT/OUTPUT, 4 LO_N/LO−, 5 LO_P/LO+, 6 3V3_A/SDN. SDN remains enabled. This matches the red module order for a flat cable.
- J5, CJMCU-30205: pin 1 3V0_TEMP, 2 GND, 3 SDA, 4 SCL. J9 battery meter: JST PH B2B-PH-K-S(LF)(SN), pin 1 switched BAT+, pin 2 GND. A BSS84LT1G high-side device and BSS138LT1G enable it only while 3V3_SYS exists; 1 MΩ ties the BSS84 gate to its source. J9 is for meters drawing only tens of mA.
- R39, YAGEO RC0603FR-0710KL, 10 kΩ 1 %, is in series between TPS_EN and TPS63070 EN, close to the IC. The 100 kΩ R12 pulldown remains on the switch side. PS/SYNC stays grounded. R3 remains 0 Ω.
- L1 is Coilcraft **XAL4020-152MEC**, 1.5 µH with the unchanged XAL4020 footprint; “C” denotes 7-inch reel packaging.
- J3 silkscreen labels form one column outside and aligned with its six pins. The reduced PINA logo and “PinaBio Paca v.2.0.” appear on top. Connector names and pin labels are at least 1.0 mm high with 0.15 mm stroke.
