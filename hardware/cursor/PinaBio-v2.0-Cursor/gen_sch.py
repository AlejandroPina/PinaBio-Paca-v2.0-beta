#!/usr/bin/env python3
"""Generate the PinaBio v.2.0. Cursor schematic from SPEC-0.9."""
import re
import uuid
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SYM = Path("/usr/share/kicad/symbols")
D = Decimal
GRID = D("1.27")
STUB = D("2.54")

def q(v):
    if not isinstance(v, D):
        v = D(str(v))
    nm = (v * D(1000000)).quantize(D("1"), rounding=ROUND_HALF_UP)
    return nm / D(1000000)

def fmt(v):
    v = q(v)
    s = format(v, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"

def snap(v):
    v = q(v)
    n = (v / GRID).quantize(D("1"), rounding=ROUND_HALF_UP)
    return n * GRID

def grab(text, name):
    token = f'(symbol "{name}"'
    i = text.find(token)
    if i < 0:
        raise SystemExit(f"symbol not found: {name}")
    depth = 0
    for j in range(i, len(text)):
        depth += (text[j] == "(") - (text[j] == ")")
        if depth == 0:
            return text[i : j + 1]
    raise SystemExit(f"unbalanced {name}")

def materialize(path, name, lib):
    text = Path(path).read_text(errors="replace")
    raw = grab(text, name)
    m = re.search(r'\(extends "([^"]+)"\)', raw)
    if not m:
        return raw.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)
    parent_name = m.group(1)
    parent = grab(text, parent_name)
    units = []
    key = f'(symbol "{parent_name}_'
    idx = 0
    while True:
        k = parent.find(key, idx)
        if k < 0:
            break
        depth = 0
        for j in range(k, len(parent)):
            depth += (parent[j] == "(") - (parent[j] == ")")
            if depth == 0:
                units.append(parent[k : j + 1].replace(f"{parent_name}_", f"{name}_", 1))
                idx = j + 1
                break
    inner = raw[raw.find("\n") + 1 :]
    inner = re.sub(r'\(extends "[^"]+"\)\s*', "", inner, count=1)
    inner = inner.rstrip()
    if inner.endswith(")"):
        inner = inner[:-1]
    return f'(symbol "{lib}:{name}"\n' + inner + "\n" + "\n".join(units) + "\n)\n"

PIN_RE = re.compile(
    r'\(pin (\w+) \w+\s+\(at ([-\d.]+) ([-\d.]+) (\d+)\)\s+\(length ([-\d.]+)\)'
    r'[\s\S]*?\(name "([^"]*)"[\s\S]*?\(number "([^"]+)"'
)

def parse_units(body, short):
    units = {}
    key = f'(symbol "{short}_'
    idx = 0
    while True:
        k = body.find(key, idx)
        if k < 0:
            break
        depth = 0
        for j in range(k, len(body)):
            depth += (body[j] == "(") - (body[j] == ")")
            if depth == 0:
                chunk = body[k : j + 1]
                um = re.match(rf'\(symbol "{re.escape(short)}_(\d+)_', chunk)
                unit = int(um.group(1))
                pins = []
                for typ, x, y, ang, length, pname, num in PIN_RE.findall(chunk):
                    pins.append(
                        {
                            "num": num,
                            "name": pname,
                            "type": typ,
                            "x": D(x),
                            "y": D(y),
                            "ang": int(ang),
                            "len": D(length),
                        }
                    )
                units.setdefault(unit, []).extend(pins)
                idx = j + 1
                break
    return units

def pins_of(units, unit):
    return list(units.get(0, [])) + list(units.get(unit, []))

def outward(ang):
    a = (int(ang) + 180) % 360
    return {0: (D(1), D(0)), 90: (D(0), D(-1)), 180: (D(-1), D(0)), 270: (D(0), D(1))}[a]

def label_angle(dx, dy):
    return {(1, 0): 0, (0, -1): 270, (-1, 0): 180, (0, 1): 90}[(int(dx), int(dy))]

def custom_symbol(lib_id, ref, desc, pins):
    short = lib_id.split(":")[-1]
    xs = [p["x"] for p in pins]
    ys = [p["y"] for p in pins]
    # body inset from the pin tips by the pin length
    x0, x1 = min(xs) + D("2.54"), max(xs) - D("2.54")
    y0, y1 = min(ys) + D("2.54"), max(ys) - D("2.54")
    pin_s = []
    for p in pins:
        pin_s.append(
            f'''(pin {p["type"]} line (at {fmt(p["x"])} {fmt(p["y"])} {p["ang"]}) (length 2.54)
(name "{p["name"]}" (effects (font (size 1.27 1.27))))
(number "{p["num"]}" (effects (font (size 1.27 1.27)))))'''
        )
    return f'''(symbol "{lib_id}"
(exclude_from_sim no) (in_bom yes) (on_board yes)
(property "Reference" "{ref}" (at 0 {fmt(y1 + D("2.54"))} 0) (effects (font (size 1.27 1.27))))
(property "Value" "{short}" (at 0 {fmt(y0 - D("2.54"))} 0) (effects (font (size 1.27 1.27))))
(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
(property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
(property "Description" "{desc}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
(symbol "{short}_0_1"
(rectangle (start {fmt(x0)} {fmt(y0)}) (end {fmt(x1)} {fmt(y1)})
(stroke (width 0.254) (type default)) (fill (type background))))
(symbol "{short}_1_1"
{chr(10).join(pin_s)}
))
'''

def P(num, name, typ, x, y, ang):
    return {"num": str(num), "name": name, "type": typ, "x": D(str(x)), "y": D(str(y)), "ang": ang, "len": D("2.54")}

