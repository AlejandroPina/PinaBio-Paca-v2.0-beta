# PinaBio Paca — contrato de firmware, BLE y datos `PROTO-0.4`

[Portada](../../README.md) · [Especificación](especificacion.md)

Propuesta de protocolo, no firmware implementado. Campos multibyte en *little-endian*. El protocolo conserva datos crudos, calibración y pérdidas; no diagnostica ni calcula HRV en la placa.

## Estados y armado

Estados: `BOOT`, `IDLE_USB`, `IDLE_BATTERY`, `ACQUIRING`, `LOW_BATTERY`, `SENSOR_FAULT` e `INTERNAL_FAULT`. `LEADS_OFF` es una bandera de ECG. VBUS no es por sí mismo un bloqueo: con ON, batería presente y aislador USB externo puede existir `ACQUIRING`. El firmware no puede detectar de forma fiable el aislador y debe informar `usb_present` y `isolation_unverified` en STATUS; la aplicación muestra una advertencia inequívoca y el usuario confirma el procedimiento seguro antes de START.

El armado exige ON físico, alimentación válida, realimentación de contactos abiertos al inicio, autocomprobación de buses/ADC y posterior cierre confirmado. Si falla un contacto, se abre o no confirma, el estado pasa a `INTERNAL_FAULT`; ningún comando puede forzar la barrera. OFF corta alimentación. Wi‑Fi queda desactivado desde el arranque.

## Muestreo

- ECG: ADS `0x40`, 600 SPS continuo, referencia interna 2,048 V, ganancia 1, PGA bypass; GPIO6 marca DRDY.
- GSR, tórax y abdomen: ADS `0x41`, MUX→START→DRDY→READ, 20 SPS efectivos por canal inicial; GPIO7 marca DRDY.
- PPG: MAX30102, RED+IR, 200 pares/s iniciales; GPIO10 dispara vaciado FIFO. El tiempo individual se reconstruye y se marca `TIMING_ESTIMATED` hasta validar deriva.
- Temperatura y batería: 1 Hz inicial. GSR y bandas conservan ADS crudo más magnitud y estado de calidad.

## BLE y trama

Servicio provisional `b88b0000-1a8c-4a2b-ae02-50494e414249`; características `0001` Control, `0002` Data, `0003` Status, `0004` Metadata y `0005` ControlResult. MTU objetivo 247 y mínimo 128 para START.

La trama mantiene cabecera de 22 bytes y CRC16/CCITT-FALSE final: `magic u16=0x5042`, `major u8=1`, `type u8` (ECG/PPG/SLOW/STATUS), `seq u16`, `flags u16`, `t0_us u64`, `period_ns u32`, `count u16`, payload y CRC16. ECG es s24 LE; PPG son RED u24 + IR u24; SLOW contiene `channel u8`, `quality u8`, `dt_us u16`, `value_s32` y `raw_s32`. Los canales SLOW son GSR, THORAX, ABDOMEN, TEMP y BATTERY.

`STATUS` incluye estado, motivo, `physical_vbus`, `isolation_unverified`, `body_contact_fb`, `adc_overrun`, `ble_drop` y `ppg_overflow`. Los motivos de START incluyen `LOW_BATTERY`, `CONTACT_OPEN`, `SENSOR_FAULT`, `INTERNAL_FAULT` y `MTU_TOO_SMALL`; no existe `VBUS_LOCKOUT`.

## Control, pérdida y pruebas

`START` recibe máscara de canales y devuelve sesión y tasas concedidas; `STOP`, `GET_STATUS` y `SET_PPG` conservan su semántica. No se habilitan AUX ni IDAC. Si los anillos se llenan se descartan muestras antiguas completas y la siguiente trama lleva `GAP_BEFORE`; nunca se repiten o inventan muestras.

Se deben probar diez minutos de ECG/PPG, pérdidas BLE y MTU insuficiente, contactos fallados, batería baja, saturación, FIFO PPG, CRC y los cuatro estados USB/interruptor. La prueba de adquisición con USB exige aislador externo medido: no puede aprobarse solo con una bandera de software.
