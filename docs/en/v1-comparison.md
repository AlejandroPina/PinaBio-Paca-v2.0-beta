# PinaBio V1 versus V2 — revision `CMP-0.4`

V1 has published PCB, firmware and application material. V2 now has a KiCad 9.0.9 prototype schematic and PCB with zero ERC, DRC and schematic/PCB parity issues, but no assembled and tested board, V2 firmware or V2 application. V2 proposes a dedicated 600 SPS ADS122C04 ECG path, a separate slow ADS path, PPG interrupt timing and a protected LiPo/BQ24074/TPS63070 power tree. Sensor connectors have no automatic cutoff.

The revised V2 uses a 3.3 V rail plus a 3.0 V LDO for the temperature module, rather than a 2.9 V analogue rail, charges/programs with switch OFF, and permits USB data with switch ON only through a host-powered external isolator during person-connected use. These are unvalidated design targets, not measured safety or performance claims. V2 is intentionally incompatible with V1.1 software and has no compatibility adapter.
