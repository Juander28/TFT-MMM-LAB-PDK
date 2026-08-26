# Magnetic fields and thin-film transistors — what the literature actually says

Background for the magnetic-field term in the device model
(`libs.tech/ngspice/design.ngspice`, parameters `B` and `b_scale`), collected
because the lab is measuring a reduction in Kp under an applied field and
wants to read that change as a sensor output through the transconductance of
an amplifier.

Read the arithmetic first. It decides how to interpret every measurement that
follows, and it is not encouraging for the mechanism people usually assume.

---

## The magnitude problem, before anything else

Our measured field-effect mobility is **µ = 4.58 cm²/V·s** (best corner,
Kp/Cox). Everything below scales with the dimensionless product **µB**:

| At B = 1 T | value | what it is |
|---|---|---|
| µB | 4.58 × 10⁻⁴ | the Hall angle, in radians |
| (µB)² | **2.1 × 10⁻⁷** | classical magnetoresistance, ΔG/G |
| µB | **4.6 × 10⁻⁴ /T = 0.046 %/T** | the largest *linear* response available, and only with a split drain |

Classical magnetoresistance — µ(B) = µ/(1 + (µB)²), the term the model
carries — is **two parts in ten million per tesla**. It is not a sensor; at
our mobility it is not even a measurable effect. A 1 % change in Kp would
need µB ≈ 0.1, i.e. µ ≈ 1000 cm²/V·s at 1 T, or 4.6 cm²/V·s at 220 T.

So: **if the lab measures a reduction in Kp under a field, classical
magnetoresistance is not what caused it.** That is a finding, not a nuisance.
Before the number goes into a model, rule out the ordinary explanations —
temperature drift during the measurement (Kp moves far more with a degree of
self-heating than with a tesla), mechanical stress from the magnet or the
probe station, bias stress and hysteresis between successive sweeps, contact
resistance drift, and the field acting on the *instrument* rather than the
device. Measure with the field reversed: a real magnetic effect on the
mobility is even in B, an artefact usually is not.

---

## Group 1 — field during *fabrication*: real, published, and a different subject

The best-cited work on IGZO and magnetic fields applies the field **while the
film is being made**, not while the transistor operates. Static and rotating
fields align magnetic moments and strengthen metal–oxygen bonds at low process
temperature, which raises mobility permanently.

- **Park et al., ACS Appl. Mater. Interfaces 10(19), 16613–16622 (2018)**,
  doi:10.1021/acsami.8b02433 — static and rotating fields during
  low-temperature activation; a rotating field at 1150 rpm gives µ_FE =
  12.68 cm²/V·s and S.S. = 0.37 V/dec, comparable to or better than a 300 °C
  anneal.

  *What it predicts for our device:* nothing about operation. It is a process
  option — if the lab has a magnet, annealing under it may raise Kp
  permanently. That is a fabrication experiment, and it would change the model
  card, not add a term to it.

Do not let this group blur into the next one. It is the most common confusion
in this literature.

---

## Group 2 — field during *operation*: the relevant group

### 2a. Quantum interference in a-IGZO — the one paper at our mobility

- **Wang et al., Appl. Phys. Lett. 110, 022106 (2017)**, doi:10.1063/1.4974080,
  open access as arXiv:1703.04007 — magnetoconductivity of an a-IGZO TFT with
  **µ = 5.6 cm²/V·s, V_T = 1.4 V, S.S. = 0.45 V/dec**: within measurement
  scatter, our device. Weak localization below B ≈ 0.035 T on top of weak
  antilocalization at higher field, the two in competition and tunable with
  the gate. Measured **from 1.5 K to 40 K**, B from 0 to 0.2 T. At 40 K the
  conductivity change over the whole sweep is 1.3 × 10⁻⁶ e²/h — of order a
  percent of that device's channel conductance, and already washing out as the
  temperature rises.

  *What it predicts for our device:* a percent-level field response exists in
  exactly this material at exactly this mobility — **at liquid-helium
  temperatures**. The phase coherence length that carries it goes as T^(−3/4);
  by 40 K the feature is a plateau and at 300 K there is nothing left. If the
  lab measures a room-temperature effect, this is not it either, but it is the
  closest published mechanism and the right one to argue against.

