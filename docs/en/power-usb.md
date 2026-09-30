# Power and USB — revision `PWR-0.4`

There is one USB-C connector, a protected 1S LiPo and a BQ24074 power path. OFF makes a high-side MOSFET pass VBUS to BQ24074, so the battery charges and the TPS63070 can power the ESP32 for programming. All body paths are open.

ON blocks VBUS from BQ24074. The board runs from the LiPo and native USB D+/D− still support programming and data, but USB neither powers the board nor charges the cell. A host-powered external USB isolator is mandatory to use USB during a session on a person. Board ground stays connected to USB ground; the external isolator provides the isolation.

`EN1` is high, `EN2` is grounded, `CE` is grounded, and `ILIM`, `ISET` and `TS` are populated from the actual USB source, LiPo and NTC design. The initial charge target is about 300 mA. No control pin may float. TPS63070 supplies the only 3.3 V rail in forced PWM; no 2.9 V LDO is used. Validate VBUS blocking, diode orientation, no back-power with ON/no battery, charger temperature, ripple and actual module/contact current before release.
