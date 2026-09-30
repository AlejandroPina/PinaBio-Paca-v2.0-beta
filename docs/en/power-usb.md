# Power and USB — revision `PWR-0.6`

[Home](../../README.en.md) · [Hardware specification](specification.md)

One USB-C connector, a protected 1S LiPo, a BQ24074 power path and a TPS63070 provide the single nominal 3.3 V rail. The physical switch controls the BQ24074 mode and the regulator enable; firmware does not choose the charging or system power source.

With **OFF and USB**, `EN1=high`, `EN2=low` and `CE=low` select USB500 mode. Valid `IN` powers `OUT` and charges the cell; TPS63070 can power the ESP32 for programming. All body paths remain open. Select the 500 mA input limit only when the USB source permits it. The initial battery-charge target is about 300 mA; measure the simultaneous system load during programming.

With **ON and USB**, `EN1=EN2=high` select standby/USB suspend. TI specifies that internal `Q1` (IN→OUT) is off and `Q2` (BAT→OUT) is on: the battery powers the board and charging stops. `CE=high` adds charge inhibition but cannot replace standby because CE alone leaves USB-powered OUT active. VBUS remains at the charger's `IN` pin; “battery only” describes the source of OUT and the board, not a physically unpowered USB connector or charger. Native D+/D− remain available for programming and data.

Without USB, IN is invalid and OUT follows the battery. ON enables TPS63070; OFF disables it. Any USB acquisition with a person connected requires an external host-powered isolator that separates data, ground and power and supplies the appropriate VBUS on the board side.

| Switch | USB | `EN1/EN2/CE` with valid VBUS | OUT source | Charge | ESP32 | Body paths |
|---|---|---|---|---|---|---|
| OFF | no | biased low; invalid input | battery, system load disabled | no | off | open |
| OFF | yes | high/low/low | USB | yes | on for maintenance | open |
| ON | no | invalid input | battery | no | on | armable |
| ON | yes | high/high/high | battery | no | on, USB data | armable only with external isolator |

## Hardware requirements

- Protected VBUS connects to BQ24074 IN in both switch positions. **Do not fit the external VBUS-cutoff MOSFET.** Place the IN and OUT capacitors required by TI.
- EN1 must be high when VBUS is valid. EN2 and CE must be high with ON and VBUS, low with OFF and VBUS. The physical switch and bias network must establish these levels without the ESP32 or battery; no control input may float. Verify levels and sequencing when USB is inserted and the switch moves.
- For EN1, EN2 and CE, TI specifies a **1.4–6 V** high level, a **0–0.4 V** low level and an **−0.3 to 7 V** absolute-maximum range. The 7 V limit is not a design target. The network deriving these signals from VBUS must limit their voltage during normal operation, insertion and foreseeable overvoltage, with margin below 6 V; do not connect raw VBUS directly without demonstrating compliance. The IN pin has a different, higher absolute maximum that does not protect the logic pins.
- With ON, USB and no battery, standby must prevent OUT from powering the board from USB. The regulator must not start without a valid battery. With OFF, USB and no battery, programming may start.
- Select ILIM, ISET, ITERM, TMR and TS for the actual USB source, cell and NTC. BQ24074 has no SYSOFF pin and does not replace cell protection.
- Body contacts must open before the BQ24074 can change from battery to USB supply when moving ON→OFF. Hardware timing and verification remain schematic requirements; firmware timing alone is insufficient.
- TPS63070 runs in forced PWM and provides the only 3.3 V rail. Check voltage at the MAX30205 pin and reduce the setpoint if it exceeds 3.3 V. Start the analogue-island feed with 0 Ω and choose a ferrite only after noise measurements.
- USB-C has ESD protection and separate 5.1 kΩ Rd resistors on CC1/CC2. D+/D− and VBUS detection must not back-power an off ESP32. The external isolator must create its board-side isolated VBUS from the host.

## Acceptance tests

Measure voltage and current at IN, OUT, BAT, 3V3_SYS and USB in all four states. Capture EN1, EN2 and CE with an oscilloscope in steady state and during USB insertion/removal, VBUS disturbances and switch movement; verify functional thresholds and absolute limits. With ON+USB, OUT must track the battery, charge current must be zero, and removing the battery must not start the board through VBUS or D+/D−. With OFF+USB, test charging and programming without a battery. Verify that body paths open before USB can power the system. Measure external-isolator performance, 3.3 V ripple, module current and charger temperature. Person-connected sessions remain unapproved until the results and contact tests are documented.

[TI BQ24074 datasheet](https://www.ti.com/lit/ds/symlink/bq24074.pdf), Table 7-2 and Section 9.3.2.