TPS_PINS = [
    P(1, "PS/SYNC", "input", -15.24, 12.7, 0),
    P(2, "PG", "open_collector", -15.24, 10.16, 0),
    P(14, "EN", "input", -15.24, 7.62, 0),
    P(15, "VSEL", "input", -15.24, 5.08, 0),
    P(12, "VIN", "power_in", -15.24, 2.54, 0),
    P(13, "VIN", "power_in", -15.24, 0, 0),
    P(3, "VAUX", "passive", -15.24, -2.54, 0),
    P(5, "FB", "input", -15.24, -5.08, 0),
    P(6, "FB2", "passive", -15.24, -7.62, 0),
    P(11, "L1", "passive", 15.24, 7.62, 180),
    P(10, "PGND", "power_in", 15.24, 5.08, 180),
    P(9, "L2", "passive", 15.24, 2.54, 180),
    P(7, "VOUT", "power_out", 15.24, 0, 180),
    P(8, "VOUT", "passive", 15.24, -2.54, 180),
    P(4, "GND", "power_in", 0, -15.24, 90),
]
ADS_PINS = [
    P(1, "A0", "input", -12.7, 10.16, 0),
    P(2, "A1", "input", -12.7, 7.62, 0),
    P(3, "RESET", "input", -12.7, 5.08, 0),
    P(4, "DGND", "power_in", -12.7, 2.54, 0),
    P(5, "AVSS", "power_in", -12.7, 0, 0),
    P(6, "AIN3", "passive", -12.7, -2.54, 0),
    P(7, "AIN2", "passive", -12.7, -5.08, 0),
    P(8, "REFN", "passive", -12.7, -7.62, 0),
    P(16, "SCL", "input", 12.7, 10.16, 180),
    P(15, "SDA", "bidirectional", 12.7, 7.62, 180),
    P(14, "DRDY", "output", 12.7, 5.08, 180),
    P(13, "DVDD", "power_in", 12.7, 2.54, 180),
    P(12, "AVDD", "power_in", 12.7, 0, 180),
    P(11, "AIN0", "passive", 12.7, -2.54, 180),
    P(10, "AIN1", "passive", 12.7, -5.08, 180),
    P(9, "REFP", "passive", 12.7, -7.62, 180),
]

LIBS = {}

def add_lib(key, body, short):
    LIBS[key] = {"body": body, "short": short, "units": parse_units(body, short)}

def load_official():
    specs = [
        ("R", SYM / "Device.kicad_sym", "R", "Device"),
        ("C", SYM / "Device.kicad_sym", "C", "Device"),
        ("L", SYM / "Device.kicad_sym", "L", "Device"),
        ("USB", SYM / "Connector.kicad_sym", "USB_C_Receptacle_USB2.0_16P", "Connector"),
        ("SW", SYM / "Switch.kicad_sym", "SW_Slide_DPDT", "Switch"),
        ("PUSH", SYM / "Switch.kicad_sym", "SW_Push", "Switch"),
        ("BQ", SYM / "Battery_Management.kicad_sym", "BQ24074RGT", "Battery_Management"),
        ("ESD", SYM / "Power_Protection.kicad_sym", "USBLC6-2SC6", "Power_Protection"),
        ("NT", SYM / "Device.kicad_sym", "NetTie_2", "Device"),
        ("BZX", SYM / "Diode.kicad_sym", "BZX84Cxx", "Diode"),
        ("NMOS", SYM / "Transistor_FET.kicad_sym", "Q_NMOS_GSD", "Transistor_FET"),
        ("PMOS", SYM / "Transistor_FET.kicad_sym", "TP0610T", "Transistor_FET"),
        ("LDO", SYM / "Regulator_Linear.kicad_sym", "TLV70012_SOT23-5", "Regulator_Linear"),
        ("OPA", SYM / "Amplifier_Operational.kicad_sym", "LM2902", "Amplifier_Operational"),
        ("ESP", SYM / "RF_Module.kicad_sym", "ESP32-S3-MINI-1", "RF_Module"),
        ("FLAG", SYM / "power.kicad_sym", "PWR_FLAG", "power"),
    ]
    for n in (2, 3, 4, 5, 6):
        specs.append((f"J{n}", SYM / "Connector_Generic.kicad_sym", f"Conn_01x{n:02d}", "Connector_Generic"))
    for key, path, name, lib in specs:
        body = materialize(path, name, lib)
        add_lib(key, body, name)
    add_lib(
        "TPS",
        custom_symbol(
            "PinaCursor:TPS63070",
            "U",
            "TPS63070 adjustable buck-boost, RNM, pinout SLVSC58B",
            TPS_PINS,
        ),
        "TPS63070",
    )
    add_lib(
        "ADS",
        custom_symbol(
            "PinaCursor:ADS122C04PW",
            "U",
            "ADS122C04 TSSOP-16 PW pinout, SBAS751B",
            ADS_PINS,
        ),
        "ADS122C04PW",
    )

# placements filled in build()
PLACES = []
# Purchasable identity. Electrical value and footprint stay as they are.
# Empty MPN means the exact orderable was not confirmed.
META = {}

def stamp(refs, mfr, mpn, voltage="", dielectric=""):
    for ref in refs:
        META[ref] = {"mfr": mfr, "mpn": mpn, "voltage": voltage, "dielectric": dielectric}

