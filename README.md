QUE QUEDA. No hay nada en marcha.

1. El interruptor. Esta bien conectado, pero la placa no dice que lado es ON. Hay que mirar la pieza real.
2. La bobina de 1,5 uH. El BOM no tiene su codigo de fabricante: la huella y la hoja de datos no coinciden, y no he inventado un codigo.
3. Antes de fabricar, mirar a ojo el trazado alrededor del TPS63070, sobre todo la masa de debajo.

En el modulo de temperatura, unir A0, A1 y A2 a masa. El mazo del ECG cruza alimentacion con masa, y LO+ con LO-. El del pulso y el de temperatura pueden ir rectos. Eso ya esta escrito en la carpeta de la placa.

<p align="center"><img src="assets/pina-logo.jpg" alt="Logo de PINA — Protocolos e Innovación en Neurociencia Aplicada" width="640"></p>

# PinaBio Paca v2.0 beta — documentación y prototipo KiCad

[English](README.en.md)

Este conjunto define una LiPo 1S con BQ24074, un TPS63070 a 3,3 V y un LDO de 3,0 V solo para el sensor de temperatura. Con el interruptor OFF y USB conectado se carga la batería y se permite programar. Con ON y USB, el modo standby del BQ24074 deja el sistema alimentado por la batería y detiene la carga; USB transporta datos, y requiere un aislador externo alimentado desde el host cuando haya una persona conectada.

La placa registra ECG, PPG, GSR, dos bandas respiratorias, temperatura local y batería. Es un diseño experimental de biofeedback, no un dispositivo médico.

## Documentación

- [Proyecto KiCad 9 «PinaBio-v2.0-ChatGPT»](hardware/PinaBio-v2.0-ChatGPT/README.md) — esquemático, PCB enrutada, BOM e informes ERC/DRC; **prototipo pendiente de validación, sin Gerbers liberados para fabricación**.
- [Proyecto KiCad 9 «PinaBio-v2.0-Cursor»](hardware/cursor/PinaBio-v2.0-Cursor/README.md) — la misma placa según `SPEC-0.9` / `PWR-0.7`, con la antena U.FL en el borde y la masa partida.
- [Especificación de hardware (ES)](docs/es/especificacion.md)
- [Alimentación y USB (ES)](docs/es/alimentacion-usb.md)
- [Protocolo BLE y datos (ES)](docs/es/protocolo.md)
- [Comparación V1/V2 (ES)](docs/es/comparacion-v1.md)
- [Registro de revisión (ES)](docs/es/revision-diseno.md)
- [Hardware specification (EN)](docs/en/specification.md)
- [Power and USB (EN)](docs/en/power-usb.md)
- [Protocol (EN)](docs/en/protocol.md)
- [V1 comparison (EN)](docs/en/v1-comparison.md)

Antes de fabricación son obligatorios: revisión independiente de huellas y esquema, verificación de cada breakout, comprobación de las rutas hacia el cuerpo y los ensayos eléctricos descritos en la especificación. Los conectores de sensores no llevan cortes automáticos; para USB durante la adquisición con una persona se exige un aislador externo.
