v {xschem version=3.4.5 file_version=1.2

* IGZO TFT in a magnetic field - UCI/INRF process (igzo_mmm_lab)
*
* Five identical devices at the same bias.  The only thing that differs is
* what magnetic field the model is told about:
*
*   XREF    B = 0                     the reference
*   XB1     B = 1 T,  b_scale = 1     classical magnetoresistance, as-is
*   XB278   B = 1 T,  b_scale = 278
*   XB1K    B = 1 T,  b_scale = 1000
*   XB2K2   B = 1 T,  b_scale = 2181
*
* THE MODEL.  design.ngspice divides the intrinsic width by
*
*     mr = 1 + (mu_corner * b_scale * B)^2
*
* Level 1 only ever uses the product Kp*W/L, so dividing W is the same as
* dividing the mobility.  mr = 1 at B = 0, so a netlist that says nothing
* about magnetic fields behaves exactly as it did before this term existed.
*
* THE RESULT, WHICH IS A NEGATIVE ONE.  At the measured mobility of
* 4.6 cm^2/Vs, mu*B at one tesla is 4.6e-4, so (mu*B)^2 = 2.1e-7: two parts
* in ten million.  This netlist returns 9.6e-8 of relative current change at
* one tesla.  Classical magnetoresistance in this material is NOT measurable
* and cannot be the basis of a sensor.  That is the answer, not a failure to
* find one.
*
* WHICH IS WHY b_scale EXISTS.  It is the ratio of a measured effect to the
* classical one, and the sweep above is the useful form of the question: how
* far from classical would a real effect have to sit before a circuit noticed?
*   b_scale =  278  ->  0.7 % of current
*   b_scale = 1000  ->  8.7 %
*   b_scale = 2181  ->  30 %
* About 320 buys one percent.  If the laboratory measures a change in Kp under
* a field - and it reports that it does - then whatever causes it is not this
* term, and b_scale is where that measurement goes until it is understood.
*
* NUMERICS.  reltol=1e-10 abstol=1e-16 is not optional here.  The classical
* effect is nine significant figures down; at ngspice's default tolerances it
* is indistinguishable from convergence noise.
*
* NOT MODELLED.  The Hall voltage - the transverse one, which is what a real
* magnetometer is built from - and any shift of Vth with field.  See
* docs/bibliography/ for what the literature does and does not support.
}
G {}
K {}
V {}
S {}
E {}
B 2 20 80 700 420 {flags=graph
y1=0
y2=0.0007
ypos1=0
ypos2=2
divy=5
subdivy=1
unity=u
x1=0
x2=6
divx=5
subdivx=1
unitx=1
dataset=-1
autoload=1
rawfile=$netlist_dir/tft_bfield.raw
sim_type=dc
logx=0
logy=0
color="4 6 7 8 9"
node="i(iref)
i(ib1)
i(ib278)
i(ib1k)
i(ib2k2)"
hilight_wave=-1
}
B 2 740 80 1420 420 {flags=graph
y1=-0.02
y2=0.35
ypos1=0
ypos2=2
divy=5
subdivy=1
unity=1
x1=0
x2=6
divx=5
subdivx=1
unitx=1
dataset=-1
autoload=1
rawfile=$netlist_dir/tft_bfield.raw
sim_type=dc
logx=0
logy=0
color="6 7 8 9"
node="rel1
rel278
rel1k
rel2k2"
hilight_wave=-1
}
N 130 -490 130 -440 {
lab=DREF}
N 50 -410 90 -410 {
lab=G}
N 130 -380 130 -310 {
lab=S}
N 330 -490 330 -440 {
lab=DB1}
N 250 -410 290 -410 {
lab=G}
N 330 -380 330 -310 {
lab=S}
N 530 -490 530 -440 {
lab=DB278}
N 450 -410 490 -410 {
lab=G}
N 530 -380 530 -310 {
lab=S}
N 730 -490 730 -440 {
lab=DB1K}
N 650 -410 690 -410 {
lab=G}
N 730 -380 730 -310 {
lab=S}
N 930 -490 930 -440 {
lab=DB2K2}
N 850 -410 890 -410 {
lab=G}
N 930 -380 930 -310 {
lab=S}
C {devices/code_shown.sym} 20 -160 0 0 {name=MODELS only_toplevel=true
format="tcleval( @value )"
value="
.include $::IGZO_MODELS/design.ngspice
.lib $::IGZO_MODELS/igzo_mmm_lab.ngspice best
"}
C {devices/lab_pin.sym} 50 -410 0 0 {name=l1 sig_type=std_logic lab=G}
C {devices/lab_pin.sym} 130 -490 0 0 {name=l2 sig_type=std_logic lab=DREF}
C {devices/lab_pin.sym} 130 -310 0 0 {name=l3 sig_type=std_logic lab=S}
C {devices/lab_pin.sym} 250 -410 0 0 {name=l4 sig_type=std_logic lab=G}
C {devices/lab_pin.sym} 330 -490 0 0 {name=l5 sig_type=std_logic lab=DB1}
C {devices/lab_pin.sym} 330 -310 0 0 {name=l6 sig_type=std_logic lab=S}
C {devices/lab_pin.sym} 450 -410 0 0 {name=l7 sig_type=std_logic lab=G}
C {devices/lab_pin.sym} 530 -490 0 0 {name=l8 sig_type=std_logic lab=DB278}
C {devices/lab_pin.sym} 530 -310 0 0 {name=l9 sig_type=std_logic lab=S}
C {devices/lab_pin.sym} 650 -410 0 0 {name=l10 sig_type=std_logic lab=G}
C {devices/lab_pin.sym} 730 -490 0 0 {name=l11 sig_type=std_logic lab=DB1K}
C {devices/lab_pin.sym} 730 -310 0 0 {name=l12 sig_type=std_logic lab=S}
C {devices/lab_pin.sym} 850 -410 0 0 {name=l13 sig_type=std_logic lab=G}
C {devices/lab_pin.sym} 930 -490 0 0 {name=l14 sig_type=std_logic lab=DB2K2}
C {devices/lab_pin.sym} 930 -310 0 0 {name=l15 sig_type=std_logic lab=S}
C {symbols/tft_igzo.sym} 110 -410 0 0 {name=XREF
W=1000u
L=8u
ov=5u
nf=1
m=1
B=0
b_scale=1
model=igzo_tft
spiceprefix=X
}
C {symbols/tft_igzo.sym} 310 -410 0 0 {name=XB1
W=1000u
L=8u
ov=5u
nf=1
m=1
B=1
b_scale=1
model=igzo_tft
spiceprefix=X
}
C {symbols/tft_igzo.sym} 510 -410 0 0 {name=XB278
W=1000u
L=8u
ov=5u
nf=1
m=1
B=1
b_scale=278
model=igzo_tft
spiceprefix=X
}
C {symbols/tft_igzo.sym} 710 -410 0 0 {name=XB1K
W=1000u
L=8u
ov=5u
nf=1
m=1
B=1
b_scale=1000
model=igzo_tft
spiceprefix=X
}
C {symbols/tft_igzo.sym} 910 -410 0 0 {name=XB2K2
W=1000u
L=8u
ov=5u
nf=1
m=1
B=1
b_scale=2181
model=igzo_tft
spiceprefix=X
}
C {devices/code_shown.sym} 1100 -490 0 0 {name=NGSPICE only_toplevel=true
value="
vref  dref  0 10
vb1   db1   0 10
vb278 db278 0 10
vb1k  db1k  0 10
vb2k2 db2k2 0 10
vg g 0 6
vs s 0 0
.options reltol=1e-10 abstol=1e-16
.control
op
let i0    = -i(vref)
let d1    = (i0 - (-i(vb1)))/i0
let d278  = (i0 - (-i(vb278)))/i0
let d1k   = (i0 - (-i(vb1k)))/i0
let d2k2  = (i0 - (-i(vb2k2)))/i0
print i0
print d1
print d278 d1k d2k2

* The same five devices as curves, so the schematic has something to show.
* The prints above have already happened, in the operating-point plot; this
* sweep starts a new one, and it is the one that gets written.
dc vg 0 6 0.02
let iref  = -i(vref)
let ib1   = -i(vb1)
let ib278 = -i(vb278)
let ib1k  = -i(vb1k)
let ib2k2 = -i(vb2k2)

* Relative change against the zero-field device.  The 1e-18 keeps the
* division alive below threshold, where every current is exactly zero.
let rel1   = (iref - ib1)  /(iref + 1e-18)
let rel278 = (iref - ib278)/(iref + 1e-18)
let rel1k  = (iref - ib1k) /(iref + 1e-18)
let rel2k2 = (iref - ib2k2)/(iref + 1e-18)
write tft_bfield.raw

* Left graph: the five currents, which lie on top of each other - that IS
* the classical result.  Right graph: the relative change, where only the
* deliberately exaggerated b_scale values lift off zero at all.
if $?batchmode = 0
  plot iref ib1 ib278 ib1k ib2k2
  plot rel1 rel278 rel1k rel2k2
end
.endc
"}
C {devices/title.sym} 160 -30 0 0 {name=l16 author="UCI/INRF - MMM Lab"}
C {devices/launcher.sym} 1460 40 0 0 {name=hw
descr="Ctrl-click here to load or unload the waveforms by hand.
The graphs load themselves after a simulation; this is for
looking at a run made earlier."
tclcommand="
xschem raw_read $netlist_dir/[file tail [file rootname [xschem get current_name]]].raw
"
}
