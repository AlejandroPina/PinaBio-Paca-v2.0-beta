# Alimentación y USB — revisión `PWR-0.7`

[Portada](../../README.md) · [Especificación](especificacion.md)

Hay un USB-C, una LiPo 1S protegida, un BQ24074 con *power-path* y un TPS63070 a 3,295 V y un TLV75530PDBVR a 3,0 V solo para el CJMCU-30205. El interruptor físico gobierna el modo del BQ24074 y la habilitación del regulador; el firmware no decide si se carga la batería o de dónde sale la energía del sistema.

## Funcionamiento

Con **OFF y USB**, `EN1=alto`, `EN2=bajo` y `CE=bajo` seleccionan el modo USB500 del BQ24074. Su entrada `IN` alimenta `OUT` y carga la LiPo; el TPS63070 puede alimentar el ESP32 para programarlo. Los sensores no se desconectan automáticamente: antes de cargar o programar con USB directo se retiran los sensores de la persona. El límite de 500 mA solo debe seleccionarse cuando la fuente USB lo permita; la carga objetivo inicial es de aproximadamente 300 mA y se debe verificar el consumo simultáneo durante la programación.

Con **ON y USB**, `EN1=EN2=alto` seleccionan *standby/USB suspend*. Según la hoja de datos del BQ24074, el FET interno `Q1` entre `IN` y `OUT` queda abierto y `Q2` entre `BAT` y `OUT` queda cerrado: la LiPo alimenta la placa y no se carga. `CE=alto` añade una inhibición de carga, pero no sustituye `EN1=EN2=alto`, porque `CE` por sí solo deja activa la salida alimentada desde USB. VBUS sigue presente en `IN`; la afirmación «solo batería» se refiere a la alimentación de `OUT` y de la placa, no a que el cargador quede físicamente sin tensión. D+/D− permiten programación y datos.

Sin USB, `IN` no es válido y `OUT` recibe energía de la batería. ON habilita el TPS63070; OFF lo mantiene apagado. Para adquirir con USB y una persona conectada es obligatorio un aislador externo que separe datos, masa y alimentación del ordenador y que proporcione el VBUS necesario del lado de la placa.

| Interruptor | USB | `EN1/EN2/CE` con VBUS válido | Origen de `OUT` | Carga | ESP32 | Uso con persona |
|---|---|---|---|---|---|---|
| OFF | no | bajos por polarización; entrada inválida | batería, sin carga del sistema | no | apagado | sin adquisición |
| OFF | sí | alto/bajo/bajo | USB | sí | encendido para mantenimiento | sin persona conectada |
| ON | no | entrada inválida | batería | no | encendido | adquisición con batería |
| ON | sí | alto/alto/alto | batería | no | encendido, USB datos | solo con aislador externo |

## Implementación obligatoria

