<p align="center"><img src="assets/pina-logo.jpg" alt="PINA — Protocols and Innovation in Applied Neuroscience logo" width="640"></p>

# PinaBio Paca v2.0 beta — design documentation

[Español](README.md)

This documentation defines a protected 1S LiPo, a BQ24074 and a single nominal 3.3 V rail. With the switch OFF and USB connected, the battery charges and the ESP32 can be programmed. With the switch ON and USB connected, the BQ24074 standby mode leaves the system powered from the battery and stops charging. USB can carry data; a host-powered external USB isolator is required whenever a person is connected.

The board is designed to acquire ECG, PPG, GSR, two respiration bands, local temperature and battery voltage. It is an experimental biofeedback design, not a medical device.

## Documentation

- [Hardware specification (EN)](docs/en/specification.md)
- [Power and USB (EN)](docs/en/power-usb.md)
- [Protocol (EN)](docs/en/protocol.md)
- [V1 comparison (EN)](docs/en/v1-comparison.md)
- [Especificación de hardware (ES)](docs/es/especificacion.md)
- [Alimentación y USB (ES)](docs/es/alimentacion-usb.md)
- [Protocolo BLE y datos (ES)](docs/es/protocolo.md)
- [Comparación V1/V2 (ES)](docs/es/comparacion-v1.md)
- [Registro de revisión (ES)](docs/es/revision-diseno.md)

Before manufacture, the actual breakouts, KiCad schematic and PCB, body-contact paths, and the specified electrical and isolation tests must be independently verified.
