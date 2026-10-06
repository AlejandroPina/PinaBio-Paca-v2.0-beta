![PinaBio Paca v.2.0., cara superior de la PCB](hardware/PinaBio-Paca-v2.0/PinaBio-Paca-v2.0-top.png)

# PinaBio Paca v2.0 beta

[English](README.en.md)

Placa experimental para registrar ECG, pulso óptico (PPG), respuesta galvánica de la piel (GSR), dos bandas de respiración y temperatura, y transmitir los datos por BLE. El uso previsto es investigación y biofeedback; no es un dispositivo médico.

La nueva placa **PINABio "Paca" v.2.0.** se encuentra en [hardware/PinaBio-Paca-v2.0](hardware/PinaBio-Paca-v2.0/README.md). Es un proyecto editable de **KiCad 9.0.9**, con esquemático, PCB de cuatro capas, BOM, Gerbers, taladros y posiciones. Mide **84,50 × 53,11 mm**. KiCad 9.0.9 informa **ERC 0, DRC 0, 0 conexiones pendientes y 0 diferencias entre esquemático y PCB**. Los archivos de fabricación son una salida de prototipo; falta la inspección independiente de huellas y la validación eléctrica de la primera placa ensamblada.

## Qué lleva

- ESP32-S3-MINI-1U-N8 con antena externa U.FL, BLE y Wi-Fi desactivado.
- Dos ADS122C04: uno dedicado al ECG a 600 SPS y otro para GSR, respiración torácica, respiración abdominal y AUX.
- MCP6004, módulo AD8232 externo, módulo GY-MAX30102 externo y módulo CJMCU-30205 externo.
- LiPo protegida de una celda, BQ24074 con power-path, TPS63070 para 3V3_SYS y TLV75530PDBVR a 3,0 V solo para la temperatura.
- Un USB-C soldado en el borde para carga, programación y datos. El interruptor exterior DPDT ON-ON controla el modo del BQ24074 y la habilitación del TPS63070. Con ON y USB, el sistema funciona desde la batería y no carga.
- No hay cortes automáticos en los sensores ni aislamiento USB en la placa. Para adquirir con una persona conectada y USB presente se requiere un aislador USB externo apto para ese uso.

## Documentación

- [Proyecto y conexiones de la PCB](hardware/PinaBio-Paca-v2.0/README.md)
- [Especificación de hardware](docs/es/especificacion.md)
- [Alimentación y USB](docs/es/alimentacion-usb.md)
- [Protocolo y datos](docs/es/protocolo.md)
- [Comparación con V1](docs/es/comparacion-v1.md)

**Antes de encargar montaje:** confirmar orientación y dimensiones del USB-C, TPS63070, todos los conectores y el interruptor cableado; medir los tres módulos externos reales; verificar las transiciones ON/OFF/USB y las tensiones del cargador y reguladores. Los informes de KiCad no sustituyen estas pruebas.
