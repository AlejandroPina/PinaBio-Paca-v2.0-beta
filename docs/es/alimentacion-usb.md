# Alimentación y USB — revisión `PWR-0.4`

[Portada](../../README.md) · [Especificación](especificacion.md)

Este documento sustituye el árbol de dos raíles y el bloqueo automático por VBUS de `SPEC-0.3`. Hay un USB-C y una LiPo 1S protegida.

## Funcionamiento

Con el interruptor **OFF**, un MOSFET de lado alto deja pasar VBUS hacia el BQ24074. El cargador alimenta su salida SYS, se carga la LiPo y el TPS63070 genera 3,3 V: el ESP32 puede enumerar y programarse. Todas las vías hacia el cuerpo permanecen abiertas.

Con el interruptor **ON**, el MOSFET bloquea VBUS hacia el BQ24074. La placa se alimenta de la LiPo; D+/D− siguen conectados al ESP32 y permiten programación o datos USB, pero no hay carga ni alimentación desde el puerto. Para usar USB mientras los sensores están sobre una persona es obligatorio un aislador externo de datos y alimentación, alimentado por el ordenador.

| Estado | Carga | ESP | Datos USB | Cuerpo |
|---|---|---|---|---|
| OFF, sin USB | no | apagado | no | abierto |
| OFF, USB | sí | encendido | sí | abierto |
| ON, sin USB | no | LiPo | no | armable |
| ON, USB | no | LiPo | sí | armable únicamente con aislador externo |

## Implementación obligatoria

- El MOSFET ha de bloquear tanto el canal como el diodo intrínseco en ON. Los 100 kΩ a masa mantienen estable la entrada del BQ24074 sin simular un adaptador válido.
- `EN1=alto`, `EN2=masa`, `CE=masa`; `ILIM`, `ISET` y `TS` se montan según hoja de datos, fuente USB, NTC y LiPo reales. El BQ24074 no incluye SYSOFF y no sustituye la protección de la celda.
- TPS63070 en PWM forzado, un único 3,3 V. Verificar la consigna en el pin del MAX30205 y bajarla si supera 3,3 V.
- No hay TPS7A20 de 2,9 V. La ferrita hacia analógica se sustituye inicialmente por 0 Ω y se decide en ensayo.
- USB-C usa ESD, Rd de 5,1 kΩ en CC1/CC2 y no entrega VBUS al conector.
- El aislador no está soldado a la placa. Debe generar su 5 V aislado desde el lado host; uno que exija energía de la placa no es adecuado con el aparato encendido.

## Ensayos

Medir carga y SYS con OFF; confirmar con ON que no entra corriente de carga; confirmar OFF/USB sin batería permite programación; y confirmar ON/USB sin batería no arranca por VBUS ni por D+/D−. Medir aislamiento del cable externo, rizado 3,3 V, consumo de módulos y la temperatura del cargador. No se permite una sesión corporal hasta que estos ensayos y el ensayo de contactos estén documentados.
