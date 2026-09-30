# Revisión de diseño — 30 de septiembre de 2026

La revisión `SPEC-0.4` resuelve las contradicciones detectadas entre el README y `SPEC-0.3`.

1. Un único raíl de 3,3 V sustituye `2V9_A` y el TPS7A20; el TCA9801 deja de ser necesario.
2. OFF permite carga y programación desde USB con conexiones corporales abiertas.
3. ON bloquea VBUS hacia el cargador, alimenta desde batería y mantiene D+/D− para datos/programación.
4. VBUS ya no abre automáticamente la barrera: la adquisición con USB solo se admite usando un aislador externo alimentado desde el host. La placa informa presencia USB, pero no puede certificar el aislador.
5. El divisor del ECG se recalcula tras medir el AD8232 alimentado a 3,3 V para no exceder la referencia ADS de 2,048 V.
6. GSR y las bandas conservan excitación ≈0,50 V y 100 kΩ físicamente en serie, con corriente de corto ≈5 µA.

Quedan bloqueados hasta prototipo: MOSFET de VBUS y su orientación, contactos de barrera, presupuesto de corriente de breakouts/relés, compatibilidad real de módulos y pruebas de aislamiento externo. Ningún documento autoriza fabricar hasta superar los ensayos listados en `especificacion.md`.
