# PinaBio Paca v2.0 beta — especificación de hardware `SPEC-0.4`

[Portada](../../README.md) · [Alimentación y USB](alimentacion-usb.md) · [Protocolo](protocolo.md)

**Estado:** diseño para revisión antes de capturar KiCad; no es un esquemático validado ni una orden de fabricación. Uso experimental y de biofeedback, no médico. **DEBE** expresa un requisito de diseño; *propuesto* exige comprobación de banco.

## 1. Alcance y arquitectura

PinaBio registra ECG, PPG, GSR, dos bandas de respiración, temperatura local y tensión de batería. El ESP32-S3-MINI-1U-N8 coordina dos ADS122C04, los módulos I²C y BLE; Wi‑Fi permanece desactivado. Un ADS se dedica al ECG y el segundo a GSR, tórax y abdomen. La aplicación conserva muestras crudas y calcula métricas derivadas; ninguna señal constituye diagnóstico.

```text
USB-C ─ ESD ─ MOSFET VBUS ─ BQ24074 ─ SYS ─ TPS63070 ─ 3V3_SYS
                         │                         ├─ ESP32-S3 / BLE / ADS122C04 ×2
LiPo 1S protegida ───────┘                         └─ isla analógica 3V3_A (0 Ω inicial)

AD8232 ─ ADS ECG (600 SPS)       MAX30102 ─ I²C + INT
GSR / tórax / abdomen ─ MCP6004 ─ ADS lento       MAX30205 ─ I²C
```

Hay un solo raíl nominal de 3,3 V. `3V3_A` es una isla filtrable desde `3V3_SYS`, inicialmente puenteada con 0 Ω; **no hay regulador de 2,9 V ni TCA9801**. El TPS63070 funciona en PWM forzado. La tensión medida en el pin del MAX30205 debe quedar entre 3,0 y 3,3 V; si la tolerancia la rebasa se baja la consigna del convertidor, sin bajar de 3,0 V.

## 2. Alimentación y USB

| Red | Origen y destino | Requisito |
|---|---|---|
| `BAT_PROT` | LiPo 1S protegida → BAT del BQ24074 | 3,0–4,2 V; batería con protección y NTC. |
| `VBUS_RAW` | USB-C tras ESD/fusible | Nunca a GPIO; detección solo telemétrica. |
| `SYS` | Salida del BQ24074 → TPS63070 | El BQ24074 aporta *power-path*, no 3,3 V regulados. |
| `3V3_SYS` | TPS63070 | ESP32, ADC digitales, módulos y lógica. Diseñar ≥500 mA y medir picos BLE, PPG y contactos. |
| `3V3_A` | Desde 3V3_SYS mediante 0 Ω/ferrita opcional | ADS analógico, MCP6004 y AD8232. |
| `0V5_EXC` | MCP6004 desde 56 kΩ/10 kΩ de 3V3_A | ≈0,50 V; calibrar por placa. |

USB-C es un sumidero USB 2.0: `CC1`/`CC2` llevan `Rd=5,1 kΩ` a masa, D+/D− tienen ESD de baja capacidad y van a GPIO19/GPIO20. El conector nunca recibe VBUS desde la placa. El interruptor solo gobierna el MOSFET de VBUS, no la corriente de carga. Con OFF, VBUS alcanza el BQ24074; con ON queda bloqueado. El MOSFET debe impedir conducción por su diodo interno y la entrada del BQ24074 queda definida por 100 kΩ a masa al bloquearse.

`EN1` alto y `EN2` a masa seleccionan límite USB de 500 mA; `CE` a masa, `ILIM` e `ISET` se calculan para una carga prevista de ≈300 mA y `TS` se conecta al NTC. Ninguno de esos pines se deja flotante.

| Interruptor | USB | Fuente de 3V3 | Carga | USB datos/programación | Conexiones corporales |
|---|---:|---|---|---|---|
| OFF | no | ninguna | no | no | abiertas |
| OFF | sí | VBUS vía BQ24074 | sí | sí | abiertas |
| ON | no | LiPo | no | no | armables |
| ON | sí | LiPo | no | sí | armables solo con aislador USB externo |

