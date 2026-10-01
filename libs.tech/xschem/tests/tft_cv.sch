v {xschem version=3.4.5 file_version=1.2

* IGZO TFT parasitic capacitance - UCI/INRF process (igzo_mmm_lab)
*
* Four identical devices that differ only in gate overlap:
*
*   XOV0    ov =  0        no overlap at all - what level 1 alone contributes
*   XOV2    ov =  2 um
*   XOV5    ov =  5 um     the overlap measured off the GDS, the PCell default
*   XOV10   ov = 10 um
*
* Cgg is read as -Im(Ig)/omega with 1 V of AC on the gate, swept from 1 kHz
* to 1 GHz.
*
* WHAT THIS TEST PROVES.  At low frequency,
*
*     Cgg(ov=5u) - Cgg(ov=0) = 15.64 pF = 2 * cox_area * ov * W
*
* exactly, which is the overlap the wrapper in design.ngspice puts there by
* hand.  That is the one capacitance in this PDK with a measurement behind it
* (Cox = 1.564 fF/um^2, from the 400 x 400 um plate).
*
* WHAT IT ALSO PROVES, AND MATTERS MORE.  The overlap does not stay there.
* The wrapper puts Cgd and Cgs on the INTERNAL nodes, behind the contact
* resistances, and 3.3 kOhm against 7.82 pF is a pole at about 6 MHz.  The
* difference above is 15.64 pF at 1 kHz, 13.6 pF at 1 MHz, and by 10 MHz it
* has gone through zero: the network stops behaving like a capacitor at all.
* This is the same contact that dominates tft_transfer.sch, seen from the AC
* side, and it is why an RF loading number from this model cannot be trusted.
*
* WHAT IS NOT MEASURED.  Cgg(ov=0) is about 12.5 pF and it is level 1's
* channel capacitance, derived from Tox = 22.1 nm - which is an SiO2-EQUIVALENT
* thickness chosen to reproduce Cox, not the 50 nm of Al2O3 that is actually
* there.  No C-V or S-parameter measurement backs any of it.  The overlap
* difference is trustworthy; the absolute value is not.
}
G {}
K {}
V {}
S {}
E {}
B 2 20 80 1000 420 {flags=graph
y1=-5e-12
y2=4e-11
ypos1=0
ypos2=2
divy=5
subdivy=1
unity=p
x1=3
x2=9
divx=5
subdivx=1
unitx=1
dataset=-1
autoload=1
rawfile=$netlist_dir/tft_cv.raw
sim_type=ac
logx=1
logy=0
color="4 6 7 8"
node="cgg0
cgg2
cgg5
cgg10"
hilight_wave=-1
}
N 130 -490 130 -440 {
lab=D0}
N 50 -410 90 -410 {
lab=G0}
N 130 -380 130 -310 {
lab=0}
N 330 -490 330 -440 {
lab=D2}
N 250 -410 290 -410 {
lab=G2}
N 330 -380 330 -310 {
lab=0}
N 530 -490 530 -440 {
lab=D5}
N 450 -410 490 -410 {
lab=G5}
N 530 -380 530 -310 {
lab=0}
N 730 -490 730 -440 {
lab=D10}
N 650 -410 690 -410 {
lab=G10}
N 730 -380 730 -310 {
lab=0}
C {devices/code_shown.sym} 20 -160 0 0 {name=MODELS only_toplevel=true
format="tcleval( @value )"
value="
.include $::IGZO_MODELS/design.ngspice
.lib $::IGZO_MODELS/igzo_mmm_lab.ngspice best
"}
C {devices/lab_pin.sym} 50 -410 0 0 {name=l1 sig_type=std_logic lab=G0}
C {devices/lab_pin.sym} 130 -490 0 0 {name=l2 sig_type=std_logic lab=D0}
C {devices/gnd.sym} 130 -310 0 0 {name=l3 lab=0}
C {devices/lab_pin.sym} 250 -410 0 0 {name=l4 sig_type=std_logic lab=G2}
C {devices/lab_pin.sym} 330 -490 0 0 {name=l5 sig_type=std_logic lab=D2}
C {devices/gnd.sym} 330 -310 0 0 {name=l6 lab=0}
C {devices/lab_pin.sym} 450 -410 0 0 {name=l7 sig_type=std_logic lab=G5}
C {devices/lab_pin.sym} 530 -490 0 0 {name=l8 sig_type=std_logic lab=D5}
C {devices/gnd.sym} 530 -310 0 0 {name=l9 lab=0}
C {devices/lab_pin.sym} 650 -410 0 0 {name=l10 sig_type=std_logic lab=G10}
C {devices/lab_pin.sym} 730 -490 0 0 {name=l11 sig_type=std_logic lab=D10}
C {devices/gnd.sym} 730 -310 0 0 {name=l12 lab=0}
C {symbols/tft_igzo.sym} 110 -410 0 0 {name=XOV0
W=1000u
L=8u
ov=0
nf=1
m=1
model=igzo_tft
spiceprefix=X
}
C {symbols/tft_igzo.sym} 310 -410 0 0 {name=XOV2
W=1000u
L=8u
ov=2u
nf=1
m=1
model=igzo_tft
spiceprefix=X
}
C {symbols/tft_igzo.sym} 510 -410 0 0 {name=XOV5
W=1000u
L=8u
ov=5u
nf=1
m=1
model=igzo_tft
spiceprefix=X
}
C {symbols/tft_igzo.sym} 710 -410 0 0 {name=XOV10
W=1000u
L=8u
ov=10u
nf=1
m=1
model=igzo_tft
spiceprefix=X
}
C {devices/code_shown.sym} 900 -490 0 0 {name=NGSPICE only_toplevel=true
value="
vg0  g0  0 dc 3 ac 1
vg2  g2  0 dc 3 ac 1
vg5  g5  0 dc 3 ac 1
vg10 g10 0 dc 3 ac 1
vd0  d0  0 0
vd2  d2  0 0
vd5  d5  0 0
vd10 d10 0 0
.control
save all
ac dec 20 1k 1g
let w = 2*pi*frequency
let cgg0  = -imag(i(vg0))/w
let cgg2  = -imag(i(vg2))/w
let cgg5  = -imag(i(vg5))/w
let cgg10 = -imag(i(vg10))/w

* the overlap, isolated: it must equal 2 * cox_area * ov * W
let dov2  = cgg2  - cgg0
let dov5  = cgg5  - cgg0
let dov10 = cgg10 - cgg0
meas ac d2_lo  FIND dov2  AT=1k
meas ac d5_lo  FIND dov5  AT=1k
meas ac d10_lo FIND dov10 AT=1k
let predicted5 = 2*1.564e-3*5e-6*1000e-6
print predicted5

* and the same overlap as the contact carries it away with frequency
meas ac d5_1m  FIND dov5 AT=1meg
meas ac d5_10m FIND dov5 AT=10meg

* the part level 1 invents, for which there is no measurement
meas ac c_channel FIND cgg0 AT=1k
write tft_cv.raw

* Four gate capacitances against frequency, one per overlap.  They start
* 6.3 pF apart per 2 um of overlap and end up on top of each other - and
* below zero - once the contact resistance has taken them.
if $?batchmode = 0
  plot cgg0 cgg2 cgg5 cgg10
  plot dov5
end
.endc
"}
C {devices/title.sym} 160 -30 0 0 {name=l13 author="UCI/INRF - MMM Lab"}
C {devices/launcher.sym} 1040 40 0 0 {name=hw
descr="Ctrl-click here to load or unload the waveforms by hand.
The graphs load themselves after a simulation; this is for
looking at a run made earlier."
tclcommand="
xschem raw_read $netlist_dir/[file tail [file rootname [xschem get current_name]]].raw
"
}
