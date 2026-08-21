# Building a PDK for the UCI/INRF IGZO TFT process

**Working language.** This document, and every technical artefact it describes
(files, comments, reports, figures), is written in **English** — that is the
convention in `CLAUDE.md` §9 and it is what makes the work usable by UCLA and by
anyone reading a paper. **Conversation and answers are in Spanish.** If you are
an assistant reading this file: write the documents in English, reply to Juan in
Spanish.

---

## 1. Why this document exists

We have measured IGZO TFTs, a layer stack, and a GDS of the test chip. What we do
*not* have is a PDK — the packaged set of files that lets a tool draw, simulate,
check and hand off a design in this process without the designer re-deriving the
geometry every time.

The container ships three complete open-source PDKs at `/foss/pdks`. They are the
best possible reference, because they solve exactly this problem and their file
formats are the ones our tools (xschem, KLayout, ngspice, magic) already read.
This document maps what is in them, what each piece does, and which pieces we
need to write for IGZO.

---

## 2. What is installed at /foss/pdks

```
/foss/pdks/
├── sky130A          -> ciel/sky130/versions/<hash>/sky130A      SkyWater 130 nm
├── gf180mcuD        -> ciel/gf180mcu/versions/<hash>/gf180mcuD  GlobalFoundries 180 nm
├── ihp-sg13g2                                                    IHP SiGe BiCMOS 130 nm
├── ihp-sg13cmos5l                                                IHP CMOS variant
└── ciel/                                                         version store (2.1 GB)
```

`sky130A` and `gf180mcuD` are symlinks into the `ciel` version store. **Use
`gf180mcuD` as the primary template**: it is the process our own tapeout repo
targets, its PCell code is the most readable of the three, and it is small
enough to read end to end.

Both follow the same two-directory convention, which we should copy:

| Directory | Holds |
|---|---|
| `libs.tech/` | everything **tool-specific**: how each EDA tool is configured for this process |
| `libs.ref/`  | everything **design-specific**: the actual cells — GDS, LEF, symbols, models |

---

## 3. Directory tour — what every file is for

### 3.1 `libs.tech/klayout/` — layout, layers, DRC, PCells

```
klayout/tech/
├── gf180mcu.lyt          technology definition  (READ FIRST)
├── gf180mcu.lyp          layer display properties: colour, fill, name per layer
├── gf180mcu.map          GDS layer/datatype <-> stream name mapping
├── drc/                  design-rule decks (Ruby .drc, run by KLayout in batch)
├── lvs/                  layout-vs-schematic decks + netlist converters
├── pymacros/
│   ├── gf180mcu.lym      registers the PCell library at KLayout start-up
│   └── cells/            one Python file per device family
│       ├── fet.py            PCell *declaration*: parameters shown in the GUI
│       ├── draw_fet.py       PCell *implementation*: the geometry
│       ├── via_generator.py  shared helper that stamps contact arrays
│       └── ...
└── macros/               GUI menu items
```

**`*.lyt` — the technology file.** The root object. Declares the technology
name, the database unit (`<dbu>0.001</dbu>`, i.e. 1 nm), points at the `.lyp`,
and defines **connectivity** so KLayout can extract nets:

```xml
<connectivity>
  <connection>30/0,33/0,Metal1</connection>     <!-- diffusion, poly, via to M1 -->
  <connection>Metal1,35/0,Metal2</connection>   <!-- M1 - Via1 - M2 -->
  <symbols>Metal1='34/0+34/10'</symbols>        <!-- drawing + pin are one net -->
</connectivity>
```

**`*.lyp` — layer properties.** One `<properties>` block per layer with
`<source>layer/datatype@1</source>`, `<name>`, colour and fill pattern. This is
what makes a layout readable. *We already have one of these* (see §4).

**`*.map` — stream mapping.** Plain text, one line per layer:
`Metal1  NET,SPNET,PIN,VIA  34 0`. Used when writing GDS from a router or
importing from another tool.

**`pymacros/cells/*.py` — the PCells.** This is the part that answers "how do I
generate cells in KLayout". Two files per device: a *declaration* and a *draw*
function. The declaration is a `pya.PCellDeclarationHelper` subclass whose
`self.param(...)` calls become the parameter fields in the KLayout GUI:

```python
class nfet(pya.PCellDeclarationHelper):
    def __init__(self):
        super(nfet, self).__init__()
        self.param("w_gate", self.TypeDouble, "Width",  default=0.22, unit="um")
        self.param("l_gate", self.TypeDouble, "Length", default=0.28, unit="um")
        self.param("nf",     self.TypeInt,    "Number of Fingers", default=1)
        self.Type_handle = self.param("bulk", self.TypeList, "Bulk Type")
        self.Type_handle.add_choice("None", "None")
        self.Type_handle.add_choice("Guard Ring", "Guard Ring")

    def produce_impl(self):
        # hand the parameters to the geometry generator
        cell = draw_nfet(w=self.w_gate, l=self.l_gate, nf=self.nf, ...)
```

