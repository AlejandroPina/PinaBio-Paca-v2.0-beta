# PinaBio Paca v2.0 beta — hardware specification `SPEC-0.6`

This is a design-review specification, not a validated schematic or manufacturing release. PinaBio is for experimental research and biofeedback, not medical use or diagnosis.

## Scope and power architecture

The ESP32-S3-MINI-1U-N8 acquires ECG, PPG, GSR, thoracic and abdominal respiration bands, local temperature and battery voltage, then sends raw data over BLE with Wi‑Fi disabled. One ADS122C04 is dedicated to ECG; the other serves GSR and both bands. MAX30102 and MAX30205 are external I²C modules.

LiPo 1S protected → BQ24074 → TPS63070 → one nominal `3V3_SYS` rail. An initially 0 Ω link may feed a `3V3_A` analogue island. There is **no 2.9 V rail, TPS7A20 or TCA9801**. TPS63070 uses forced PWM. Prototype measurements must keep MAX30205 supply within 3.0–3.3 V.

## USB, switch and body connections

USB-C is a USB 2.0 sink: CC1/CC2 have 5.1 kΩ Rd resistors; D+/D− have low-capacitance ESD and connect to GPIO19/20. Protected VBUS reaches BQ24074 IN in both switch positions. There is no external VBUS-cutoff MOSFET. The physical switch sets the charger mode pins and regulator enable independently of the ESP32.

With OFF and valid VBUS, `EN1=high`, `EN2=low` and `CE=low` allow charging and USB-powered OUT; USB500 is permitted only when the source supports that current. With ON and valid VBUS, `EN1=EN2=high` select standby/USB suspend: internal `Q1` (IN→OUT) is open, `Q2` (BAT→OUT) is closed and charging stops. `CE=high` adds charge inhibition but cannot alone prevent USB from powering OUT. EN1, EN2 and CE must be driven by the physical switch and VBUS, remain defined with no battery, and never rely on firmware. ILIM, ISET and ITERM are sized for the actual USB source, cell and initial ≈300 mA charge target; TS connects to the cell NTC.

The VBUS-derived logic must meet these limits at each EN1, EN2 and CE pin: low **0–0.4 V**, high **1.4–6 V**, absolute maximum **−0.3 to 7 V**, including transients. The schematic must provide the necessary voltage limiting/protection and operating margin below 6 V; 7 V is not a design target. The higher voltage tolerance at IN does not extend to these pins. See [power and USB](power-usb.md).

The TPS63070 hardware enable must implement `(OFF and valid VBUS) or (ON and valid battery)`. This permits OFF+USB programming without a battery while preventing ON+USB from starting without one. The schematic must define the battery-valid condition and open all body contacts before changing from battery power to USB power on an ON→OFF transition. [TI BQ24074 datasheet](https://www.ti.com/lit/ds/symlink/bq24074.pdf), Table 7-2 and Section 9.3.2.

| Switch | USB | BQ24074 mode | Board source | LiPo charge | USB data | Body paths |
|---|---:|---|---|---|---|---|
| OFF | no | invalid input | none | no | no | open |
| OFF | yes | USB500 if source permits | USB through BQ24074 | yes | yes, programming | open |
| ON | no | invalid input | LiPo | no | no | armable |
| ON | yes | standby, `EN1=EN2=high` | LiPo | no | yes | armable only with an external USB isolator |

With OFF, USB powers the ESP for programming and charges the cell; removing USB powers the board down. With ON, D+/D− remain available and OUT is battery powered even though VBUS remains at charger IN. Body connectors use normally-open contacts for every conductor, including power, ground and each signal. Closing requires ON, power-good, self-test and physical feedback; firmware cannot override the barrier.

An external host-powered USB isolator is mandatory for use with a person while USB is connected. The board USB ground is not cut; isolation belongs in the external cable. Firmware can report USB presence but cannot prove that an isolator is fitted. A normal USB cable must not be used on a person.

## Acquisition front ends

| Signal | Implementation and initial configuration |
|---|---|
| ECG | External AD8232, dedicated ADS122C04, internal 2.048 V reference, PGA bypass, gain 1, 600 SPS. Calculate the AD8232 output divider after measuring the 3.3 V-powered module; the former 20.0/40.2 kΩ divider is not accepted without that test. |
| GSR | MCP6004-buffered ≈0.50 V excitation; a physical 100 kΩ series resistor limits normal short-circuit current to ≈5 µA. |
| Thorax / abdomen | One identical buffered front end each; measure real band ranges before freezing 100 kΩ and filters. |
| PPG | External MAX30102/GY-30102, 3.3 V, I²C plus INT; validate its actual regulators, pull-ups, LED current and voltage levels. |
| Temperature | External MAX30205 at 3.3 V, I²C address 0x48; validate pull-ups and local thermal behaviour. |

The slow ADS initially samples GSR, thorax and abdomen at 20 SPS each. Report OPEN, SHORT, OUT_OF_RANGE and UNCALIBRATED rather than false values. Bands provide resistance and a derived respiratory curve, not lung volume. ADS IDACs remain disabled and never connect to body paths.

## Mandatory verification

Measure every breakout; test all four USB/switch states including no battery; prove ON+USB leaves OUT on BAT with zero charge current and VBUS/D+/D− cannot back-power ON-without-battery. Capture EN1, EN2 and CE during steady states and switch/USB transients to check their voltage limits, and prove body contacts open before USB can power the system. Measure 3.3 V ripple and load; prove opening of every body conductor under GPIO failure; test GSR fault current, ECG range/noise, external buses and USB-isolator behaviour. KiCad capture, BOM, independent body-path review and these results are required before manufacture.
