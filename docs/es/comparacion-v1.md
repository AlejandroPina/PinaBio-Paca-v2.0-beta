# PinaBio V1 frente a V2 — revisión `CMP-0.4`

[Portada](../../README.md) · [Especificación V2](especificacion.md)

V1 cuenta con placa, firmware y aplicación publicados. V2 ya tiene esquemático y PCB de prototipo en KiCad 9.0.9 con ERC/DRC/paridad cero, pero todavía no hay una placa montada, firmware ni aplicación V2 verificados. Las mejoras son objetivos de diseño, no prestaciones demostradas.

| Aspecto | V1 | V2 revisada | Condición |
|---|---|---|---|
| ECG | ADS1115 compartido | ADS122C04 dedicado, 600 SPS y DRDY | Verificar ruido, divisor y 50/60 Hz. |
| GSR / respiración | Excitación ≈0,5 V, tres señales lentas | ADS lento separado, MCP6004 y 100 kΩ físicos en serie | Medir sensibilidad de bandas y corriente de fallo. |
| PPG / temperatura | Módulos existentes | Módulos externos con INT PPG y conectores directos | Verificar cada breakout y niveles a 3,3 V / 3,0 V. |
| Alimentación | Regulación distribuida de V1 | LiPo + BQ24074 + TPS63070 a 3,3 V y TLV75530PDBVR a 3,0 V solo para temperatura | Medir picos y carga; no hay 2,9 V. |
| USB | Regla de no usar USB sobre la piel | Carga/programación con OFF; datos con ON y aislador externo | Aislador medido desde el lado host; cable normal no apto sobre persona. |
| Conexiones al cuerpo | Conectores directos | Conectores directos; el aislamiento con USB durante adquisición es externo | No hay desconexión automática de sensores al conectar USB. |
| Software | Firmware/app V1.1 | PROTO-0.4 nuevo, no implementado | Sin compatibilidad ni adaptador V1.1. |

V2 aumenta control de potencia, temporización y separación de adquisición, pero todavía retrocede en madurez hasta montar y ensayar el prototipo y completar firmware y aplicación.