Note `nf` — *number of fingers* is a standard PCell parameter, and it is exactly
the knob we were sizing by hand in `scale/`.

`gf180mcu.lym` is the XML wrapper that makes KLayout import `cells/` at start-up
(`<autorun>true</autorun>`). Without it the PCells exist but never register.

### 3.2 `libs.tech/xschem/` — schematic capture

```
xschem/
├── xschemrc            sets XSCHEM_LIBRARY_PATH so the symbols are findable
├── symbols/            one .sym per device (60 files in gf180mcuD)
└── tests/              example schematics that exercise every device
```

**How a symbol becomes a netlist line.** An `.sym` file is plain text. The `K {}`
block carries the electrical behaviour; the `L`/`B`/`P`/`T` lines are just the
drawing. From `symbols/nfet_10v0_asym.sym`:

```
K {type=nmos
format="@spiceprefix@name @pinlist @model L=@L W=@W
+ nf=@nf ad=@ad as=@as pd=@pd ps=@ps m=@m"
lvs_format="@name @pinlist @model L=@L W=@W nf=@nf m=@m"
template="name=M1
L=0.60u
W=25u
nf=1
m=1
ad=\"'W * 1.48u'\"
model=nfet_10v0_asym
spiceprefix=X
"
}
B 5 17.5 -32.5 22.5 -27.5 {name=D dir=inout}    <!-- pin: drain -->
B 5 -22.5 -2.5 -17.5 2.5  {name=G dir=in}       <!-- pin: gate  -->
B 5 17.5  27.5 22.5  32.5 {name=S dir=inout}    <!-- pin: source-->
B 5 19.92 -0.08 20.08 0.08 {name=B dir=in}      <!-- pin: bulk  -->
```

- `format` is the SPICE line emitted. `@pinlist` expands to the pins **in the
  order the `B` boxes are declared** — get that order wrong and the netlist is
  silently wrong.
- `template` gives the default parameter values, and can carry expressions
  (`ad="'W * 1.48u'"`) so parasitics scale with W automatically.
- `lvs_format` is a second, simpler line used when netlisting for LVS.
- `spiceprefix=X` makes the device instantiate as a subcircuit rather than a
  primitive — the usual choice when the model is a `.subckt` with parasitics.

The symbol can also display live simulation results; the `tcleval(...)` text
lines pull `gm` and `id` back from ngspice and print them next to the device.

### 3.3 `libs.tech/ngspice/` — the compact models

```
ngspice/
├── design.ngspice        global switches: corner selection, Monte-Carlo flags
├── sm141064.ngspice      the device models themselves
└── sm141064_mim.ngspice  MIM capacitor models
```

The pattern to copy: **one file of switches, one file of models**. A schematic
includes only `design.ngspice`, which sets `sw_stat_global` / corner parameters
and then includes the model file. That is what makes corner runs a one-line
change instead of an edit of the netlist.

### 3.4 `libs.tech/magic/` and `libs.tech/netgen/`

Magic's `.tech` file is a second, independent description of the same layer
stack, used for its own DRC and for extraction. Netgen holds the LVS setup.
**Both are optional for us** — KLayout alone covers layout, DRC, LVS and PCells,
and adding Magic doubles the maintenance for no immediate gain.

### 3.5 `libs.ref/` — the cells

```
libs.ref/gf180mcu_fd_pr/
├── gds/      primitive-device GDS
└── mag/      the same cells in Magic format
```

Naming is `<foundry>_<source>_<type>`: `gf180mcu_fd_pr` = GlobalFoundries 180 MCU,
*foundry-developed*, *primitives*. `_sc_` would be standard cells, `_io_` pads.
For us a single `uci_inrf_pr` (primitives) library is enough to start.

---

## 4. What we already have

### 4.1 The mask set — `TFT/TFT_layout.GDS`

The test chip, 12.5 x 12.5 mm, top cell `TFT_1`, 271 instances. It already
contains a full device matrix plus test structures:

| Cell family | Contents |
|---|---|
| `TFT-{L}L{W}W` | transistors, L in {5, 10, 20, 40, 80, 160} um, W in {10, 50, 100, 500, 1000} um |
| `Test_capacitance` | MIM plate, 400 x 400 um — this is what gave us Cox |
| `Test_TLM-contact` | TLM ladder for contact resistance |
| `Test_GFP-contact`, `Test_mobility` | further test structures |
| `TEXT`, `oxide`, `Alignment` | labels, oxide openings, alignment marks |

**This GDS is the specification of the process geometry.** Everything a PCell
needs to reproduce is already drawn in it.