def fill_meta():
    y = "YAGEO"
    sm = "Samsung Electro-Mechanics"
    stamp(["R1", "R2"], y, "RC0603FR-075K1L")
    stamp(["R35", "R36"], y, "RC0603FR-0722RL")
    stamp(["R3", "R15"], y, "RC0603JR-070RL")
    stamp(["R4", "R22", "R38", "R25", "R26", "R27", "R29"], y, "RC0603FR-0710KL")
    stamp(["R5"], y, "RC0603FR-0715KL")
    stamp(["R6", "R7"], y, "RC0603FR-072K94L")
    stamp(["R37"], y, "RC0603FR-0746K4L")
    stamp(["R8"], y, "RC0603FR-072K2L")
    stamp(["R9", "R10", "R11", "R12", "R19", "R20", "R21", "R30", "R31", "R32"], y, "RC0603FR-07100KL")
    stamp(["R13"], y, "RT0603BRD0749K9L")
    stamp(["R14"], y, "RT0603BRD0716KL")
    stamp(["R16", "R17"], y, "RC0603FR-071ML")
    stamp(["R18"], y, "RC0603FR-07330KL")
    stamp(["R23", "R24"], y, "RC0603FR-074K7L")
    stamp(["R28"], y, "RC0603FR-0756KL")
    stamp(["R33"], y, "RC0603FR-0733K2L")
    stamp(["R34"], y, "RC0603FR-0747K5L")
    stamp(["C1"], sm, "CL10A475KO8NNNC", "16V", "X5R")
    stamp(["C2", "C3", "C4", "C5", "C6", "C10", "C16"], sm, "CL21A106KOQNNNE", "16V", "X5R")
    stamp(["C7", "C8", "C9"], sm, "CL21A226MAYNNNE", "25V", "X5R")
    stamp(["C11", "C14", "C17", "C18", "C19", "C20", "C21", "C22"], sm, "CL10B104KB8NNNC", "50V", "X7R")
    stamp(["C12", "C13"], sm, "CL21B225KAFNNNE", "25V", "X7R")
    stamp(["C15"], sm, "CL10A105KB8NNNC", "50V", "X5R")
    stamp(["J1"], "HCTL", "HC-TYPE-C-16P-01A")
    stamp(["U1"], "STMicroelectronics", "USBLC6-2SC6")
    stamp(["D1"], "Nexperia", "BZX84-C3V6,215")
    stamp(["U2"], "Texas Instruments", "BQ24074RGTR")
    stamp(["SW1"], "C&K", "JS202011JCQN")
    stamp(["U3"], "Texas Instruments", "TPS63070RNMR")
    stamp(["U4"], "Texas Instruments", "TLV75530PDBVR")
    stamp(["Q1"], "onsemi", "BSS84LT1G")
    stamp(["Q2", "Q3"], "onsemi", "BSS138LT1G")
    stamp(["J2"], "JST", "B3B-PH-K-S(LF)(SN)")
    stamp(["U5"], "Espressif", "ESP32-S3-MINI-1U-N8")
    stamp(["SW2"], "Omron", "B3U-1000P")
    stamp(["U6", "U7"], "Texas Instruments", "ADS122C04IPWR")
    stamp(["U8"], "Microchip", "MCP6004-I/SL")
    stamp(["J3"], "JST", "B6B-PH-K-S(LF)(SN)")
    stamp(["J4"], "JST", "B5B-PH-K-S(LF)(SN)")
    stamp(["J5"], "JST", "B4B-PH-K-S(LF)(SN)")
    stamp(["J6", "J7", "J8"], "JST", "B2B-PH-K-S(LF)(SN)")
    # L1 stays blank: the land is XAL4020 and the datasheet link is the XFL4020 family.

def place(lib, ref, value, fp, ds, unit, assign):
    pins = pins_of(LIBS[lib]["units"], unit)
    if not pins:
        raise SystemExit(f"no pins {lib} unit {unit}")
    nets = {}
    for p in pins:
        if p["num"] not in assign:
            if p["type"] == "no_connect":
                nets[p["num"]] = None
            else:
                raise SystemExit(f"{ref} {lib} unit {unit} missing pin {p['num']} {p['name']}")
        else:
            nets[p["num"]] = assign[p["num"]]
    extra = META.get(ref, {"mfr": "", "mpn": "", "voltage": "", "dielectric": ""})
    PLACES.append(
        {
            "lib": lib,
            "ref": ref,
            "value": value,
            "fp": fp,
            "ds": ds,
            "unit": unit,
            "nets": nets,
            "pins": pins,
            "mfr": extra["mfr"],
            "mpn": extra["mpn"],
            "voltage": extra["voltage"],
            "dielectric": extra["dielectric"],
        }
    )

def by_name(lib, unit, mapping):
    pins = pins_of(LIBS[lib]["units"], unit)
    assign = {}
    for p in pins:
        if p["name"] not in mapping:
            raise SystemExit(f"name {p['name']} not in map for {lib} u{unit}: {[x['name'] for x in pins]}")
        assign[p["num"]] = mapping[p["name"]]
    return assign

