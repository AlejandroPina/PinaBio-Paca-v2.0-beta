# PinaBio Paca v2.0 beta — especificación de hardware `SPEC-0.7`

[Portada](../../README.md) · [Alimentación y USB](alimentacion-usb.md) · [Protocolo](protocolo.md)

**Estado:** diseño para revisión antes de capturar KiCad; no es un esquemático validado ni una orden de fabricación. Uso experimental y de biofeedback, no médico. **DEBE** expresa un requisito de diseño; *propuesto* exige comprobación de banco.

## 1. Alcance y arquitectura

PinaBio registra ECG, PPG, GSR, dos bandas de respiración, temperatura local y tensión de batería. El ESP32-S3-MINI-1U-N8 coordina dos ADS122C04, los módulos I²C y BLE; Wi‑Fi permanece desactivado. Un ADS se dedica al ECG y el segundo a GSR, tórax y abdomen. La aplicación conserva muestras crudas y calcula métricas derivadas; ninguna señal constituye diagnóstico.

```text
USB-C ─ ESD ─ BQ24074 IN/OUT ─ SYS ─ TPS63070 ─ 3V3_SYS
                   │                       ├─ ESP32-S3 / BLE / ADS122C04 ×2
LiPo 1S protegida ─┘ BAT                   ├─ isla analógica 3V3_A (0 Ω inicial)
                                              └─ TLV75530PDBVR ─ 3V0_TEMP ─ CJMCU-30205

AD8232 ─ ADS ECG (600 SPS)       MAX30102 ─ I²C + INT
GSR / tórax / abdomen ─ MCP6004 ─ ADS lento       MAX30205 ─ I²C
```

El TPS63070, en PWM forzado, genera el raíl de 3,30 V nominales (consigna 3,295 V). `3V3_A` es una isla filtrable desde `3V3_SYS`, inicialmente puenteada con 0 Ω. **No hay regulador de 2,9 V ni TCA9801.** Un segundo regulador, el TLV75530PDBVR, hace 3,0 V fijos y solo alimenta el VCC del CJMCU-30205. El resto de la placa va al raíl de 3,3 V.

## 2. Alimentación y USB

| Red | Origen y destino | Requisito |
|---|---|---|
| `BAT_PROT` | LiPo 1S protegida → BAT del BQ24074 | 3,0–4,2 V; batería con protección y NTC. |
| `VBUS_RAW` | USB-C tras ESD/fusible | Nunca a GPIO; detección solo telemétrica. |
| `SYS` | Salida del BQ24074 → TPS63070 | El BQ24074 aporta *power-path*, no 3,3 V regulados. |
| `3V3_SYS` | TPS63070. FB: 49,9 kΩ de VOUT a FB y 16,0 kΩ de FB a masa, ambas al 0,1 %. PS/SYNC a masa. | 3,295 V nominales. ESP32, ADC, PPG, lógica y la entrada del LDO. Diseñar ≥500 mA y medir picos BLE, PPG y contactos. |
| `3V3_A` | Desde 3V3_SYS mediante 0 Ω/ferrita opcional | ADS analógico, MCP6004 y AD8232. |
| `3V0_TEMP` | TLV75530PDBVR desde 3V3_SYS. 2,2 µF X7R en entrada y en salida, para conservar al menos 0,47 µF efectivos. EN unido a su entrada. | Solo el VCC del CJMCU-30205. |
| `0V5_EXC` | MCP6004 desde 56 kΩ/10 kΩ de 3V3_A | ≈0,50 V; calibrar por placa. |

USB-C es un sumidero USB 2.0: `CC1`/`CC2` llevan `Rd=5,1 kΩ` a masa, D+/D− tienen ESD de baja capacidad y van a GPIO19/GPIO20. El conector nunca recibe VBUS desde la placa. VBUS protegido llega a `IN` del BQ24074 con OFF y con ON; no hay MOSFET externo de corte. El interruptor físico fija los pines de modo del cargador y la habilitación del regulador sin depender del ESP32.

Con OFF y VBUS válido: `EN1=alto`, `EN2=bajo`, `CE=bajo` permiten carga y salida desde USB, con límite USB500 solo si la fuente lo admite. Con ON y VBUS válido: `EN1=EN2=alto` ponen el BQ24074 en *standby/USB suspend*: `Q1` interno (IN→OUT) abierto, `Q2` (BAT→OUT) cerrado y carga detenida. `CE=alto` añade inhibición de carga, pero no basta por sí solo para evitar que USB alimente `OUT`. Los niveles de `EN1`, `EN2` y `CE` deben provenir del interruptor y VBUS, seguir definidos sin batería y no depender de firmware. `ILIM`, `ISET` e `ITERM` se calculan para la fuente, LiPo y carga prevista de ≈300 mA; `TS` va al NTC.

La lógica derivada de VBUS debe respetar en cada pin `EN1`, `EN2` y `CE`: bajo **0–0,4 V**, alto **1,4–6 V**, máximo absoluto **−0,3 a 7 V**, incluso durante transitorios. El esquema debe incluir la limitación/protección necesaria y margen respecto a 6 V en operación; los 7 V no son una consigna. La tolerancia de `IN` a una tensión mayor no se extiende a estos pines. Véase [alimentación y USB](alimentacion-usb.md).

