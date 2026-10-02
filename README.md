FOTOS DE LOS MODULOS.

Temperatura: si. Dos fotos del CJMCU-30205. El orden es VCC, GND, SDA, SCL, OS, A0, A1, A2. Por eso el conector de la placa quedo en 4 pines: 3V0, GND, SDA, SCL. A0, A1 y A2 se unen a masa en el modulo.

PPG: si, una foto del modulo morado de 5 agujeros, con el regulador de 1,8 V. En esa foto no se leen los nombres de los pines. No puedo comprobar si el orden de la placa (3V3, GND, SCL, SDA, INT) coincide con el modulo. Hace falta una foto donde se lean SCL, SDA e INT.

ECG: no. No tengo foto del modulo AD8232. La comparacion con SparkFun salio de su esquema publicado, no de una foto tuya. Si me la mandas otra vez, miro el orden de los pines.

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
