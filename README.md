# TFT-MMM-LAB-PDK

An open PDK for the **UCI/INRF IGZO thin-film transistor process**, packaged so
that it is used exactly like the open-source PDKs it sits next to - sky130A,
gf180mcuD, ihp-sg13g2 - in the four tools this lab works with: **klayout,
xschem, ngspice and magic**.

Internally the technology is called `igzo_mmm_lab`.

```
use-pdk TFT-MMM-LAB-PDK     # after ./install.sh - switches all four tools
```

Everything here is derived from things that were measured or drawn: the test
chip `TFT_layout.GDS`, the layer table the masks were made from, and the I-V
and C-V data taken on three fabricated chips. Where a number is an assumption
rather than a measurement, it says so - in the file that carries it, not only
here. Read [What this PDK does not know](#what-this-pdk-does-not-know) before
trusting a simulation.

---

## The process

A **top-gate coplanar IGZO TFT**, four masks, in the order the process runs
them:

| # | Layer | GDS | What it is |
|---|-------|-----|------------|
| 1 | `igzo`   | 4/0 | semiconductor island, deposited first |
| 2 | `sd`     | 6/0 | Au source/drain, directly on the IGZO - the contact **is** the overlap |
| 3 | `oxetch` | 5/0 | openings in the blanket 50 nm Al2O3. A probe window where nothing covers it; a **via** where gate metal does |
| 4 | `gate`   | 2/0 | Au gate, last metal, above the dielectric |
|   | `align`  | 8/0 | alignment marks |
|   | `text`   | 63/0 | annotation - what a cell prints about itself. Never fabricated |

The gate is deposited *after* the dielectric etch, so an opening covered by
gate metal shorts the two metals together. That is the process's only via, and
it is what lets a spiral inductor bring its inner end out.

The gate dielectric has no mask of its own: it is a blanket ALD film, and only
its openings are drawn. Datatype 10 on the two conductors is a pin purpose and
datatype 20 a label purpose.

### What was measured

| Quantity | Value | How |
|---|---|---|
| Gate dielectric | 50 nm Al2O3, eps_r = 8.83 | stated, confirmed by C-V |
| Cox | 156.4 nF/cm² = **1.564 fF/µm²** | 400 × 400 µm plate of `Test_capacitance`, 250.2 pF measured |
| Kp = µCox | 0.717 µA/V² long channel | linear and saturation extraction agree to 0.5 % |
| Mobility | 4.6 cm²/Vs | Kp / Cox |
| Vth | +0.09 V long channel, down to −1.32 V short | |
| lambda | 0.0067 long channel | Early voltage |
| Contact resistance | 2·Rc·W = 6.6 MΩ·µm | R_on against L |
| Gate overlap | 5.0 µm per side | measured off the GDS, consistent across L |
| Drawn-to-printed bias | +3 µm (drawn 5 µm prints as 8 µm) | one GDS cell against one measured device |

---

## Install

```bash
git clone git@github.com:Juander28/TFT-MMM-LAB-PDK.git
cd TFT-MMM-LAB-PDK
./install.sh
# open a new shell, then
use-pdk TFT-MMM-LAB-PDK
```

`install.sh` builds a writable `PDK_ROOT` at `~/pdks` holding symlinks to every
PDK in `/foss/pdks` plus this one, and adds a `use-pdk` function to
`~/.bashrc`. Nothing is copied and the vendor PDKs keep working unchanged;
`use-pdk gf180mcuD` switches back.

This indirection exists because `/foss/pdks` belongs to root and cannot be
written by the `designer` account. With a root shell in the container,

```bash
ln -s /path/to/TFT-MMM-LAB-PDK /foss/pdks/TFT-MMM-LAB-PDK
```

puts it literally beside the others; `install.sh` does that by itself whenever
`/foss/pdks` happens to be writable.

Verify the whole thing across the four tools at any time:

```bash
./scripts/run_checks.sh
```

---

## Using it

### klayout - layout, PCells, DRC

The technology `igzo_mmm_lab` appears in the technology selector, and the
library **`igzo_mmm_lab_pr`** in the library browser, with three PCells:

- **`tft_igzo`** - the transistor. `w_gate`, `l_gate`, `nf`, `gate_ov`,
  `sd_len`, `pad`. Defaults reproduce the fabricated `TFT-10L100W` shape for
  shape; the regression test asserts exactly that.
- **`cap_mim`** - the S/D-metal / Al2O3 / gate-metal overlap capacitor, the
  structure Cox came from. Size it by dimensions, by area, or by the
  capacitance you need - the other two are read back - and it prints its own
  value on the layout.
- **`ind_igzo`** - a planar inductor: square or circular, one spiral in series
  or n concentric rings in parallel, on either gold. It estimates series L and
  series R through `tools/coil_core.py` and prints them on itself. Read the
  cell SOP before believing them: at the 50 nm of gold the process is assumed
  to have, Q is 0.03 at 100 MHz.

`l_gate` is the **drawn** length. The PCell reports `l_printed = l_gate +
l_bias` as a read-only parameter and never bakes the bias into the geometry - a
mask generator draws the mask.

DRC:

```bash
python3 libs.tech/klayout/tech/drc/run_drc.py --path <layout.gds> --topcell <cell>
```

### xschem - schematic

`symbols/tft_igzo.sym`, pins **D G S** in that order - three terminals, no
bulk, because a TFT sits on glass. `symbols/cap_mim.sym` and
`symbols/ind_igzo.sym` are two-pin passives. `W`, `L` and `ov` are drawn
dimensions in metres.

Testbenches: `tests/tft_iv.sch` sweeps the measured device, and
`tests/tank_ac.sch` puts all three cells together as a 100 MHz tuned load.

### ngspice - simulation

```spice
.include $PDK_ROOT/$PDK/libs.tech/ngspice/design.ngspice
.lib     $PDK_ROOT/$PDK/libs.tech/ngspice/igzo_mmm_lab.ngspice tt
XM1 d g s b igzo_tft W=100u L=10u ov=5u
```

Corners: `tt`, `best`, `short`, `all`. The wrapper `igzo_tft` adds the measured
contact resistance (3.3 Ω·m / W per contact) and the overlap capacitance
(Cox·ov·W per side) around a level-1 core, so `ov` can be swept - which is the
point, because the overlap is what decides whether a tuned stage works.

### magic - layout and extraction

```bash
magic -rcfile $PDK_ROOT/$PDK/libs.tech/magic/igzo_mmm_lab.magicrc
```

Reads and writes the four-mask GDS, extracts `igzo_tft` devices, and its
`.mag` device views live in `libs.ref/igzo_mmm_lab_pr/mag/`. LVS closes against
the xschem netlist through `libs.tech/netgen/setup.tcl`.

---

## What this PDK does not know

1. **The models are DC-only.** They reproduce the measured output curves -
   median simulated/measured = 1.01 over 18 devices - and nothing else has been
   checked. Cox is measured, but the overlap capacitance rests on a 5 µm
   overlap read off one GDS cell and no C-V or S-parameter measurement backs
   the AC behaviour. Do not trust an RF loading number from this model yet.
2. **Level 1 imposes a square law.** The measured saturation exponent is
   gamma = 2.31, so the model runs about 20 % pessimistic on gm at a given
   current. Valid range: VGS ≤ 6 V, VDS ≤ 10 V.
3. **The +3 µm drawn-to-printed bias is one sample.** Its spread across a wafer
   is unknown, which is why the PCell reports it instead of applying it.
4. **The DRC deck is preliminary.** Every rule is either measured or read off
   the test chip; there is no foundry rule document. 5 µm is the minimum drawn
   dimension because the smallest drawn device is 5 µm and it prints at 8 µm -
   that is the edge of what the process has been shown to do, not a comfortable
   minimum. Running the deck over the fabricated chip is instructive:
   - the transistor matrix is clean **except** the 5 µm cells, which are drawn
     with 3.5 µm of gate overlap instead of 5 µm;
   - `Test_capacitance` is clean;
   - `Test_mobility` violates several rules - it is a measurement structure,
     drawn before any rules existed.
5. **Extracted width is not drawn width.** Magic measures the gated island, and
   the island is drawn 5 µm past each electrode end for alignment margin, so
   extraction reports about 13 % more width than the device has. `l` extracts
   exactly. `libs.tech/netgen/setup.tcl` allows 20 % on `w` and 1 % on `l`, and
   says why. Drawing the island flush with the electrodes makes it exact.
6. **TFT2 is not represented.** Its saturation exponent comes out at 0.87,
   which no square-law model can express. Treat that chip as anomalous.

---

## Layout of the repository

```
tools/                     shared code, so the repository stands alone
├── coil_core.py           the coil physics, from the coil calculator
├── xls_reader.py          reads the measurement .xls
├── pdk_paths.py           the one place that knows where anything is
└── coil_calculator/       the GUI calculators
libs.tech/                 tool-specific
├── klayout/tech/          igzo_mmm_lab.{lyt,lyp,map}, PCells, DRC deck
├── xschem/                symbol, xschemrc, testbenches
├── ngspice/               design.ngspice (wrappers), igzo_mmm_lab.ngspice (corners)
├── magic/                 igzo_mmm_lab.{tech,magicrc}
└── netgen/                LVS setup
libs.ref/igzo_mmm_lab_pr/  design-specific
├── gds/                   TFT_layout.gds (the test chip), tft_primitives.gds
└── mag/                   magic views of the device matrix
docs/                      PDK_GUIDE.md, extraction/, figures/, bibliography/,
                           and pdf/ - the generators for the five documents
measurements/              the measured .xls: present locally, never in git
scripts/                   library generation and the end-to-end checks
measurements/              drop point for raw data - not tracked, see its README
```

The device matrix, the GDS primitives and the magic views are all **generated**
from the PCells:

```bash
python3 scripts/build_libs_ref.py     # PCells -> tft_primitives.gds
./scripts/build_mag_views.sh          # that GDS -> libs.ref/.../mag/*.mag
```

There is one description of the geometry - the PCell - and everything else is
derived from it, so the views cannot drift apart. Do not hand-edit the `.mag`
files.

---

## The documents

Five, each in English and Spanish, generated by `docs/pdf/` and written to
`~/Documents/PDK-TFT-MMM-LAB/docs` (reachable from the designs mount as
`/foss/designs/Documents/PDK-TFT-MMM-LAB`):

| Document | What it is |
|---|---|
| Cells and tools | what the PDK contains and how it looks in each tool; how to activate it and switch between PDKs |
| Cell SOP | every parameter of every cell, and where its default came from - measured, off the chip, assumed, or your choice |
| Model vs measurement | simulated against measured curves, the extraction spread, contact resistance, Cox, and what to measure next |
| Overview deck | eleven slides: what was built, every parameter with an arrow pointing at it, model against measurement |
| Capabilities and limits | what can honestly be designed here and what cannot, with fT, the gm lost to the contacts, and the ceiling in numbers |

```bash
cd docs/pdf
./make_figures.sh
python3 make_pdf.py && python3 make_sop.py && python3 make_model_report.py
python3 make_slides.py && python3 make_capabilities.py
```

`docs/bibliography/` carries the literature behind the model's magnetic-field
term - what is published, what each paper would predict for a device with our
mobility, and why a field applied while the film is grown is a different
subject from a field applied while the transistor runs. Its open-access PDFs
are fetched by `docs/bibliography/fetch_pdfs.sh`, not tracked.

PDFs are not tracked here: they are output, and this repository carries what
they are made from - including the raw measurements, locally, untracked.

## Provenance and licence

The structure of every tech file here follows the corresponding file in
**gf180mcuD** (Apache-2.0, GlobalFoundries PDK Authors), which is the clearest
worked example of this problem in the open. Each file names the one it came
from. This repository is Apache-2.0 as well.

Process and measurements: UCI/INRF, MMM Lab.
`docs/PDK_GUIDE.md` is the design document this PDK was built from.
