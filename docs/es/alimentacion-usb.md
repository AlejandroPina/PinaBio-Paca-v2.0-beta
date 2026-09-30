# Alimentación y USB — revisión `PWR-0.6`

[Portada](../../README.md) · [Especificación](especificacion.md)

Hay un USB-C, una LiPo 1S protegida, un BQ24074 con *power-path* y un TPS63070 que genera el único raíl nominal de 3,3 V. El interruptor físico gobierna el modo del BQ24074 y la habilitación del regulador; el firmware no decide si se carga la batería o de dónde sale la energía del sistema.

## Funcionamiento

Con **OFF y USB**, `EN1=alto`, `EN2=bajo` y `CE=bajo` seleccionan el modo USB500 del BQ24074. Su entrada `IN` alimenta `OUT` y carga la LiPo; el TPS63070 puede alimentar el ESP32 para programarlo. Todas las vías hacia el cuerpo permanecen abiertas. El límite de 500 mA solo debe seleccionarse cuando la fuente USB lo permita; la carga objetivo inicial es de aproximadamente 300 mA y se debe verificar el consumo simultáneo durante la programación.

Con **ON y USB**, `EN1=EN2=alto` seleccionan *standby/USB suspend*. Según la hoja de datos del BQ24074, el FET interno `Q1` entre `IN` y `OUT` queda abierto y `Q2` entre `BAT` y `OUT` queda cerrado: la LiPo alimenta la placa y no se carga. `CE=alto` añade una inhibición de carga, pero no sustituye `EN1=EN2=alto`, porque `CE` por sí solo deja activa la salida alimentada desde USB. VBUS sigue presente en `IN`; la afirmación «solo batería» se refiere a la alimentación de `OUT` y de la placa, no a que el cargador quede físicamente sin tensión. D+/D− permiten programación y datos.

Sin USB, `IN` no es válido y `OUT` recibe energía de la batería. ON habilita el TPS63070; OFF lo mantiene apagado. Para adquirir con USB y una persona conectada es obligatorio un aislador externo que separe datos, masa y alimentación del ordenador y que proporcione el VBUS necesario del lado de la placa.

| Interruptor | USB | `EN1/EN2/CE` con VBUS válido | Origen de `OUT` | Carga | ESP32 | Conexiones corporales |
|---|---|---|---|---|---|---|
| OFF | no | bajos por polarización; entrada inválida | batería, sin carga del sistema | no | apagado | abiertas |
| OFF | sí | alto/bajo/bajo | USB | sí | encendido para mantenimiento | abiertas |
| ON | no | entrada inválida | batería | no | encendido | armables |
| ON | sí | alto/alto/alto | batería | no | encendido, USB datos | armables solo con aislador externo |

## Implementación obligatoria

- VBUS, después de protección de entrada, llega a `IN` del BQ24074 en ambas posiciones. **No se monta el MOSFET de corte de VBUS.** La entrada `IN` y `OUT` deben tener los condensadores indicados por TI.
- `EN1` debe estar alto cuando VBUS es válido. `EN2` y `CE` deben estar altos con **ON y VBUS**, y bajos con **OFF y VBUS**. El interruptor físico y la polarización de estas redes deben imponer los estados sin ESP32 ni batería; ningún pin de control puede quedar flotante. Los niveles y la secuencia se verifican también durante la inserción de USB y el cambio de posición.
- Para `EN1`, `EN2` y `CE`, TI especifica nivel alto de **1,4–6 V**, nivel bajo de **0–0,4 V** y máximo absoluto de **−0,3 a 7 V**. Los 7 V son un límite de daño, no una consigna de diseño. La red que obtenga estas señales de VBUS debe limitar su tensión durante funcionamiento normal, inserción y sobretensiones previsibles, con margen respecto a 6 V; no se conectará VBUS directamente sin demostrar que esos límites se cumplen. El pin `IN` admite una tensión máxima absoluta distinta y mayor, que no protege los pines lógicos.
- Con **ON, USB y batería ausente**, `EN1=EN2=alto` debe impedir que `OUT` encienda la placa desde USB. El regulador debe permanecer apagado si no hay batería válida. Con **OFF, USB y batería ausente**, el regulador puede arrancar para programación.
- `ILIM`, `ISET`, `ITERM`, `TMR` y `TS` se dimensionan según hoja de datos, fuente USB, NTC y LiPo reales. El BQ24074 no tiene pin `SYSOFF` ni sustituye la protección de la celda.
- La lógica de los contactos corporales debe abrir todas las vías antes de que el BQ24074 pueda pasar de batería a USB al mover ON→OFF. El diseño de temporización y su ensayo quedan pendientes del esquema; no basta con confiar en firmware.
- TPS63070 en PWM forzado, un único 3,3 V. Verificar la consigna en el pin del MAX30205 y bajarla si supera 3,3 V.
- La isla analógica empieza con 0 Ω y se decide si lleva ferrita tras medir ruido.
- USB-C usa ESD y dos resistencias `Rd` de 5,1 kΩ en CC1/CC2. D+/D− y la detección de VBUS no deben realimentar el ESP32 apagado. El aislador no está soldado a la placa y debe generar su VBUS aislado desde el host.

## Ensayos

Medir tensión y corriente en `IN`, `OUT`, `BAT`, `3V3_SYS` y USB durante los cuatro estados. Registrar con osciloscopio los niveles de `EN1`, `EN2` y `CE` en estado estable y durante inserción, retirada y perturbaciones de VBUS y cambios del interruptor; verificar tanto los umbrales funcionales como los límites absolutos. Con ON+USB, `OUT` debe seguir a la batería, la corriente de carga debe ser nula y quitar la batería no debe arrancar la placa desde VBUS o D+/D−. Con OFF+USB, verificar carga y programación incluso sin batería. Comprobar que las vías corporales se abren antes de activar alimentación USB del sistema. Medir aislamiento del cable externo, rizado de 3,3 V, consumo de módulos y temperatura del cargador. Ninguna sesión corporal se aprueba antes de documentar estos ensayos y el ensayo de contactos.

[BQ24074, hoja de datos de TI](https://www.ti.com/lit/ds/symlink/bq24074.pdf), tabla 7-2 y apartado 9.3.2.