### 4.2 The layer table — `New folder/LAYOUT/TFT_P1_V9_02162024.lyp`

A working KLayout layer-properties file with eight layers:

| GDS | Name | Present in the GDS? |
|---|---|---|
| 1/0 | Mask | declared, not drawn |
| 2/0 | Gate - Au | yes, 847 polygons |
| 3/0 | Dielectric - Al2O3 | declared, not drawn |
| 4/0 | Semiconductor (IGZO) | yes, 132 |
| 5/0 | oxide etch pattern | yes, 24 |
| 6/0 | SD contact - Au | yes, 701 |
| 7/0 | Dielectric 2 - Al2O3 | declared, not drawn |
| 8/0 | Alignment | yes, 5 |

⚠️ **The `.lyp` has a malformed entry.** Layer 7's `<source>` field reads
`'Dielectric 2 - Al2O3' 7/0@1` — the name was pasted into the source string
instead of the `<name>` element. Fix that before using the file as a PDK asset.

The dielectric layers being declared but not drawn is normal for a blanket ALD
film, but it means **a PCell has to add them explicitly** if DRC is ever to check
dielectric openings.

### 4.3 Measured process parameters

From the extraction work already done (`tft/`, and recorded in
`test1/models/tft_igzo_test1.lib`):

| Quantity | Value | Source |
|---|---|---|
| Gate dielectric | 50 nm Al2O3, eps_r = 8.83 | stated + confirmed by CV |
| Cox | 156.4 nF/cm^2 = 1.564 fF/um^2 | 400x400 um plate, 250.2 pF measured |
| Kp = mu*Cox | 0.717 uA/V^2 (long channel, best chip) | linear and saturation extraction, agree to 0.5 % |
| Mobility | 4.6 cm^2/Vs | Kp / Cox |
| Vth | +0.09 V long channel, down to -1.32 V short | |
| lambda | 0.0067 long channel | Early voltage |
| Gate overlap | 5.0 um per side | measured off the GDS |
| Contact resistance | 2*Rc*W = 6.6e6 Ohm*um | R_on vs L scaling |
| Drawn-to-printed bias | +3 um (drawn 5 um prints as 8 um) | GDS vs measured device |

That last row is a **process design rule in disguise**: any PCell must apply the
bias, or draw-to-print will silently be wrong by 3 um.

---

## 5. What is missing, in build order

### Step 1 — Layer definition (half a day)

Produce `pdk/libs.tech/klayout/tech/igzo.lyt`, `igzo.lyp`, `igzo.map`.

- Start from `New folder/LAYOUT/TFT_P1_V9_02162024.lyp`, fix the layer-7 entry,
  and add `<name>` to every layer.
- Copy the `.lyt` skeleton from `gf180mcuD/libs.tech/klayout/tech/gf180mcu.lyt`.
  Set `<dbu>0.001</dbu>` (the GDS is already on a 1 nm grid) and write the
  `<connectivity>` block for our stack:
  `Gate(2/0)` is one conductor, `SD(6/0)` another, and they are **not** connected
  by a via layer — in a TFT they are separated by the dielectric everywhere
  except where the semiconductor bridges them.
- The `.map` matters only when exporting from another tool; write it last.

### Step 2 — Device PCell (two or three days)

`pdk/libs.tech/klayout/tech/pymacros/cells/tft.py` + `draw_tft.py`, registered by
an `igzo.lym` copied from `gf180mcu.lym`.

Parameters, taken straight from the geometry already in the GDS:

| Parameter | Default | Notes |
|---|---|---|
| `w_gate` | 100 um | device width |
| `l_gate` | 10 um | drawn length; the PCell adds the +3 um bias internally |
| `nf` | 1 | fingers — folds the device, does **not** change fT (measured) |
| `overlap` | 5 um | gate overlap per side; the dominant parasitic |
| `sd_width` | 97.5 um | source/drain electrode, from `TFT-10L100W` |
| `pad` | on/off | the 400x400 um probe pads |

The geometry to reproduce, read out of cell `TFT-10L100W`:

```
layer 4 (IGZO)  : x [-15, 15]      y [-205, -95]     -> island, 30 x 110 um
layer 6 (S/D)   : x [5, 102.5]     y [-200, -100]    -> drain electrode
layer 6 (S/D)   : x [-102.5, -5]   y [-200, -100]    -> source electrode
layer 2 (gate)  : x [-10, 10]      y [-215, 375]     -> gate stripe, 20 um wide
layer 6 (pads)  : 400 x 400 um, both sides
```

Channel length is the gap between the S/D inner edges (10 um here); channel
width is the overlap of the IGZO island with the electrodes (100 um); the gate
stripe overhangs each edge by 5 um. A finger array repeats the S/D pair on a
pitch of `l_gate + 2*overlap + contact`, sharing electrodes between fingers.

