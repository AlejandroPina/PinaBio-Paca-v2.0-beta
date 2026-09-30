# PinaBio Paca — firmware, BLE and data contract `PROTO-0.5`

This is a proposed protocol, not implemented firmware. Multibyte fields are little-endian; raw data, calibration and loss markers are retained and the board makes no diagnosis.

States are `BOOT`, `IDLE_USB`, `IDLE_BATTERY`, `ACQUIRING`, `LOW_BATTERY`, `SENSOR_FAULT` and `INTERNAL_FAULT`. `LEADS_OFF` remains an ECG flag. VBUS is not an automatic lockout: `ACQUIRING` may be entered with ON, battery and a correctly fitted external isolator. Firmware reports `physical_vbus` and `isolation_unverified`; it cannot certify the cable. START requires ON, power-good and sensor self-test. There are no sensor cutoff relays or contact-feedback signals. With OFF+USB, remove sensors from the person before charging or programming.

ECG uses ADS `0x40` at 600 SPS; GSR, thorax and abdomen use ADS `0x41` in single-shot mode at an initial 20 SPS per channel. PPG starts at 200 RED/IR pairs per second and temperature/battery at 1 Hz. BLE service and frame compatibility remain as `PROTO-0.3`: service UUID `b88b0000-1a8c-4a2b-ae02-50494e414249`, Control/Data/Status/Metadata/ControlResult characteristics, minimum MTU 128, 22-byte header and CRC-16/CCITT-FALSE.

STATUS includes state, reason, `physical_vbus`, `isolation_unverified`, ADC overrun, BLE loss and PPG overflow. START may fail with `LOW_BATTERY`, `SENSOR_FAULT`, `INTERNAL_FAULT` or `MTU_TOO_SMALL`; `CONTACT_OPEN` and `VBUS_LOCKOUT` are removed. Test data loss, MTU, ECG/PPG timing and USB acquisition with a measured external isolator before implementation release.