La habilitación del TPS63070 debe obedecer por hardware a `(OFF y VBUS válido) o (ON y batería válida)`. Así OFF+USB admite programación sin batería, mientras ON+USB sin batería no arranca. El esquema debe definir la detección de batería válida y secuenciar la apertura de contactos corporales antes de pasar de alimentación por batería a USB al mover ON→OFF. [Hoja de datos BQ24074 de TI](https://www.ti.com/lit/ds/symlink/bq24074.pdf), tabla 7-2 y apartado 9.3.2.

| Interruptor | USB | Modo BQ24074 | Fuente de 3V3 | Carga | USB datos/programación | Conexiones corporales |
|---|---:|---|---|---|---|---|
| OFF | no | entrada inválida | ninguna | no | no | abiertas |
| OFF | sí | USB500, si fuente válida | VBUS vía BQ24074 | sí | sí | abiertas |
| ON | no | entrada inválida | LiPo | no | no | armables |
| ON | sí | standby, `EN1=EN2=alto` | LiPo | no | sí | armables solo con aislador USB externo |

Con OFF y USB, el ESP puede arrancar para programarse; al retirar USB queda apagado. Con ON y USB, D+/D− continúan funcionando y `OUT` se alimenta de la batería, aunque VBUS permanece en `IN` del cargador. Para medir con USB conectado se requiere un aislador externo alimentado desde el ordenador; la masa del conector de placa no se corta, pues el retorno de datos forma parte de ese aislamiento externo. Un cable USB normal no debe usarse sobre una persona.

## 3. Barrera corporal

Cada conductor de `J_ECG`, `J_PPG`, `J_TEMP`, `J_RESP_T` y `J_RESP_A`, incluida masa y alimentación, cruza contactos normalmente abiertos. `BODY_ALLOW` requiere ON, alimentación válida, autocomprobación y confirmación de los contactos. Pérdida de alimentación abre la barrera. El firmware solo puede solicitar armado: no debe poder cerrar contactos si el realimentado físico no coincide ni sustituir la lógica de seguridad.

No se admiten rutas alternativas por blindajes, ESD, *pull-ups*, diodos de GPIO, fijaciones o puntos de prueba. El diseño no afirma aislamiento galvánico interno ni seguridad clínica. Con USB durante una medición, la seguridad depende del aislador externo y del procedimiento de uso, no de detectar VBUS.

## 4. Módulos y adquisición

| Conector / señal | Interfaz | Requisitos eléctricos |
|---|---|---|
| AD8232 externo | 3V3, GND, OUTPUT, LO+, LO−, SDN | Verificar breakout a 3,3 V. ADS ECG: referencia interna 2,048 V, PGA bypass, ganancia 1, 600 SPS. Divisor: 33,2 kΩ desde OUTPUT y 47,5 kΩ a masa, al 1 %. A 3,30 V de salida plena el ADS ve 1,94 V; a 3,40 V ve 2,00 V, por debajo de 2,048 V. No usar 20,0/40,2 kΩ. La medida de la excursión real comprueba que el módulo no recorta antes del divisor. Si OUTPUT ya sale recortada, el divisor no lo corrige. |
| MAX30102/GY-30102 | 3V3, GND, SCL, SDA, INT | Verificar reguladores, niveles, *pull-ups*, LED y consumo del módulo real. PPG inicialmente 200 pares/s. |
| CJMCU-30205 | 3V0_TEMP, GND, SDA, SCL, OS, A0, A1, A2 | VCC del módulo va directo al chip: no lleva regulador. A0, A1 y A2 a masa fijan 0x48. Las pull-up del módulo van a su VCC. |
| GSR | Dos electrodos | `0V5_EXC → 100 kΩ → sensor → retorno`; seguidor MCP6004 y ADS lento. Corriente de cortocircuito ≈5 µA. |
| Bandas tórax/abdomen | Dos hilos por banda | Mismo frontal que GSR, con resistencia fija de 100 kΩ revisable tras medir bandas reales. |

Los IDAC de los ADS permanecen apagados y no se conectan a rutas corporales. GSR y bandas se muestrean inicialmente a 20 SPS por canal; se publican estados OPEN, SHORT, OUT_OF_RANGE y UNCALIBRATED. Las bandas producen resistencia y curva respiratoria, no volumen pulmonar.

I²C de ADC (GPIO4/5) opera a 400 kHz con ADS `0x40` y `0x41`; DRDY entra por GPIO6/7. I²C de módulos (GPIO8/9) empieza a 100 kHz; INT PPG usa GPIO10. `BAT_SENSE` (GPIO1) usa divisor 1 MΩ/330 kΩ conmutado, filtro y calibración. GPIO0 queda reservado para BOOT; D−/D+ son GPIO19/20.

## 5. Verificación obligatoria

1. Fotografiar y medir cada breakout: pinout, reguladores, *pull-ups*, consumo y dimensiones.
2. Ensayar los cuatro estados USB/interruptor, incluso sin batería: con ON y USB, `OUT` sigue a BAT y la corriente de carga es nula; sin batería, D+/D− y VBUS no pueden elevar 3V3. Medir con osciloscopio `EN1`, `EN2` y `CE` durante los estados y transiciones, y comprobar sus límites de tensión y que los contactos corporales se abren antes de que USB pueda alimentar el sistema.
3. Medir 3V3 en el ESP y 3V0 en el VCC del CJMCU-30205, rizado, picos BLE/PPG y carga del BQ24074. En el módulo de pulso, con el LED encendido y el cable puesto, VIN no debe bajar de 3,1 V.
4. Confirmar apertura de cada conductor corporal, masa incluida, con firmware fallado o GPIO atascado.
5. Demostrar limitación GSR ante corto y ausencia de bypass de los 100 kΩ.
6. Medir excursión AD8232, saturación ADS, ruido 50/60 Hz, respuesta de bandas y buses con cables reales.
7. Validar aislamiento externo y datos USB durante adquisición antes de permitir ese modo de uso.

Antes de fabricar se requieren esquemático KiCad, ERC/DRC limpios, BOM/huellas verificadas y revisión independiente de las rutas al cuerpo.