def build_places():
    fill_meta()
    R0603 = "Resistor_SMD:R_0603_1608Metric"
    C0603 = "Capacitor_SMD:C_0603_1608Metric"
    C0805 = "Capacitor_SMD:C_0805_2012Metric"
    SOT23 = "Package_TO_SOT_SMD:SOT-23"
    DS_BQ = "https://www.ti.com/lit/ds/symlink/bq24074.pdf"
    DS_TPS = "https://www.ti.com/lit/ds/symlink/tps63070.pdf"
    DS_LDO = "https://www.ti.com/lit/ds/symlink/tlv755p.pdf"
    DS_ADS = "https://www.ti.com/lit/ds/symlink/ads122c04.pdf"
    DS_ESP = "https://www.espressif.com/sites/default/files/documentation/esp32-s3-mini-1_mini-1u_datasheet_en.pdf"
    DS_OPA = "https://ww1.microchip.com/downloads/en/DeviceDoc/MCP6001-1R-1U-2-4-1-MHz-Low-Power-Op-Amp-DS20001733L.pdf"

    def R(ref, value, a, b, ds="~"):
        place("R", ref, value, R0603, ds, 1, {"1": a, "2": b})

    def C(ref, value, a, b, fp=C0603):
        place("C", ref, value, fp, "~", 1, {"1": a, "2": b})

    def J(n, ref, value, nets, fp):
        place(f"J{n}", ref, value, fp, "~", 1, {str(i + 1): nets[i] for i in range(n)})

    # USB-C sink
    usb_pins = pins_of(LIBS["USB"]["units"], 1)
    usb = {}
    for p in usb_pins:
        name = p["name"]
        if name in ("GND", "SHIELD"):
            usb[p["num"]] = "GND"
        elif name == "VBUS":
            usb[p["num"]] = "VBUS"
        elif name == "CC1":
            usb[p["num"]] = "CC1"
        elif name == "CC2":
            usb[p["num"]] = "CC2"
        elif name == "D-":
            usb[p["num"]] = "USB_DM_C"
        elif name == "D+":
            usb[p["num"]] = "USB_DP_C"
        elif name in ("SBU1", "SBU2"):
            usb[p["num"]] = None
        else:
            raise SystemExit("USB pin " + name)
    place(
        "USB",
        "J1",
        "USB-C",
        "Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A",
        "~",
        1,
        usb,
    )
    R("R1", "5.1k", "CC1", "GND")
    R("R2", "5.1k", "CC2", "GND")
    place(
        "ESD",
        "U1",
        "USBLC6-2SC6",
        "Package_TO_SOT_SMD:SOT-23-6",
        "https://www.st.com/resource/en/datasheet/usblc6-2.pdf",
        1,
        {"1": "USB_DM_C", "3": "USB_DP_C", "6": "USB_DM", "4": "USB_DP", "5": "VBUS", "2": "GND"},
    )
    # 22 ohm between the USBLC6 (connector side already on USB_D*_C) and the ESP32.
    R("R35", "22", "USB_DM", "USB_DM_IO")
    R("R36", "22", "USB_DP", "USB_DP_IO")
    R("R3", "0", "VBUS", "VBUS_RAW")
    R("R4", "10.0k", "VBUS", "VLOG")
    R("R5", "15.0k", "VLOG", "GND")
    place(
        "BZX",
        "D1",
        "BZX84-C3V6",
        SOT23,
        "https://assets.nexperia.com/documents/data-sheet/BZX84_SERIES.pdf",
        1,
        {"3": "VLOG", "1": "GND"},
    )
    # BQ24074. Pin 15 is ITERM. Pin 14 is TMR: 46.4 kΩ 1% to ground.
    place(
        "BQ",
        "U2",
        "BQ24074",
        "Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm",
        DS_BQ,
        1,
        {
            "15": "ITERM",
            "4": "EN2_CE",
            "14": "TMR",
            "6": "VLOG",
            "5": "EN2_CE",
            "12": "ILIM",
            "16": "ISET",
            "13": "VBUS_RAW",
            "17": "GND",
            "8": "GND",
            "10": "SYS",
            "11": "SYS",
            "2": "BAT_PROT",
            "3": "BAT_PROT",
            "1": "TS",
            "7": "PGOOD",
            "9": "CHG",
        },
    )
    R("R6", "2.94k 1%", "ISET", "GND", DS_BQ)
    R("R7", "2.94k 1%", "ITERM", "GND", DS_BQ)
    R("R37", "46.4k 1%", "TMR", "GND", DS_BQ)
    R("R8", "2.2k", "ILIM", "GND")
    R("R9", "100k", "CHG", "3V3_SYS")
    R("R10", "100k", "PGOOD", "3V3_SYS")
    C("C1", "4.7uF", "VBUS_RAW", "GND")
    C("C2", "10uF", "SYS", "GND", C0805)
    C("C3", "10uF", "BAT_PROT", "GND", C0805)
    # DPDT: pin 2 and pin 5 are the commons (B). Throw A is ON.
    place(
        "SW",
        "SW1",
        "SW_DPDT",
        "Button_Switch_SMD:SW_DPDT_CK_JS202011JCQN",
        "https://www.ckswitches.com/media/1428/js.pdf",
        1,
        {"1": "VLOG", "2": "EN2_CE", "3": "GND", "4": "BAT_PROT", "5": "TPS_EN", "6": "VLOG"},
    )
    R("R11", "100k", "EN2_CE", "GND")
    R("R12", "100k", "TPS_EN", "GND")
    # TPS63070
    place(
        "TPS",
        "U3",
        "TPS63070",
        "PinaCursor:TPS63070RNM",
        DS_TPS,
        1,
        {
            "1": "GND",
            "2": None,
            "14": "TPS_EN",
            "15": "GND",
            "12": "SYS",
            "13": "SYS",
            "3": "VAUX",
            "5": "FB",
            "6": "GND",
            "11": "SW_L1",
            "10": "GND",
            "9": "SW_L2",
            "7": "3V3_SYS",
            "8": "3V3_SYS",
            "4": "GND",
        },
    )
    place(
        "L",
        "L1",
        "1.5uH",
        "Inductor_SMD:L_Coilcraft_XAL4020-XXX",
        "https://www.coilcraft.com/en-us/products/power/shielded-inductors/xfl/xfl4020/",
        1,
        {"1": "SW_L1", "2": "SW_L2"},
    )
    C("C4", "10uF", "SYS", "GND", C0805)
    C("C5", "10uF", "SYS", "GND", C0805)
    C("C6", "10uF", "SYS", "GND", C0805)
    C("C7", "22uF", "3V3_SYS", "GND", C0805)
    C("C8", "22uF", "3V3_SYS", "GND", C0805)
    C("C9", "22uF", "3V3_SYS", "GND", C0805)
    C("C10", "10uF", "3V3_SYS", "GND", C0805)
    C("C11", "100nF", "VAUX", "GND")
    R("R13", "49.9k 0.1%", "3V3_SYS", "FB", DS_TPS)
    R("R14", "16.0k 0.1%", "FB", "GND", DS_TPS)
    # 3.0 V only for the temperature module
    place(
        "LDO",
        "U4",
        "TLV75530PDBVR",
        "Package_TO_SOT_SMD:SOT-23-5",
        DS_LDO,
        1,
        {"1": "3V3_SYS", "3": "3V3_SYS", "2": "GND", "5": "3V0_TEMP"},
    )
    C("C12", "2.2uF", "3V3_SYS", "GND", C0805)
    C("C13", "2.2uF", "3V0_TEMP", "GND", C0805)
    R("R15", "0", "3V3_SYS", "3V3_A")
    # Battery divider opens when 3V3_SYS falls
    place("PMOS", "Q1", "BSS84", SOT23, "https://www.onsemi.com/pdf/datasheet/bss84-d.pdf", 1, {"1": "Q1G", "2": "BAT_PROT", "3": "DIV_IN"})
    place("NMOS", "Q2", "BSS138", SOT23, "https://www.onsemi.com/pdf/datasheet/bss138-d.pdf", 1, {"1": "3V3_SYS", "2": "GND", "3": "Q1G"})
    R("R16", "1M", "Q1G", "BAT_PROT")
    R("R17", "1M", "DIV_IN", "BAT_SENSE")
    R("R18", "330k", "BAT_SENSE", "GND")
    R("R19", "100k", "3V3_SYS", "GND")
    C("C14", "100nF", "BAT_SENSE", "GND")
    # VBUS presence, active low on GPIO2
    place("NMOS", "Q3", "BSS138", SOT23, "https://www.onsemi.com/pdf/datasheet/bss138-d.pdf", 1, {"1": "VBUS_G", "2": "GND", "3": "VBUS_N"})
    R("R20", "100k", "VLOG", "VBUS_G")
    R("R21", "100k", "VBUS_N", "3V3_SYS")
    J(3, "J2", "J_BATT", ["BAT_PROT", "GND", "TS"], "Connector_JST:JST_PH_B3B-PH-K_1x03_P2.00mm_Vertical")
    # ESP32-S3-MINI-1U-N8
    esp = {}
    named = {
        "45": "EN_MOD",
        "4": "BOOT",
        "5": "BAT_SENSE",
        "6": "VBUS_N",
        "8": "SDA_ADC",
        "9": "SCL_ADC",
        "10": "DRDY_ECG",
        "11": "DRDY_SLOW",
        "12": "SDA_MOD",
        "13": "SCL_MOD",
        "14": "PPG_INT",
        "15": "LO_P",
        "16": "LO_N",
        "23": "USB_DM_IO",
        "24": "USB_DP_IO",
    }
    for p in pins_of(LIBS["ESP"]["units"], 1):
        if p["num"] in named:
            esp[p["num"]] = named[p["num"]]
        elif p["name"] in ("GND", "3V3"):
            esp[p["num"]] = "GND" if p["name"] == "GND" else "3V3_SYS"
        else:
            esp[p["num"]] = None
    place(
        "ESP",
        "U5",
        "ESP32-S3-MINI-1U-N8",
        "RF_Module:ESP32-S2-MINI-1U",
        DS_ESP,
        1,
        esp,
    )
    R("R22", "10k", "EN_MOD", "3V3_SYS", DS_ESP)
    C("C15", "1uF", "EN_MOD", "GND")
    C("C16", "10uF", "3V3_SYS", "GND", C0805)
    C("C17", "100nF", "3V3_SYS", "GND")
    place("PUSH", "SW2", "BOOT", "Button_Switch_SMD:SW_SPST_B3U-1000P", "~", 1, {"1": "BOOT", "2": "GND"})
    R("R38", "10k", "BOOT", "3V3_SYS", DS_ESP)
    R("R23", "4.7k", "SDA_ADC", "3V3_SYS")
    R("R24", "4.7k", "SCL_ADC", "3V3_SYS")
    R("R25", "10k", "PPG_INT", "3V3_SYS")
    # ADS122C04 ECG 0x40 and slow 0x41
    def ads(ref, a0, ain0, ain1, ain2, drdy):
        place(
            "ADS",
            ref,
            "ADS122C04",
            "Package_SO:TSSOP-16_4.4x5mm_P0.65mm",
            DS_ADS,
            1,
            {
                "1": a0,
                "2": "AGND",
                "3": "3V3_SYS",
                "4": "AGND",
                "5": "AGND",
                "6": "3V3_A",
                "7": ain2,
                "8": "3V3_A",
                "9": "3V3_A",
                "10": ain1,
                "11": ain0,
                "12": "3V3_A",
                "13": "3V3_SYS",
                "14": drdy,
                "15": "SDA_ADC",
                "16": "SCL_ADC",
            },
        )

    ads("U6", "AGND", "ECG_DIV", "3V3_A", "3V3_A", "DRDY_ECG")
    ads("U7", "3V3_SYS", "OUT_GSR", "OUT_TH", "OUT_AB", "DRDY_SLOW")
    C("C18", "100nF", "3V3_A", "AGND")
    C("C19", "100nF", "3V3_SYS", "AGND")
    C("C20", "100nF", "3V3_A", "AGND")
    C("C21", "100nF", "3V3_SYS", "AGND")
    R("R26", "10k", "DRDY_ECG", "3V3_SYS")
    R("R27", "10k", "DRDY_SLOW", "3V3_SYS")
    # MCP6004 followers
    place("OPA", "U8", "MCP6004", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm", DS_OPA, 1, by_name("OPA", 1, {"+": "DIV_EXC", "-": "0V5_EXC", "~": "0V5_EXC"}))
    place("OPA", "U8", "MCP6004", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm", DS_OPA, 2, by_name("OPA", 2, {"+": "SNS_GSR", "-": "OUT_GSR", "~": "OUT_GSR"}))
    place("OPA", "U8", "MCP6004", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm", DS_OPA, 3, by_name("OPA", 3, {"+": "SNS_TH", "-": "OUT_TH", "~": "OUT_TH"}))
    place("OPA", "U8", "MCP6004", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm", DS_OPA, 4, by_name("OPA", 4, {"+": "SNS_AB", "-": "OUT_AB", "~": "OUT_AB"}))
    place("OPA", "U8", "MCP6004", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm", DS_OPA, 5, by_name("OPA", 5, {"V+": "3V3_A", "V-": "AGND"}))
    C("C22", "100nF", "3V3_A", "AGND")
    R("R28", "56k 1%", "3V3_A", "DIV_EXC")
    R("R29", "10k 1%", "DIV_EXC", "AGND")
    R("R30", "100k", "0V5_EXC", "SNS_GSR")
    R("R31", "100k", "0V5_EXC", "SNS_TH")
    R("R32", "100k", "0V5_EXC", "SNS_AB")
    R("R33", "33.2k 1%", "ECG_OUT", "ECG_DIV")
    R("R34", "47.5k 1%", "ECG_DIV", "AGND")
    # One short wide join between digital GND and analog AGND, next to the ADCs.
    place(
        "NT",
        "NT1",
        "GND_TIE",
        "PinaCursor:GndTie_2mm",
        "~",
        1,
        {"1": "GND", "2": "AGND"},
    )
    ph = "Connector_JST:JST_PH_B{n}B-PH-K_1x{n:02d}_P2.00mm_Vertical"
    J(6, "J3", "J_ECG", ["3V3_A", "AGND", "ECG_OUT", "LO_P", "LO_N", "3V3_A"], ph.format(n=6))
    J(5, "J4", "J_PPG", ["3V3_SYS", "GND", "SCL_MOD", "SDA_MOD", "PPG_INT"], ph.format(n=5))
    J(4, "J5", "J_TEMP", ["3V0_TEMP", "GND", "SDA_MOD", "SCL_MOD"], ph.format(n=4))
    J(2, "J6", "J_GSR", ["SNS_GSR", "AGND"], ph.format(n=2))
    J(2, "J7", "J_RESP_T", ["SNS_TH", "AGND"], ph.format(n=2))
    J(2, "J8", "J_RESP_A", ["SNS_AB", "AGND"], ph.format(n=2))

def pack():
    x = D("25.4")
    y = D("25.4")
    row_h = D(0)
    limit = D("1050")
    gap = D("5.08")
    for part in PLACES:
        xs, ys = [], []
        for p in part["pins"]:
            xs.append(p["x"])
            ys.append(-p["y"])  # file Y
        minx, maxx = min(xs) - STUB, max(xs) + STUB
        miny, maxy = min(ys) - STUB, max(ys) + STUB
        w, h = maxx - minx, maxy - miny
        if x + w > limit:
            x = D("25.4")
            y = snap(y + row_h + gap)
            row_h = D(0)
        # center so the bbox starts at (x, y)
        cx = snap(x - minx)
        cy = snap(y - miny)
        part["at"] = (cx, cy)
        x = snap(x + w + gap)
        row_h = max(row_h, h)
    return y + row_h + D("20")

def emit():
    sheet = str(uuid.uuid4())
    wires, labels, noconns, symbols = [], [], [], []
    occupied = {}  # point -> net or None

    def mark(pt, net):
        pt = (fmt(pt[0]), fmt(pt[1]))
        if pt in occupied and occupied[pt] != net:
            raise SystemExit(f"short at {pt}: {occupied[pt]} vs {net}")
        occupied[pt] = net

    for part in PLACES:
        sx, sy = part["at"]
        groups = {}
        for p in part["pins"]:
            wx, wy = q(sx + p["x"]), q(sy - p["y"])
            groups.setdefault((wx, wy), []).append(p)
        for (wx, wy), group in groups.items():
            nets = {part["nets"][p["num"]] for p in group}
            if len(nets) != 1:
                raise SystemExit(f"{part['ref']} stacked pins disagree at {wx},{wy}: {nets}")
            net = next(iter(nets))
            mark((wx, wy), net if net else f"NC:{part['ref']}")
            if net is None:
                if any(p["type"] != "no_connect" for p in group):
                    noconns.append(f'(no_connect (at {fmt(wx)} {fmt(wy)}) (uuid "{uuid.uuid4()}"))')
                continue
            dx, dy = outward(group[0]["ang"])
            ex, ey = q(wx + dx * STUB), q(wy + dy * STUB)
            mark((ex, ey), net)
            wires.append(
                f'(wire (pts (xy {fmt(wx)} {fmt(wy)}) (xy {fmt(ex)} {fmt(ey)})) (stroke (width 0) (type default)) (uuid "{uuid.uuid4()}"))'
            )
            ang = label_angle(dx, dy)
            labels.append(
                f'(label "{net}" (at {fmt(ex)} {fmt(ey)} {ang}) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{uuid.uuid4()}"))'
            )
            part.setdefault("ends", {})[net] = (ex, ey)
        pinxml = "\n".join(
            f'(pin "{p["num"]}" (uuid "{uuid.uuid4()}"))' for p in part["pins"]
        )
        lib_ids = {
            "R": "Device:R",
            "C": "Device:C",
            "L": "Device:L",
            "USB": "Connector:USB_C_Receptacle_USB2.0_16P",
            "SW": "Switch:SW_Slide_DPDT",
            "PUSH": "Switch:SW_Push",
            "BQ": "Battery_Management:BQ24074RGT",
            "ESD": "Power_Protection:USBLC6-2SC6",
            "NT": "Device:NetTie_2",
            "BZX": "Diode:BZX84Cxx",
            "NMOS": "Transistor_FET:Q_NMOS_GSD",
            "PMOS": "Transistor_FET:TP0610T",
            "LDO": "Regulator_Linear:TLV70012_SOT23-5",
            "OPA": "Amplifier_Operational:LM2902",
            "ESP": "RF_Module:ESP32-S3-MINI-1",
            "TPS": "PinaCursor:TPS63070",
            "ADS": "PinaCursor:ADS122C04PW",
            "FLAG": "power:PWR_FLAG",
        }
        if part["lib"] in lib_ids:
            lib_id = lib_ids[part["lib"]]
        else:
            lib_id = f"Connector_Generic:Conn_01x{int(part['lib'][1:]):02d}"
        cap_props = ""
        if part["lib"] == "C":
            cap_props = (
                f'(property "Voltage" "{part["voltage"]}" (at {fmt(sx)} {fmt(sy)} 0) '
                f'(effects (font (size 1.27 1.27)) (hide yes)))\n'
                f'(property "Dielectric" "{part["dielectric"]}" (at {fmt(sx)} {fmt(sy)} 0) '
                f'(effects (font (size 1.27 1.27)) (hide yes)))\n'
            )
        symbols.append(
            f'''(symbol (lib_id "{lib_id}") (at {fmt(sx)} {fmt(sy)} 0) (unit {part["unit"]})
(exclude_from_sim no) (in_bom {"no" if part["ref"].startswith("#") or part["lib"] == "NT" else "yes"}) (on_board {"no" if part["ref"].startswith("#") else "yes"}) (dnp no)
(uuid "{uuid.uuid4()}")
(property "Reference" "{part["ref"]}" (at {fmt(sx)} {fmt(sy - D("1.27"))} 0) (effects (font (size 1.27 1.27))))
(property "Value" "{part["value"]}" (at {fmt(sx)} {fmt(sy + D("2.54"))} 0) (effects (font (size 1.27 1.27))))
(property "Footprint" "{part["fp"]}" (at {fmt(sx)} {fmt(sy)} 0) (effects (font (size 1.27 1.27)) (hide yes)))
(property "Datasheet" "{part["ds"]}" (at {fmt(sx)} {fmt(sy)} 0) (effects (font (size 1.27 1.27)) (hide yes)))
(property "Manufacturer" "{part["mfr"]}" (at {fmt(sx)} {fmt(sy)} 0) (effects (font (size 1.27 1.27)) (hide yes)))
(property "MPN" "{part["mpn"]}" (at {fmt(sx)} {fmt(sy)} 0) (effects (font (size 1.27 1.27)) (hide yes)))
{cap_props}{pinxml}
(instances (project "PinaBio-v2.0-Cursor" (path "/{sheet}" (reference "{part["ref"]}") (unit {part["unit"]}))))
)'''
        )

    # Power-out flags for power_in nets that have no power_out pin.
    driven = set()
    needs = set()
    for part in PLACES:
        for p in part["pins"]:
            net = part["nets"][p["num"]]
            if not net:
                continue
            if p["type"] == "power_out":
                driven.add(net)
            if p["type"] == "power_in":
                needs.add(net)
    for net in sorted(needs - driven):
        host = next(p for p in PLACES if net in p.get("ends", {}))
        ex, ey = host["ends"][net]
        # flag pin is at the symbol origin, length 0, so sit it on the stub end
        PLACES_FLAG = {
            "lib": "FLAG",
            "ref": "#FLG",
            "value": "PWR_FLAG",
            "fp": "",
            "ds": "~",
            "unit": 1,
            "at": (ex, ey),
            "pins": pins_of(LIBS["FLAG"]["units"], 1),
            "nets": {},
        }
        # emit directly
        symbols.append(
            f'''(symbol (lib_id "power:PWR_FLAG") (at {fmt(ex)} {fmt(ey)} 0) (unit 1)
(exclude_from_sim yes) (in_bom no) (on_board no) (dnp no)
(uuid "{uuid.uuid4()}")
(property "Reference" "#FLG" (at {fmt(ex)} {fmt(ey + D("2.54"))} 0) (effects (font (size 1.27 1.27)) (hide yes)))
(property "Value" "PWR_FLAG" (at {fmt(ex)} {fmt(ey - D("2.54"))} 0) (effects (font (size 1.27 1.27)) (hide yes)))
(property "Footprint" "" (at {fmt(ex)} {fmt(ey)} 0) (effects (font (size 1.27 1.27)) (hide yes)))
(property "Datasheet" "~" (at {fmt(ex)} {fmt(ey)} 0) (effects (font (size 1.27 1.27)) (hide yes)))
(pin "1" (uuid "{uuid.uuid4()}"))
(instances (project "PinaBio-v2.0-Cursor" (path "/{sheet}" (reference "#FLG") (unit 1))))
)'''
        )
        print(f"PWR_FLAG on {net}")

    bodies = "\n".join(LIBS[k]["body"] for k in LIBS)
    note = (
        "PinaBio v.2.0. Cursor. SPEC-0.9. Sensores sin corte en serie. "
        "Interruptor: throw A (pines 1 y 4) es ON. "
        "GPIO4=SDA y GPIO5=SCL del bus ADC; GPIO8=SDA y GPIO9=SCL de los modulos. "
        "J5 (J_TEMP) lleva 4 pines: 3V0_TEMP, GND, SDA_MOD, SCL_MOD. A0, A1 y A2 del CJMCU-30205 van a GND en el modulo y OS queda sin conectar. "
        "GPIO0 tiene 10 kΩ a 3V3_SYS. D+/D− llevan 22 Ω entre USBLC6-2SC6 y el ESP32. "
        "TMR del BQ24074 lleva 46,4 kΩ a masa. GND y AGND se unen solo en NT1."
    )
    sch = f'''(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") (uuid "{sheet}") (paper "A0")
(title_block (title "PinaBio v.2.0. Cursor") (date "2026-10-01") (rev "SPEC-0.9")
(comment 1 "Diseno de competicion Cursor. Sin corte de sensores.")
(comment 2 "PWR-0.7  TLV75530 solo para CJMCU-30205. Masa digital y analogica."))
(lib_symbols
{bodies}
)
{chr(10).join(symbols)}
{chr(10).join(wires)}
{chr(10).join(labels)}
{chr(10).join(noconns)}
(text "{note}" (at 25.4 12.7 0) (effects (font (size 2.0 2.0))) (uuid "{uuid.uuid4()}"))
(sheet_instances (path "/" (page "1")))
(embedded_fonts no)
)
'''
    out = ROOT / "PinaBio-v2.0-Cursor.kicad_sch"
    out.write_text(sch)
    print("wrote", out, "bytes", len(sch))

def tables():
    libs = [
        "Device",
        "Connector",
        "Connector_Generic",
        "Switch",
        "Battery_Management",
        "Power_Protection",
        "Diode",
        "Transistor_FET",
        "Regulator_Linear",
        "Amplifier_Operational",
        "RF_Module",
        "power",
    ]
    rows = ["(sym_lib_table", "  (version 7)"]
    for name in libs:
        rows.append(
            f'  (lib (name "{name}")(type "KiCad")(uri "${{KICAD9_SYMBOL_DIR}}/{name}.kicad_sym")(options "")(descr ""))'
        )
    rows.append(
        f'  (lib (name "PinaCursor")(type "KiCad")(uri "${{KIPRJMOD}}/PinaCursor.kicad_sym")(options "")(descr "TPS63070 and ADS122C04"))'
    )
    rows.append(")")
    (ROOT / "sym-lib-table").write_text("\n".join(rows) + "\n")
    (ROOT / "fp-lib-table").write_text(
        "(fp_lib_table\n  (version 7)\n"
        f'  (lib (name "PinaCursor")(type "KiCad")(uri "${{KIPRJMOD}}/lib.pretty")(options "")(descr "TPS63070 RNM"))\n'
        ")\n"
    )
    pro = ROOT / "PinaBio-v2.0-Cursor.kicad_pro"
    # The committed project holds the board rules (0.15 mm clearance, 0.25 mm via).
    # A stub would make KiCad rewrite those rules to its defaults.
    if not pro.exists():
        pro.write_text(
            '{"meta":{"filename":"PinaBio-v2.0-Cursor.kicad_pro","version":1},"sheets":[]}\n'
        )

def bom():
    seen = set()
    lines = ["Reference,Value,Footprint,Manufacturer,MPN,Voltage,Dielectric,Datasheet,Qty"]
    grouped = {}
    for p in PLACES:
        if p["ref"].startswith("#") or p["lib"] == "NT":
            continue
        if p["ref"] in seen:
            continue
        seen.add(p["ref"])
        key = (p["value"], p["fp"], p["mfr"], p["mpn"], p["voltage"], p["dielectric"])
        grouped.setdefault(key, []).append(p)
    for (value, fp, mfr, mpn, voltage, dielectric), parts in grouped.items():
        refs = " ".join(p["ref"] for p in parts)
        ds = parts[0]["ds"]
        lines.append(
            f'"{refs}","{value}","{fp}","{mfr}","{mpn}","{voltage}","{dielectric}","{ds}",{len(parts)}'
        )
    (ROOT / "bom.csv").write_text("\n".join(lines) + "\n")
    print("bom lines", len(lines) - 1)

def write_symlib():
    chunks = []
    for key in ("TPS", "ADS"):
        body = LIBS[key]["body"]
        body = body.replace('(symbol "PinaCursor:', '(symbol "', 1)
        chunks.append(body)
    (ROOT / "PinaCursor.kicad_sym").write_text(
        "(kicad_symbol_lib (version 20241209) (generator \"cursor\")\n" + "\n".join(chunks) + ")\n"
    )

def main():
    load_official()
    write_symlib()
    build_places()
    pack()
    emit()
    tables()
    bom()

if __name__ == "__main__":
    main()
