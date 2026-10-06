# Power and USB — revision `PWR-0.7`

[Home](../../README.en.md) · [Hardware specification](specification.md)

One USB-C connector, a protected 1S LiPo, a BQ24074 power path and a TPS63070 at 3.295 V. A TLV75530PDBVR makes 3.0 V only for the CJMCU-30205. The physical switch controls the BQ24074 mode and the regulator enable; firmware does not choose the charging or system power source.

With **OFF and USB**, `EN1=high`, `EN2=low` and `CE=low` select USB500 mode. Valid `IN` powers `OUT` and charges the cell; TPS63070 can power the ESP32 for programming. Sensor connectors are not automatically disconnected; remove sensors from the person before charging or programming with direct USB. Select the 500 mA input limit only when the USB source permits it. The initial battery-charge target is about 300 mA; measure the simultaneous system load during programming.

With **ON and USB**, `EN1=EN2=high` select standby/USB suspend. TI specifies that internal `Q1` (IN→OUT) is off and `Q2` (BAT→OUT) is on: the battery powers the board and charging stops. `CE=high` adds charge inhibition but cannot replace standby because CE alone leaves USB-powered OUT active. VBUS remains at the charger's `IN` pin; “battery only” describes the source of OUT and the board, not a physically unpowered USB connector or charger. Native D+/D− remain available for programming and data.

Without USB, IN is invalid and OUT follows the battery. ON enables TPS63070; OFF disables it. Any USB acquisition with a person connected requires an external host-powered isolator that separates data, ground and power and supplies the appropriate VBUS on the board side.

| Switch | USB | `EN1/EN2/CE` with valid VBUS | OUT source | Charge | ESP32 | Person-connected use |
|---|---|---|---|---|---|---|
| OFF | no | biased low; invalid input | battery, system load disabled | no | off | no acquisition |
| OFF | yes | high/low/low | USB | yes | on for maintenance | no person connected |
| ON | no | invalid input | battery | no | on | battery acquisition |
| ON | yes | high/high/high | battery | no | on, USB data | external isolator required |

## Hardware requirements

- Protected VBUS connects to BQ24074 IN in both switch positions. **Do not fit the external VBUS-cutoff MOSFET.** Place the IN and OUT capacitors required by TI.
- EN1 must be high when VBUS is valid. EN2 and CE must be high with ON and VBUS, low with OFF and VBUS. The physical switch and bias network must establish these levels without the ESP32 or battery; no control input may float. Verify levels and sequencing when USB is inserted and the switch moves.
- For EN1, EN2 and CE, TI specifies a **1.4–6 V** high level, a **0–0.4 V** low level and an **−0.3 to 7 V** absolute-maximum range. The 7 V limit is not a design target. The network deriving these signals from VBUS must limit their voltage during normal operation, insertion and foreseeable overvoltage, with margin below 6 V; do not connect raw VBUS directly without demonstrating compliance. The IN pin has a different, higher absolute maximum that does not protect the logic pins.
- With ON, USB and no battery, standby must prevent OUT from powering the board from USB. The regulator must not start without a valid battery. With OFF, USB and no battery, programming may start.
- Select ILIM, ISET, ITERM and TS for the actual USB source, cell and NTC. TMR is 46.4 kΩ, 1 %, to ground. BQ24074 has no SYSOFF pin and does not replace cell protection.
- No sensor-connector cutoff relays or switches are fitted. OFF+USB may power those connectors from VBUS, so direct-USB charging and programming require all sensors to be removed from the person. ON+USB with a person requires a host-powered external isolator.
- TPS63070 runs in forced PWM. Feedback divider: 49.9 kΩ from VOUT to FB and 16.0 kΩ from FB to ground, both 0.1 %. Setpoint 3.295 V. PS/SYNC tied low. Both inductor nodes stay on the top copper, with no via, at 0.40 mm for the whole run. The TLV75530PDBVR, with 2.2 µF X7R 0805 at input and output, makes 3.0 V only for the CJMCU-30205 VCC. Those capacitors keep at least 0.47 µF of effective capacitance. Start the analogue-island feed with 0 Ω. Analogue ground and digital ground meet at one short, wide point next to that link and the ADCs, so the supply and the return join together. There are no other joins.
- USB-C uses a USBLC6-2SC6 in SOT-23-6 and separate 5.1 kΩ Rd resistors on CC1/CC2. Between the protector and the ESP32, D− (GPIO19) and D+ (GPIO20) each have 22 Ω in series. D+/D− and VBUS detection must not back-power an off ESP32. The external isolator must create its board-side isolated VBUS from the host. GPIO0 has a 10 kΩ pull-up to `3V3_SYS`; the BOOT button takes it to ground.
- R39 (10 kΩ, 1 %, YAGEO RC0603FR-0710KL) is in series and close to TPS63070 EN; the 100 kΩ R12 pulldown remains on the switch side to avoid a permanent divider. L1 is Coilcraft XAL4020-152MEC, 1.5 µH, with the unchanged footprint. J9 provides BAT+ to a meter only while 3V3_SYS is active: Q4 BSS84 high-side, Q5 BSS138 pull-down, and 1 MΩ from Q4 gate to source. R3 remains a 0 Ω VBUS link, not a fuse.

## Acceptance tests

Measure voltage and current at IN, OUT, BAT, 3V3_SYS and USB in all four states. Capture EN1, EN2 and CE with an oscilloscope in steady state and during USB insertion/removal, VBUS disturbances and switch movement; verify functional thresholds and absolute limits. With ON+USB, OUT must track the battery, charge current must be zero, and removing the battery must not start the board through VBUS or D+/D−. With OFF+USB, test charging and programming without a battery and document voltage at the sensor connectors. Measure external-isolator performance, 3.3 V ripple, module current and charger temperature. Test person-connected acquisition with USB only after verifying the external isolator.

[TI BQ24074 datasheet](https://www.ti.com/lit/ds/symlink/bq24074.pdf), Table 7-2 and Section 9.3.2.
