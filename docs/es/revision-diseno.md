# Revisión de diseño — 1 de octubre de 2026

La revisión `SPEC-0.9` / `PWR-0.7` mantiene las decisiones de `SPEC-0.8` y añade el USB, el temporizador del cargador, la antena U.FL y la masa partida. Siguen vigentes los límites de tensión y ensayos de `EN1`, `EN2` y `CE` del BQ24074.

1. El TPS63070 queda a 3,295 V (49,9 kΩ / 16,0 kΩ, 0,1 %, PWM forzado). Un TLV75530PDBVR hace 3,0 V solo para el CJMCU-30205, cuyo VCC entra directo al chip, con 2,2 µF X7R en entrada y salida. No hay raíl de 2,9 V ni TCA9801.
2. OFF permite carga y programación desde USB. Los conectores de sensores no se cortan; se retiran de la persona antes de usar USB directo.
3. ON con USB pone `EN1=EN2=alto` y `CE=alto`: el BQ24074 abre internamente IN→OUT, mantiene BAT→OUT, detiene la carga y conserva D+/D− para datos/programación. VBUS permanece en `IN`; la placa se alimenta de batería.
4. No hay barrera de contactos ni corte automático por VBUS: la adquisición con USB y una persona solo se admite usando un aislador externo alimentado desde el host. La placa informa presencia USB, pero no puede certificar el aislador.
5. El divisor del ECG es 33,2 kΩ desde OUTPUT y 47,5 kΩ a masa, al 1 %. A 3,40 V de salida plena el ADS ve 2,00 V, por debajo de 2,048 V. La medida comprueba que el módulo no recorta antes del divisor.
6. GSR y las bandas conservan excitación ≈0,50 V y 100 kΩ físicamente en serie, con corriente de corto ≈5 µA.
7. El interruptor físico determina los niveles de `EN1`, `EN2`, `CE` y la habilitación del TPS63070, sin firmware y aun sin batería. OFF+USB debe poder programar; ON+USB sin batería no debe arrancar.
8. `EN1`, `EN2` y `CE` tienen alto funcional de 1,4–6 V, bajo de 0–0,4 V y máximo absoluto de −0,3 a 7 V. El esquema debe proteger estas entradas frente a VBUS y sus transitorios; 7 V no es un valor de operación.
9. D− (GPIO19) y D+ (GPIO20) llevan 22 Ω en serie entre un USBLC6-2SC6 (SOT-23-6) y el ESP32. GPIO0 lleva 10 kΩ a `3V3_SYS` y el pulsador de BOOT lo pone a masa. `TMR` del BQ24074 lleva 46,4 kΩ al 1 % a masa. Los 2,2 µF del TLV75530 son X7R 0805.
10. El ESP32-S3-MINI-1U lleva conector U.FL, no antena impresa. Ese extremo queda en el borde. Bajo él, en todas las capas y un poco más allá del módulo, no hay cobre, pistas, vías ni plano. El USB y el buck no van bajo esa zona.
11. Masa digital (ESP32, USB, BQ24074, TPS63070) y masa analógica (ADS122C04, MCP6004, divisor de ECG, GSR y bandas) se unen en un solo punto, corto y ancho, junto a los ADS y al puente de 0 Ω entre `3V3_SYS` y `3V3_A`. Las señales analógicas no cruzan la masa digital. In1 es esa masa partida; In2 es `3V3_SYS` sin señales de datos. Los dos nodos del inductor del TPS63070 van en F.Cu, sin vía, a 0,40 mm.

Quedan pendientes para el esquema y prototipo: polarización y secuencia de los pines de modo del BQ24074, presupuesto de corriente de los módulos, compatibilidad real de sus niveles eléctricos y pruebas del aislador externo. Ningún documento autoriza fabricar hasta superar los ensayos listados en `especificacion.md`.
