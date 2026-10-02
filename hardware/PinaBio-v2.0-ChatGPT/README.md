# PinaBio v2.0 ChatGPT — proyecto KiCad 9

[English](README.en.md) · [Especificación general](../../docs/es/especificacion.md) · [Alimentación y USB](../../docs/es/alimentacion-usb.md)

**Estado: prototipo de ingeniería para revisión. No liberar a fabricación ni conectar a una persona sin las verificaciones pendientes.** El esquemático, la PCB y la BOM son archivos nativos y editables de KiCad 9.0.6. Esta revisión H1 usa **cuatro capas y 96 × 96 mm**: señales y cobre local en las caras externas, masa continua en In1 y distribución de `3V3_SYS` en In2. Conserva los vertidos exteriores de masa y alimentación. Las dos conexiones TPS63070–bobina siguen en la cara superior, sin vías.

La PCB H1 conserva deliberadamente una **masa interior continua**, a diferencia de la masa partida descrita en `SPEC-0.9` y usada por Cursor. El bus digital de los ADC y otras señales cruzan entre las zonas digital y analógica; mantener una referencia de retorno continua evita obligarlas a rodear una ranura de masa. Es una propuesta de trazado para comparar y medir, no una afirmación de superioridad demostrada. La placa es mayor que la de Cursor y la diferencia de coste exige una cotización real de JLCPCB.

## Archivos

- [`PinaBio-v2.0-ChatGPT.kicad_pro`](PinaBio-v2.0-ChatGPT.kicad_pro): proyecto.
- [`PinaBio-v2.0-ChatGPT.kicad_sch`](PinaBio-v2.0-ChatGPT.kicad_sch): esquemático.
- [`PinaBio-v2.0-ChatGPT.kicad_pcb`](PinaBio-v2.0-ChatGPT.kicad_pcb): PCB enrutada.
- [`PinaBio-v2.0-ChatGPT-BOM.csv`](PinaBio-v2.0-ChatGPT-BOM.csv): BOM por referencia; [`BOM agrupada`](PinaBio-v2.0-ChatGPT-BOM-grouped.csv): 93 posiciones, 54 grupos. **No es una BOM de compra JLCPCB**: faltan códigos LCSC y elegir fabricante para componentes genéricos.
- [`PinaBio-v2.0-ChatGPT-PinNets.csv`](PinaBio-v2.0-ChatGPT-PinNets.csv): conexión de cada pin numerado del esquema.
- [`ERC-H1.txt`](ERC-H1.txt) y [`DRC-H1.txt`](DRC-H1.txt): comprobaciones de esta revisión; [`PDF del esquema`](preview/PinaBio-v2.0-ChatGPT.pdf) y [`vista frontal H1`](preview/pcb-front-H1.pdf) para revisión.
- `PinaBio-ChatGPT.kicad_sym`, `PinaBio-ChatGPT.pretty`, `sym-lib-table`, `fp-lib-table` y `3dmodels`: bibliotecas locales. [Licencias](LIBRARY-LICENSE.md).

## Circuitos y conectores

| Referencia | Conexión prevista |
| --- | --- |
| J1 | USB-C 2.0 de datos y carga, dos resistencias CC de 5,1 kΩ, ESD y TVS. |
| J2 | LiPo 1S protegida con NTC de 10 kΩ: 1 `BAT_PROT`, 2 `GND`, 3 `BAT_NTC`. Verificar polaridad del cable real. |
| SW1 | DPDT físico. OFF+USB habilita carga/programación; ON+USB configura BQ24074 en standby, detiene carga y permite datos con alimentación de batería. |
| J3 | AD8232 externo: 1 `3V3_A`, 2 `GND`, 3 `OUTPUT`, 4 `LO+`, 5 `LO−`, 6 `SDN`. El jack de electrodos pertenece al módulo. |
| J4/J5/J6 | Dos hilos para GSR/tórax/abdomen. Pin 1: excitación a través de 100 kΩ; pin 2: masa. El nodo de medida entra al MCP6004 a través de otros 100 kΩ. |
| J7 | Módulo MAX30102: 1 VIN `3V3_SYS`, 2 GND, 3 SCL, 4 SDA, 5 INT. |
| J8 | Módulo MAX30205: 1 VCC `3V0_TEMP`, 2 GND, 3 SDA, 4 SCL, 5 OS, 6 A0, 7 A1, 8 A2 (los A están a masa). **Orden y número de contactos provisionales hasta comprobar el módulo físico.** |
| J9 | Depuración UART: 1 GND, 2 `3V3_SYS`, 3 TX, 4 RX; no utilizarlo como entrada de alimentación. |