- VBUS, después de protección de entrada, llega a `IN` del BQ24074 en ambas posiciones. **No se monta el MOSFET de corte de VBUS.** La entrada `IN` y `OUT` deben tener los condensadores indicados por TI.
- `EN1` debe estar alto cuando VBUS es válido. `EN2` y `CE` deben estar altos con **ON y VBUS**, y bajos con **OFF y VBUS**. El interruptor físico y la polarización de estas redes deben imponer los estados sin ESP32 ni batería; ningún pin de control puede quedar flotante. Los niveles y la secuencia se verifican también durante la inserción de USB y el cambio de posición.
- Para `EN1`, `EN2` y `CE`, TI especifica nivel alto de **1,4–6 V**, nivel bajo de **0–0,4 V** y máximo absoluto de **−0,3 a 7 V**. Los 7 V son un límite de daño, no una consigna de diseño. La red que obtenga estas señales de VBUS debe limitar su tensión durante funcionamiento normal, inserción y sobretensiones previsibles, con margen respecto a 6 V; no se conectará VBUS directamente sin demostrar que esos límites se cumplen. El pin `IN` admite una tensión máxima absoluta distinta y mayor, que no protege los pines lógicos.
- Con **ON, USB y batería ausente**, `EN1=EN2=alto` debe impedir que `OUT` encienda la placa desde USB. El regulador debe permanecer apagado si no hay batería válida. Con **OFF, USB y batería ausente**, el regulador puede arrancar para programación.
- `ILIM`, `ISET`, `ITERM` y `TS` se dimensionan según hoja de datos, fuente USB, NTC y LiPo reales. `TMR` lleva 46,4 kΩ al 1 % a masa. El BQ24074 no tiene pin `SYSOFF` ni sustituye la protección de la celda.
- No se montan relés ni conmutadores de corte en los conectores de sensores. OFF+USB puede alimentar esos conectores desde VBUS; por eso la carga y programación con USB directo se hacen sin persona conectada. ON+USB con persona exige aislador externo alimentado desde el host.
- TPS63070 en PWM forzado. Divisor de FB: 49,9 kΩ de VOUT a FB y 16,0 kΩ de FB a masa, al 0,1 %. Consigna 3,295 V. PS/SYNC a masa. Los dos nodos del inductor van en la capa superior, sin vía, a 0,40 mm en todo el tramo. El TLV75530PDBVR, con 2,2 µF X7R 0805 a la entrada y 2,2 µF X7R 0805 a la salida, hace 3,0 V solo para el VCC del CJMCU-30205. Esos condensadores dejan al menos 0,47 µF efectivos.
- En la implementación ChatGPT, R39 (10 kΩ, 1 %, YAGEO RC0603FR-0710KL) está en serie y junto al pin EN del TPS63070; R12 (100 kΩ a masa) queda del lado del interruptor para evitar un divisor permanente. L1 es Coilcraft XAL4020-152MEC, 1,5 µH, con la misma huella. J9 entrega BAT+ a un medidor de pocas decenas de mA solo cuando 3V3_SYS está activo: Q4 BSS84 de lado alto, Q5 BSS138 a masa y 1 MΩ entre puerta y fuente de Q4. R3 continúa como puente de 0 Ω en VBUS; no es un fusible.
- La isla analógica empieza con 0 Ω y se decide si lleva ferrita tras medir ruido. La masa analógica y la masa digital se unen en un solo punto, corto y ancho, junto a ese puente y a los ADS, para que alimentación y retorno coincidan. No hay más uniones.
- USB-C usa un USBLC6-2SC6 en SOT-23-6 y dos resistencias `Rd` de 5,1 kΩ en CC1/CC2. Entre el protector y el ESP32, D− (GPIO19) y D+ (GPIO20) llevan 22 Ω en serie. D+/D− y la detección de VBUS no deben realimentar el ESP32 apagado. El aislador no está soldado a la placa y debe generar su VBUS aislado desde el host. GPIO0 lleva 10 kΩ a `3V3_SYS`; el pulsador de BOOT lo pone a masa.

## Ensayos

Medir tensión y corriente en `IN`, `OUT`, `BAT`, `3V3_SYS` y USB durante los cuatro estados. Registrar con osciloscopio los niveles de `EN1`, `EN2` y `CE` en estado estable y durante inserción, retirada y perturbaciones de VBUS y cambios del interruptor; verificar tanto los umbrales funcionales como los límites absolutos. Con ON+USB, `OUT` debe seguir a la batería, la corriente de carga debe ser nula y quitar la batería no debe arrancar la placa desde VBUS o D+/D−. Con OFF+USB, verificar carga y programación incluso sin batería y documentar la tensión presente en los conectores de sensores. Medir aislamiento del cable externo, rizado de 3,3 V, consumo de módulos y temperatura del cargador. La adquisición con una persona y USB se ensaya solo tras verificar el aislador externo.

[BQ24074, hoja de datos de TI](https://www.ti.com/lit/ds/symlink/bq24074.pdf), tabla 7-2 y apartado 9.3.2.
