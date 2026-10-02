![PCB PinaBio Paca v.2.0., cara superior](PinaBio-v2.0-ChatGPT-top.png)

# PINABio "Paca" v.2.0. — placa ChatGPT

[English](README.en.md) · [Especificación completa](../../docs/es/especificacion.md) · [Alimentación y USB](../../docs/es/alimentacion-usb.md)

Proyecto editable de **KiCad 9.0.9**, cuatro capas, **84,50 × 53,11 mm**. Deriva de la implementación de Cursor y conserva su arquitectura: un USB-C soldado, BQ24074 en standby mediante interruptor exterior, sin MOSFET de corte de VBUS, dos reguladores, sin cortes automáticos de sensores ni pull-ups nuevos de I²C, dos masas unidas solo en NT1 y keepout de cobre en todas las capas bajo el extremo U.FL del ESP32. La zona del TPS63070 y la bobina mantiene los nodos SW_L1 y SW_L2 en F.Cu, 0,40 mm y sin vías; la huella RNM conserva el pin 1 arriba a la izquierda y la numeración antihoraria.

## Archivos y verificación

- `PinaBio-v2.0-ChatGPT.kicad_sch`, `.kicad_pcb` y `.kicad_pro`: esquemático y PCB.
- `PinaCursor.kicad_sym`, `lib.pretty/`, `sym-lib-table` y `fp-lib-table`: bibliotecas necesarias.
- `bom.csv`: lista de materiales con MPN. L1 es **Coilcraft XAL4020-152MEC**.
- `fab/`: Gerbers de las cuatro capas, máscaras, pasta, serigrafía, contorno, taladros PTH/NPTH y `position.csv` en milímetros. `PinaBio-v2.0-ChatGPT-Gerbers.zip` agrupa los 14 archivos de placa y taladro para subirlos al fabricante; BOM y posiciones se entregan por separado.
- `final-erc.txt` y `final-parity.txt`: **ERC 0, DRC 0, 0 sin conectar y paridad esquema-PCB 0**, ejecutados con KiCad 9.0.9.
- `Logo PINA-reducido.jfif`: imagen fuente del logo que se convirtió a serigrafía monocroma.

Los Gerbers son **de prototipo**. Antes de fabricar o montar, otra persona debe cotejar las huellas con los componentes comprados y ensayar una primera unidad, en especial la orientación del USB-C y TPS63070, las transiciones ON/OFF/USB y el cableado de los módulos externos.

## Conectores

| Referencia | Conexión por orden de pin |
|---|---|
| J1 | USB-C HCTL HC-TYPE-C-16P-01A, boca en el borde inferior; D+ y D− pasan por USBLC6-2SC6 y resistencias de 22 Ω. |
| J2 BATT | 1 BAT+ protegido, 2 GND, 3 TS/NTC. JST PH de 3 pines. La serigrafía usa «BATT» debajo del conector. |
| J3 ECG | 1 AGND, 2 3V3_A, 3 ECG_OUT, 4 LO_N, 5 LO_P, 6 3V3_A (SDN permanentemente habilitado). Orden del módulo rojo: GND, 3.3V, OUTPUT, LO−, LO+, SDN. |
| J4 PPG | 1 3V3_SYS/VIN, 2 GND, 3 SCL, 4 SDA, 5 INT. «VIN» identifica la alimentación del módulo; las otras cuatro señales están rotuladas junto a sus pines. |
| J5 TEMP | 1 3V0_TEMP, 2 GND, 3 SDA, 4 SCL. JST PH de 4 pines; unir A0/A1/A2 a GND en el módulo CJMCU-30205. |
| J6 GSR | 1 señal GSR, 2 AGND. |
| J7 RESP T | 1 señal torácica, 2 AGND. |
| J8 RESP A | 1 señal abdominal, 2 AGND. |
| J9 BATT METER | 1 BAT+ conmutado por Q4 BSS84/Q5 BSS138, 2 GND. JST PH B2B-PH-K-S(LF)(SN), solo para medidor de unas decenas de mA. |

J9 solo entrega tensión cuando está activo **3V3_SYS** (ON con batería u OFF con USB). Q4 tiene una resistencia de 1 MΩ entre puerta y fuente. La alimentación del medidor procede de BAT_PROT y no está destinada a alimentar otros módulos.

## Interruptor y alimentación

SW1 son **seis taladros para cable**, no una huella para soldar el interruptor. La pieza de referencia en la caja es C&K **7201SYZQE**, DPDT ON-ON. Puede emplearse otro DPDT ON-ON de seis terminales, como un MTS-202, después de verificar con multímetro sus comunes y contactos. Taladros 1–6 corresponden a terminales 1–6 de la referencia C&K: 1 VLOG, 2 EN2_CE, 3 GND, 4 BAT_PROT, 5 TPS_EN y 6 VLOG.

R39 de **10 kΩ, 1 %**, junto al pin EN del TPS63070, separa TPS_EN de TPS_EN_IC. R12 de 100 kΩ queda al lado del interruptor. PS/SYNC va a masa para PWM forzado. El TLV75530PDBVR alimenta **solo** el módulo de temperatura a 3,0 V; R3 de VBUS continúa en **0 Ω**.

Con OFF y USB se carga la batería y la placa puede programarse. Con ON y USB el BQ24074 está en standby: el sistema se alimenta de la LiPo, USB lleva datos y la batería no carga. Para conectar a una persona en ese modo se exige un aislador USB externo apropiado. No hay aislador ni desconexión automática de sensores en la PCB.