El TPS63070 usa 49,9 kΩ/16,0 kΩ, al 0,1 %, para una consigna nominal de 3,295 V. El TLV75530PDBVR genera 3,0 V únicamente para J8. El AD8232 usa un divisor de 33,2 kΩ/47,5 kΩ antes del ADS122C04 dedicado al ECG. El segundo ADS122C04 recibe GSR y las dos bandas en modo de una entrada por canal; su cuarta entrada está referida a la excitación de 0,5 V y no se trata como AUX disponible. La configuración de PGA bypass, tasas y direcciones I²C se describe en la [especificación](../../docs/es/especificacion.md).

Los sensores están conectados directamente a sus etapas: **no hay relés, MOSFET ni conmutadores de corte de sensores**. Con una persona conectada, USB solo puede usarse mediante un aislador externo alimentado por el ordenador; durante OFF+carga/programación no debe haber persona conectada. No hay aislamiento galvánico en esta PCB.

## Comprobaciones efectuadas

- ERC de KiCad 9: **0 infracciones**.
- DRC de KiCad 9: **0 infracciones y 0 conexiones pendientes**.
- Cotejo de 329 pines conectados entre netlist del esquema y pads de PCB: **0 diferencias**.
- Las dos pistas TPS63070↔bobina: aproximadamente 4,7 mm cada una, sin vía. Trece tramos de `BAT_PROT`, `VBUS_RAW` y `SYS` se han ensanchado donde el DRC lo permite; las secciones cercanas a pines y vías conservan su anchura original. Se añadieron dos vías de retorno a la masa interior cerca del ESP32 y de los ADC. Hay que medir la caída de tensión a corriente real.
- Las capas interiores no contienen pistas de señal. La masa interior permanece continua y el raíl de 3,3 V usa In2.

Estas comprobaciones no validan selección de componentes, corriente, temperatura, ruido analógico, EMC ni seguridad de uso sobre el cuerpo.

## Pendiente antes de pedir a JLCPCB

1. Confirmar con los **tres módulos reales** pinout, tensión admisible, resistencias de pull-up, picos de corriente y posición de los conectores; adaptar J3/J7/J8 si difieren. J8 es especialmente provisional.
2. Auditar de forma independiente la huella local `TPS63070_RNM0015A`, orientación de todos los encapsulados, taladros, exposición térmica del BQ24074, área del conector U.FL y compatibilidad de las referencias concretas con montaje JLCPCB.
3. Medir en prototipo el consumo pico de ESP32/PPG, `3V3_SYS`, `3V0_TEMP`, arranque y transiciones ON/OFF/USB, ausencia de carga en ON+USB, temperatura y caída de tensión de pistas y cables. Validar el cable y protección de la LiPo.
4. Medir ECG, GSR, respiración y ruido de 50/60 Hz con los módulos y electrodos reales; comprobar el aislador externo en el modo ON+USB.
5. Elegir números de pieza y disponibilidad JLC/LCSC, verificar montaje, añadir fiduciales y generar Gerber, taladros y archivo de posiciones **solo después** de cerrar las comprobaciones anteriores.

Los informes ERC/DRC son útiles para detectar errores de CAD, pero no certifican un circuito para contacto humano. Por eso este directorio aún no contiene un paquete Gerber liberado para pedido.
