v {xschem version=3.4.5 file_version=1.2

* Gate capacitance WITH the semiconductor - ESTIMATED, not measured
*
* Four devices, same geometry, differing only in what their gate capacitance
* is allowed to see:
*
*   XOXIDE  igzo_tft      the measured PDK: the oxide, and nothing else
*   XDEPL   igzo_tft_cv   oxide in series with a fully depleted 30 nm IGZO
*   XACC    igzo_tft_cv   channel accumulated - tends back to the oxide
*   XTHIN   igzo_tft_cv   the same, with a 15 nm film instead of 30 nm
*
* WHY THIS EXISTS.  The measured PDK knows Cox, from the 400 x 400 um plate,
* and knows nothing about the semiconductor's own capacitance, because no C-V
* has been taken on a transistor.  libs.tech/ngspice/igzo_cv_estimated.ngspice
* supplies an estimate built from published a-IGZO values so that a circuit
* can be simulated before the measurement exists - and so the measurement,
* when it arrives, has a prediction to be compared against.
*
* NOTHING HERE IS MEASURED ON THIS PROCESS.  eps_igzo = 16 is from the
* literature; t_igzo = 30 nm is this PDK's own stated film thickness.
*
* WHAT IT SAYS.  With the channel depleted the gate sees about 86 % of what
* the oxide alone would give: 24.2 pF against 28.1 pF on the validated
* device.  With the channel accumulated it returns to the oxide value.  A
* real device lives between those two and moves with VGS; this brackets it.
*
* HOW TO READ THE ANSWER WHEN THE MEASUREMENT COMES IN.  If the measured C-V
* is flat at Cox across bias, the film is more conductive than assumed and
* the estimate is pessimistic.  If it sits near the depleted value and stays
* there, the channel is not accumulating and something is wrong with the
* interface.  Either outcome is worth knowing before designing an AC stage.
}
G {}
K {}
V {}
S {}
E {}
B 2 20 80 1000 420 {flags=graph
y1=0
y2=3.2e-11
ypos1=0
ypos2=2
divy=5
subdivy=1
unity=p
x1=3
x2=9
divx=6
subdivx=1
unitx=1
dataset=-1
autoload=1
rawfile=$netlist_dir/tft_cv_estimated.raw
sim_type=ac
logx=1
logy=0
color="4 6 7 8"
node="c_oxide
c_depleted
c_accum
c_thin"
hilight_wave=-1}
N 130 -490 130 -440 {
lab=DOX}
N 50 -410 90 -410 {
lab=GOX}
N 130 -380 130 -310 {
lab=0}
N 330 -490 330 -440 {
lab=DDEP}
N 250 -410 290 -410 {
lab=GDEP}
N 330 -380 330 -310 {
lab=0}
N 530 -490 530 -440 {
lab=DACC}
N 450 -410 490 -410 {
lab=GACC}
N 530 -380 530 -310 {
lab=0}
N 730 -490 730 -440 {
lab=DTHIN}
N 650 -410 690 -410 {
lab=GTHIN}
N 730 -380 730 -310 {
lab=0}
C {devices/code_shown.sym} 20 -160 0 0 {name=MODELS only_toplevel=true
format="tcleval( @value )"
value="
.include $::IGZO_MODELS/design.ngspice
.include $::IGZO_MODELS/igzo_cv_estimated.ngspice
.lib $::IGZO_MODELS/igzo_mmm_lab.ngspice best
"}
C {devices/lab_pin.sym} 50 -410 0 0 {name=l1 sig_type=std_logic lab=GOX}
C {devices/lab_pin.sym} 130 -490 0 0 {name=l2 sig_type=std_logic lab=DOX}
C {devices/gnd.sym} 130 -310 0 0 {name=l3 lab=0}
C {devices/lab_pin.sym} 250 -410 0 0 {name=l4 sig_type=std_logic lab=GDEP}
C {devices/lab_pin.sym} 330 -490 0 0 {name=l5 sig_type=std_logic lab=DDEP}
C {devices/gnd.sym} 330 -310 0 0 {name=l6 lab=0}
C {devices/lab_pin.sym} 450 -410 0 0 {name=l7 sig_type=std_logic lab=GACC}
C {devices/lab_pin.sym} 530 -490 0 0 {name=l8 sig_type=std_logic lab=DACC}
C {devices/gnd.sym} 530 -310 0 0 {name=l9 lab=0}
C {devices/lab_pin.sym} 650 -410 0 0 {name=l10 sig_type=std_logic lab=GTHIN}
C {devices/lab_pin.sym} 730 -490 0 0 {name=l11 sig_type=std_logic lab=DTHIN}
C {devices/gnd.sym} 730 -310 0 0 {name=l12 lab=0}
C {symbols/tft_igzo.sym} 110 -410 0 0 {name=XOXIDE
W=1000u
L=8u
ov=5u
nf=1
m=1
model=igzo_tft
spiceprefix=X
}
C {symbols/tft_igzo_cv.sym} 310 -410 0 0 {name=XDEPL
W=1000u
L=8u
ov=5u
nf=1
m=1
acc=0
t_igzo=30e-9
vdep=0
model=igzo_tft_cv
spiceprefix=X
}
C {symbols/tft_igzo_cv.sym} 510 -410 0 0 {name=XACC
W=1000u
L=8u
ov=5u
nf=1
m=1
acc=1
t_igzo=30e-9
vdep=0
model=igzo_tft_cv
spiceprefix=X
}
C {symbols/tft_igzo_cv.sym} 710 -410 0 0 {name=XTHIN
W=1000u
L=8u
ov=5u
nf=1
m=1
acc=0
t_igzo=15e-9
vdep=0
model=igzo_tft_cv
spiceprefix=X
}
C {devices/code_shown.sym} 1040 -490 0 0 {name=NGSPICE only_toplevel=true
value="
vgox   gox   0 dc 3 ac 1
vgdep  gdep  0 dc 3 ac 1
vgacc  gacc  0 dc 3 ac 1
vgthin gthin 0 dc 3 ac 1
vdox   dox   0 0
vddep  ddep  0 0
vdacc  dacc  0 0
vdthin dthin 0 0
.control
save all
set numdgt=8
ac dec 20 1k 1g
let w = 2*pi*frequency
let c_oxide     = -imag(i(vgox))/w
let c_depleted  = -imag(i(vgdep))/w
let c_accum     = -imag(i(vgacc))/w
let c_thin      = -imag(i(vgthin))/w

* what the estimate costs, at a frequency where the contact has not yet
* taken the capacitance away
meas ac c_ox_lo   FIND c_oxide    AT=1k
meas ac c_dep_lo  FIND c_depleted AT=1k
meas ac c_acc_lo  FIND c_accum    AT=1k
meas ac c_thin_lo FIND c_thin     AT=1k
let ratio_dep = c_dep_lo/c_ox_lo
print ratio_dep

* the accumulated case must return to the measured oxide value exactly - if
* it does not, the wrapper has changed something it should not have
let err_acc = (c_acc_lo - c_ox_lo)/c_ox_lo
print err_acc
write tft_cv_estimated.raw

if $?batchmode = 0
  plot c_oxide c_depleted c_accum c_thin
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
