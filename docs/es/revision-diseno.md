# Revisión de diseño — 30 de septiembre de 2026

La revisión `SPEC-0.5` mantiene la arquitectura de `SPEC-0.4` y sustituye el MOSFET externo de VBUS por el modo standby previsto por TI para el BQ24074.

1. Un único raíl de 3,3 V sustituye `2V9_A` y el TPS7A20; el TCA9801 deja de ser necesario.
2. OFF permite carga y programación desde USB con conexiones corporales abiertas.
3. ON con USB pone `EN1=EN2=alto` y `CE=alto`: el BQ24074 abre internamente IN→OUT, mantiene BAT→OUT, detiene la carga y conserva D+/D− para datos/programación. VBUS permanece en `IN`; la placa se alimenta de batería.
4. VBUS ya no abre automáticamente la barrera: la adquisición con USB solo se admite usando un aislador externo alimentado desde el host. La placa informa presencia USB, pero no puede certificar el aislador.
5. El divisor del ECG se recalcula tras medir el AD8232 alimentado a 3,3 V para no exceder la referencia ADS de 2,048 V.
6. GSR y las bandas conservan excitación ≈0,50 V y 100 kΩ físicamente en serie, con corriente de corto ≈5 µA.
7. El interruptor físico determina los niveles de `EN1`, `EN2`, `CE` y la habilitación del TPS63070, sin firmware y aun sin batería. OFF+USB debe poder programar; ON+USB sin batería no debe arrancar.

Quedan pendientes para el esquema y prototipo: polarización y secuencia de los pines de modo del BQ24074, apertura de los contactos corporales antes de pasar a alimentación USB al mover ON→OFF, presupuesto de corriente de breakouts/relés, compatibilidad real de módulos y pruebas de aislamiento externo. Ningún documento autoriza fabricar hasta superar los ensayos listados en `especificacion.md`.
