<p align="center"><img src="assets/pina-logo.jpg" alt="Logo de PINA — Protocolos e Innovación en Neurociencia Aplicada" width="640"></p>

# PinaBio Paca v2.0 beta — revisión documental

[English](README.en.md)

Este conjunto define una LiPo 1S con BQ24074, un TPS63070 a 3,3 V y un LDO de 3,0 V solo para el sensor de temperatura. Con el interruptor OFF y USB conectado se carga la batería y se permite programar. Con ON y USB, el modo standby del BQ24074 deja el sistema alimentado por la batería y detiene la carga; USB transporta datos, y requiere un aislador externo alimentado desde el host cuando haya una persona conectada.

La placa registra ECG, PPG, GSR, dos bandas respiratorias, temperatura local y batería. Es un diseño experimental de biofeedback, no un dispositivo médico.

## Documentación

- [Especificación de hardware (ES)](docs/es/especificacion.md)
- [Alimentación y USB (ES)](docs/es/alimentacion-usb.md)
- [Protocolo BLE y datos (ES)](docs/es/protocolo.md)
- [Comparación V1/V2 (ES)](docs/es/comparacion-v1.md)
- [Registro de revisión (ES)](docs/es/revision-diseno.md)
- [Hardware specification (EN)](docs/en/specification.md)
- [Power and USB (EN)](docs/en/power-usb.md)
- [Protocol (EN)](docs/en/protocol.md)
- [V1 comparison (EN)](docs/en/v1-comparison.md)

Antes de fabricación son obligatorios: verificación de cada breakout, esquemático y PCB KiCad, comprobación de las rutas hacia el cuerpo y los ensayos eléctricos descritos en la especificación. Los conectores de sensores no llevan cortes automáticos; para USB durante la adquisición con una persona se exige un aislador externo.
