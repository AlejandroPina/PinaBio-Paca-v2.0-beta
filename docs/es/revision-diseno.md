# Revisión de diseño — 30 de septiembre de 2026

La revisión `SPEC-0.6` mantiene la arquitectura de `SPEC-0.5` y añade los límites de tensión y ensayos de `EN1`, `EN2` y `CE` del BQ24074.

1. El TPS63070 queda a 3,295 V (49,9 kΩ / 16,0 kΩ, 0,1 %, PWM forzado). Un TLV75530PDBVR hace 3,0 V solo para el CJMCU-30205, cuyo VCC entra directo al chip, con 2,2 µF X7R en entrada y salida. No hay raíl de 2,9 V ni TCA9801.
2. OFF permite carga y programación desde USB con conexiones corporales abiertas.
3. ON con USB pone `EN1=EN2=alto` y `CE=alto`: el BQ24074 abre internamente IN→OUT, mantiene BAT→OUT, detiene la carga y conserva D+/D− para datos/programación. VBUS permanece en `IN`; la placa se alimenta de batería.
4. VBUS ya no abre automáticamente la barrera: la adquisición con USB solo se admite usando un aislador externo alimentado desde el host. La placa informa presencia USB, pero no puede certificar el aislador.
5. El divisor del ECG es 33,2 kΩ desde OUTPUT y 47,5 kΩ a masa, al 1 %. A 3,40 V de salida plena el ADS ve 2,00 V, por debajo de 2,048 V. La medida comprueba que el módulo no recorta antes del divisor.
6. GSR y las bandas conservan excitación ≈0,50 V y 100 kΩ físicamente en serie, con corriente de corto ≈5 µA.
7. El interruptor físico determina los niveles de `EN1`, `EN2`, `CE` y la habilitación del TPS63070, sin firmware y aun sin batería. OFF+USB debe poder programar; ON+USB sin batería no debe arrancar.
8. `EN1`, `EN2` y `CE` tienen alto funcional de 1,4–6 V, bajo de 0–0,4 V y máximo absoluto de −0,3 a 7 V. El esquema debe proteger estas entradas frente a VBUS y sus transitorios; 7 V no es un valor de operación.

Quedan pendientes para el esquema y prototipo: polarización y secuencia de los pines de modo del BQ24074, apertura de los contactos corporales antes de pasar a alimentación USB al mover ON→OFF, presupuesto de corriente de breakouts/relés, compatibilidad real de módulos y pruebas de aislamiento externo. Ningún documento autoriza fabricar hasta superar los ensayos listados en `especificacion.md`.