- **Wang et al., Appl. Phys. Express 10, 051103 (2017)**,
  doi:10.7567/APEX.10.051103, open access as arXiv:1705.05010 — the same
  competition across several devices, collapsing onto a universal function of
  channel conductivity. Useful because it says the effect is a property of the
  conduction state, not of one sample.

- **arXiv:1712.07618** — weak localization and antilocalization in a
  double-gate a-IGZO TFT, i.e. the same physics with the carrier density set
  independently of the field. Same temperature range, same conclusion.

### 2b. Split-drain MAGFETs — the linear route, and what it would cost

A transistor whose drain is split in two reports the Lorentz deflection of the
channel current as a **current imbalance**, which is linear in B and in µ —
not quadratic. This is the only field-effect device geometry with a
respectable sensitivity, and every one of them needs that fourth terminal.

- **Rodriguez-Torres, Gutierrez-Dominguez, Klima & Selberherr, IEEE Trans.
  Electron Devices 51, 2237–2245 (2004)**, doi:10.1109/ted.2004.839869 — the
  standard analysis: the response comes from the roll-off of the induced Hall
  potential along the channel, the charge-redistribution contribution is
  minor, and ΔI_D/I_D is linear in B and largely independent of geometry.

- **García-Ramírez & Sandoval-Ibarra, J. Appl. Res. Technol. 2(1), 37–43
  (2004)**, open access — sensitivity plotted directly against carrier
  mobility and temperature, over µ = 10² to 10⁵ cm²/V·s. Detects below 1 mT at
  77 K, where silicon's mobility is high; the sensitivity falls with µ all the
  way down the axis. Reported silicon MAGFET sensitivities elsewhere run
  3.8 %/T to about 12 %/T at room temperature.

- **Zhao, Wen, Lü, Guan & Liu, J. Semicond. 35(9), 094004 (2014)**,
  doi:10.1088/1674-4926/35/9/094004 — a split-drain MAGFET built on a
  **nano-polysilicon TFT**, i.e. the idea carried out of crystalline silicon
  and into thin-film technology. The nearest published thing to what the lab
  is proposing.

  *What all three predict for our device:* extrapolating their sensitivity to
  µ = 4.6 cm²/V·s gives roughly **0.05 %/T** — the µB row of the table above,
  reached from measurement rather than from theory, which is why the agreement
  is worth something. That is 2000× larger than the magnetoresistance the
  model carries, and it is the honest ceiling for a Lorentz-force sensor in
  this technology. It needs a split drain, so the wrapper's three-terminal
  device cannot express it.

### 2c. Hall measurements on amorphous oxides

- **Joo, Kim, Cha & Song, Micromachines 11(9), 822 (2020)**,
  doi:10.3390/mi11090822, open access — Hall voltage in InGaZnO films, linear
  in B from −0.4 T to +0.4 T as classical theory says, with a non-zero offset
  at B = 0 that they read as a conduction-band-edge profile.

  *What it predicts for our device:* the Hall response is classical, linear
  and small, and the offset at zero field is the practical obstacle — an
  offset drifting with temperature or bias looks exactly like a signal.

---

## Where this leaves the model

The wrapper carries µ(B) = µ/(1 + (µ·b_scale·B)²), with µ taken from the
active corner's own Kp/Cox, and `B = 0` by default so every existing netlist
is untouched. `b_scale` is dimensionless and defaults to 1, i.e. pure
classical behaviour. When the lab has a measured coefficient, set

    b_scale = sqrt( (measured ΔG/G at 1 T) / (µB)² ) = sqrt(measured / 2.1e-7)

and the model reproduces the measurement without anyone editing the corner
files. A measured 1 % per tesla would put `b_scale` near 220 — a number worth
writing down, because it is also the factor by which the measurement would
exceed the physics the term is named after.

No mechanism is asserted beyond the classical one. Naming a cause without
evidence would be worse than leaving the hook.

---

## The PDFs

`pdf/` holds the open-access papers (arXiv preprints and open journals). They
are **not tracked in git** — this repository does not carry PDFs — so run

    ./fetch_pdfs.sh

to pull them down again on a fresh clone. Everything paywalled stays as a DOI
in `magnetic_tft.bib` and in the tables above.