Use `gf180mcuD/.../cells/draw_fet.py` as the structural model and
`via_generator.py` for any contact array.

### Step 3 — xschem symbol (half a day)

`pdk/libs.tech/xschem/symbols/tft_igzo.sym`, from a copy of
`gf180mcuD/libs.tech/xschem/symbols/nfet_10v0_asym.sym`:

- Set `format` to emit our model call, and let `template` carry `W`, `L`, `nf`
  and the overlap-derived parasitics as expressions, the same way GF scales
  `ad`/`as` with W.
- Keep four pins (D, G, S, B) even though a TFT has no bulk — leaving the pin
  makes the symbol drop into existing testbenches unchanged; tie it to source in
  the model.
- Add an `xschemrc` that appends our symbol directory to `XSCHEM_LIBRARY_PATH`.

### Step 4 — Model file (already mostly done)

`test1/models/tft_igzo_test1.lib` already holds four extracted corners
(`_BEST`, `_TYP`, `_SHORT`, `_ALL`) plus a contact-resistance subcircuit. To make
it PDK-shaped, split it the way GF does:

- `pdk/libs.tech/ngspice/design.ngspice` — corner switch and includes
- `pdk/libs.tech/ngspice/igzo_tft.ngspice` — the models

⚠️ The model is **DC-validated only**, and the header of the `.lib` records why.
Anything that depends on gate capacitance at RF is not yet trustworthy.

### Step 5 — DRC deck (later)

Only worth writing once the process rules are actually known. The minimum useful
set is reachable from what we have measured: minimum drawn L (the 5 um cell
printed at 8 um, so 5 um drawn is already at the limit), minimum overlap,
minimum electrode spacing, and the alignment tolerance implied by the +3 um bias.
Copy the structure from `gf180mcuD/libs.tech/klayout/tech/drc/`.

---

## 6. Proposed layout of our PDK

```
simulaciones/pdk/
├── libs.tech/
│   ├── klayout/tech/
│   │   ├── igzo.lyt
│   │   ├── igzo.lyp
│   │   ├── igzo.map
│   │   ├── pymacros/
│   │   │   ├── igzo.lym
│   │   │   └── cells/{__init__.py, tft.py, draw_tft.py, cap_mim.py}
│   │   └── drc/
│   ├── xschem/
│   │   ├── xschemrc
│   │   └── symbols/tft_igzo.sym
│   └── ngspice/
│       ├── design.ngspice
│       └── igzo_tft.ngspice
└── libs.ref/
    └── uci_inrf_pr/
        └── gds/        primitives exported from the PCells
```

---

## 7. Reference files worth reading before writing anything

| Purpose | Path |
|---|---|
| Technology file skeleton | `/foss/pdks/gf180mcuD/libs.tech/klayout/tech/gf180mcu.lyt` |
| Layer properties example | `/foss/pdks/gf180mcuD/libs.tech/klayout/tech/gf180mcu.lyp` |
| PCell declaration | `/foss/pdks/gf180mcuD/libs.tech/klayout/tech/pymacros/cells/fet.py` |
| PCell geometry | `/foss/pdks/gf180mcuD/libs.tech/klayout/tech/pymacros/cells/draw_fet.py` |
| Contact-array helper | `.../cells/via_generator.py` |
| Library registration | `.../pymacros/gf180mcu.lym` |
| PCell regression tests | `.../pymacros/testing/pcell_reg_Pytest.py` |
| xschem symbol | `/foss/pdks/gf180mcuD/libs.tech/xschem/symbols/nfet_10v0_asym.sym` |
| xschem library path setup | `/foss/pdks/gf180mcuD/libs.tech/xschem/xschemrc` |
| Corner-switch pattern | `/foss/pdks/gf180mcuD/libs.tech/ngspice/design.ngspice` |
| DRC deck structure | `/foss/pdks/gf180mcuD/libs.tech/klayout/tech/drc/` |
| Simplest complete PDK to imitate | all of `/foss/pdks/gf180mcuD` |

Sky130 is worth a look for one thing GF does not have: `sky130A/libs.tech/klayout/pymacros/sky130_pcells.lym`
shows a second, independent style of PCell registration.

---

## 8. Honest scope note

A PCell and a symbol make the process *drawable* and *simulatable*. They do not
make it *correct*. Two things are still open and should not be hidden inside a
PDK that looks authoritative:

1. **The model has no validated gate capacitance.** Cox is measured, but the
   overlap capacitance rests on a 5 um overlap read off one GDS cell, and the
   model is validated against DC curves only.
2. **The drawn-to-printed bias is +3 um and its spread is unknown.** One sample
   of one cell is not a process characterisation. Until it is measured across
   the wafer, any PCell that silently applies a 3 um correction is asserting more
   than we know.

Both belong in the PDK's own README, not only here.
