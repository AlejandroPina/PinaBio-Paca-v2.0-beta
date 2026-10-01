# PinaBio v.2.0. Cursor

Diseño de competición en KiCad 9.0.9, solo con lo que queda escrito en SPEC-0.8 / PWR-0.7. Los sensores van a sus conectores sin relé, MOSFET ni conmutador en serie. El aislador USB es externo, en el cable. El BQ24074 entra en standby con el interruptor (EN1, EN2 y CE); no hay MOSFET de corte de VBUS.

Placa 81,34 × 57,17 mm, cuatro capas: F.Cu masa, In1.Cu masa, In2.Cu 3V3_SYS, B.Cu señales. El USB queda bajo el módulo, el buck a la izquierda y el analógico a la derecha. Hay un keepout de antena en el borde del ESP32-S3-MINI-1.

## Comprobaciones

| Informe | Resultado |
| --- | --- |
| `erc.rpt` | 0 errores, 0 avisos |
| `drc.rpt` | 0 errores, 0 avisos, 0 sin conectar |

El DRC incluye errores y avisos. No queda ninguno. La paridad esquemático–PCB también está a cero.

`fab/` tiene los Gerber (cobre, máscara, pasta, serigrafía y contorno), los Excellon PTH y NPTH, los mapas de taladro y `position.csv` en milímetros.

## Huellas que no están en la biblioteca oficial

- `lib.pretty/TPS63070RNM.kicad_mod`: patrón de tierra del encapsulado RNM (VQFN-HR de 15 pines) según el dibujo 4222000/B de TI, en SLVSC58B. Pads de señal 0,25 × 0,60 mm; pines 9–11 (L2, PGND, L1) con el cobre de 1,25 mm de ese ejemplo. Sin thermal pad. El cheurón de serigrafía está fuera de la máscara, junto al pin 1.
- Símbolo `ADS122C04` en `PinaCursor.kicad_sym`: patillaje TSSOP-16 PW de SBAS751B, figura 69. Huella oficial `Package_SO:TSSOP-16_4.4x5mm_P0.65mm`.

El resto sale de las bibliotecas de KiCad 9. El módulo es un ESP32-S3-MINI-1; la huella oficial que coincide con ese patrón se llama `RF_Module:ESP32-S2-MINI-1U` (el nombre del fichero en KiCad 9 es ese). TLV75530, MCP6004, BSS138, BSS84 y USBLC6 son alias del símbolo padre de la biblioteca. Los conectores de sensor y de batería son JST PH de la serie B. La bobina de 1,5 µH usa la huella `L_Coilcraft_XAL4020`, de la misma clase que el XFL4020.

## Reglas de la placa

- Separación de cobre 0,15 mm, pista mínima 0,15 mm, vía 0,50 / 0,25 mm (paso de 0,65 mm; anillo 0,125 mm).
- Separación agujero–cobre 0,15 mm. Con 0,20 mm no pasa la huella oficial USB-C HCTL: sus taladros de posición quedan a 0,185 mm de los pads de carcasa. No se ha editado esa huella.
- Separación cobre–borde 0,30 mm. Taladro mínimo de vía 0,25 mm.

## Lo que la spec no numera

Estos valores no están en la spec; no son corrientes de módulo:

- R22, R25, R26 y R27 son 10 kΩ (habilitación de módulo y pull-up de interrupciones / DRDY).
- Los 100 nF de desacoplo del op-amp y de los buses.
- R3 es 0 Ω en serie con VBUS: la spec no da el valor de un fusible, y este puente no abre VBUS.
- R15 es 0 Ω entre 3V3_SYS y 3V3_A. Es el mismo buck, no un segundo regulador.
- GPIO4 = SDA y GPIO5 = SCL del bus de los ADS. GPIO8 = SDA y GPIO9 = SCL de los módulos. El throw A del interruptor (pines 1 y 4) es ON. OS del CJMCU-30205 va a J5 y a TP1; no tiene GPIO, y una red de un solo pin no pasa el ERC.

El ruteo automático dejó tramos cortos de señal sobre In1 e In2. Los planos se rellenan alrededor. Un tramo de `/DIV_EXC` en In2 se desvió para que `/ECG_DIV` pudiera salir del ADS.