Con OFF y USB, el ESP puede arrancar para programarse; al retirar USB queda apagado. Con ON y USB, D+/D− continúan funcionando pero VBUS no carga ni alimenta la placa. Para medir con USB conectado se requiere un aislador externo alimentado desde el ordenador; la masa del conector de placa no se corta, pues el retorno de datos forma parte de ese aislamiento externo. Un cable USB normal no debe usarse sobre una persona.

## 3. Barrera corporal

Cada conductor de `J_ECG`, `J_PPG`, `J_TEMP`, `J_RESP_T` y `J_RESP_A`, incluida masa y alimentación, cruza contactos normalmente abiertos. `BODY_ALLOW` requiere ON, alimentación válida, autocomprobación y confirmación de los contactos. Pérdida de alimentación abre la barrera. El firmware solo puede solicitar armado: no debe poder cerrar contactos si el realimentado físico no coincide ni sustituir la lógica de seguridad.

No se admiten rutas alternativas por blindajes, ESD, *pull-ups*, diodos de GPIO, fijaciones o puntos de prueba. El diseño no afirma aislamiento galvánico interno ni seguridad clínica. Con USB durante una medición, la seguridad depende del aislador externo y del procedimiento de uso, no de detectar VBUS.

## 4. Módulos y adquisición

| Conector / señal | Interfaz | Requisitos eléctricos |
|---|---|---|
| AD8232 externo | 3V3, GND, OUTPUT, LO+, LO−, SDN | Verificar breakout a 3,3 V. ADS ECG: referencia interna 2,048 V, PGA bypass, ganancia 1, 600 SPS. El divisor OUTPUT→ADS se calcula tras medir su excursión a 3,3 V; 20,0/40,2 kΩ no se reutiliza sin esa prueba. |
| MAX30102/GY-30102 | 3V3, GND, SCL, SDA, INT | Verificar reguladores, niveles, *pull-ups*, LED y consumo del módulo real. PPG inicialmente 200 pares/s. |
| MAX30205 | 3V3, GND, SDA, SCL, dirección 0x48 | Confirmar *pull-ups* ≤3,3 V y exactitud térmica local. |
| GSR | Dos electrodos | `0V5_EXC → 100 kΩ → sensor → retorno`; seguidor MCP6004 y ADS lento. Corriente de cortocircuito ≈5 µA. |
| Bandas tórax/abdomen | Dos hilos por banda | Mismo frontal que GSR, con resistencia fija de 100 kΩ revisable tras medir bandas reales. |

Los IDAC de los ADS permanecen apagados y no se conectan a rutas corporales. GSR y bandas se muestrean inicialmente a 20 SPS por canal; se publican estados OPEN, SHORT, OUT_OF_RANGE y UNCALIBRATED. Las bandas producen resistencia y curva respiratoria, no volumen pulmonar.

I²C de ADC (GPIO4/5) opera a 400 kHz con ADS `0x40` y `0x41`; DRDY entra por GPIO6/7. I²C de módulos (GPIO8/9) empieza a 100 kHz; INT PPG usa GPIO10. `BAT_SENSE` (GPIO1) usa divisor 1 MΩ/330 kΩ conmutado, filtro y calibración. GPIO0 queda reservado para BOOT; D−/D+ son GPIO19/20.

## 5. Verificación obligatoria

1. Fotografiar y medir cada breakout: pinout, reguladores, *pull-ups*, consumo y dimensiones.
2. Ensayar los cuatro estados USB/interruptor, incluso sin batería: D+/D− y VBUS no pueden elevar 3V3 cuando ON y la batería falta.
3. Medir 3V3 en ESP y MAX30205, rizado, picos BLE/PPG y carga del BQ24074.
4. Confirmar apertura de cada conductor corporal, masa incluida, con firmware fallado o GPIO atascado.
5. Demostrar limitación GSR ante corto y ausencia de bypass de los 100 kΩ.
6. Medir excursión AD8232, saturación ADS, ruido 50/60 Hz, respuesta de bandas y buses con cables reales.
7. Validar aislamiento externo y datos USB durante adquisición antes de permitir ese modo de uso.

Antes de fabricar se requieren esquemático KiCad, ERC/DRC limpios, BOM/huellas verificadas y revisión independiente de las rutas al cuerpo.
