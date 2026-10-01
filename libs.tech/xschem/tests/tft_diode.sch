v {xschem version=3.4.8RC file_version=1.3
* Diode-connected IGZO TFT - UCI/INRF process (igzo_mmm_lab)
*
* Gate tied to drain, swept from -5 V to +10 V.  Two devices:
*
*   XD1   W = 1000 um, L =  8 um, ov = 5 um   the validated device
*   XD6   W = 6000 um, L = 10 um, ov = 2 um   the WPT rectifier device
*
* WHY THIS IS THE DIODE.  The process has four masks - igzo, sd, oxetch,
* gate - and no p-n junction anywhere in it.  A diode-connected transistor is
* the only rectifying element that can be drawn, and it is what the WPT
* rectifier is built from.  There is no diode model in this PDK and there
* should not be one: this schematic is the device.
*
* WHAT COMES OUT.  With gate tied to drain the device is always in
* saturation, so Id = (Kp/2)(W/L)(V - Vth)^2 above threshold.  The validated
* device reaches 1 uA at 0.24 V and 100 uA at 1.93 V, with a dynamic
* resistance of 7.8 kOhm at 5 V - of which 6.6 kOhm is contact, not channel.
* For a rectifier that number is the whole story, which is why the WPT design
* sizes the device at W = 6 mm.
*
* THE REVERSE IS NOT A MODEL.  Below Vth the level-1 current is exactly zero,
* and the few pA this sweep shows at -5 V are ngspice's gmin conductance, not
* physics.  There is no junction to break down and none is modelled, so
* nothing in this curve says what the real device does under reverse bias.
* Neither is there a subthreshold region, so the turn-on shown here is far
* sharper than any measured TFT.
*
* Valid range, as everywhere in this PDK: VGS <= 6 V, VDS <= 10 V.  The sweep
* runs to 10 V because that is where the rectifier works, and the top of the
* range is the top of the range.
}
G {}
K {}
V {}
S {}
F {}
E {}
B 2 20 80 700 420 {flags=graph
y1=0
y2=0.007
ypos1=0
ypos2=2
divy=5
subdivy=1
unity=m
x1=-5
x2=10
divx=5
subdivx=1
unitx=1
dataset=-1
autoload=1
rawfile=$netlist_dir/tft_diode.raw
sim_type=dc
logx=0
logy=0
color="4 6"
node="i(id)
i(id6)"
hilight_wave=-1
}
B 2 740 80 1420 420 {flags=graph
y1=-14
y2=-2
ypos1=0
ypos2=2
divy=5
subdivy=1
unity=1
x1=0
x2=10
divx=5
subdivx=1
unitx=1
dataset=-1
autoload=1
rawfile=$netlist_dir/tft_diode.raw
sim_type=dc
logx=0
logy=0
color="7"
node="logid"
hilight_wave=-1
}
N 130 -490 130 -440 {
lab=A}
N 50 -440 50 -410 {
lab=A}
N 50 -440 130 -440 {
lab=A}
N 50 -410 90 -410 {
lab=A}
N 130 -380 130 -310 {
lab=K1}
N 380 -490 380 -440 {
lab=A}
N 300 -440 300 -410 {
lab=A}
N 300 -440 380 -440 {
lab=A}
N 300 -410 340 -410 {
lab=A}
N 380 -380 380 -310 {
lab=K6}
C {devices/code_shown.sym} 20 -160 0 0 {name=MODELS only_toplevel=true
format="tcleval( @value )"
value="
.include $::IGZO_MODELS/design.ngspice
.lib $::IGZO_MODELS/igzo_mmm_lab.ngspice best
"}
C {devices/lab_pin.sym} 130 -490 0 0 {name=l1 sig_type=std_logic lab=A}
C {devices/lab_pin.sym} 130 -310 0 0 {name=l2 sig_type=std_logic lab=K1}
C {devices/lab_pin.sym} 380 -490 0 0 {name=l3 sig_type=std_logic lab=A}
C {devices/lab_pin.sym} 380 -310 0 0 {name=l4 sig_type=std_logic lab=K6}
C {symbols/tft_igzo.sym} 110 -410 0 0 {name=XD1
W=1000u
L=8u
ov=5u
nf=1
m=1
model=igzo_tft
spiceprefix=X
}
C {symbols/tft_igzo.sym} 360 -410 0 0 {name=XD6
W=6000u
L=10u
ov=2u
nf=1
m=1
model=igzo_tft
spiceprefix=X
}
C {devices/code_shown.sym} 520 -550 0 0 {name=NGSPICE only_toplevel=true
value="
va a 0 0
* one ammeter per device, so a single sweep of the anode measures both
vk1 k1 0 0
vk6 k6 0 0
.control
save all
dc va -5 10 0.01
let id  = i(vk1)
let id6 = i(vk6)

* forward: where it turns on, and how hard
meas dc v_at_1u   WHEN id=1u
meas dc v_at_100u WHEN id=100u
meas dc i_max     MAX id
meas dc i6_max    MAX id6

* dynamic resistance at 5 V - compare against 2*Rc*W/W = 6.6 kOhm
let rdyn = 1/deriv(id)
meas dc rd_at_5 FIND rdyn AT=5

* reverse: this is gmin, not a junction
meas dc i_rev FIND id AT=-5
* Linear on the left, log on the right.  The log curve is the one that
* shows there is no reverse branch and no subthreshold slope: below Vth
* the level-1 current is exactly zero, and log10 of zero is floored here
* so the curve sits on the floor instead of going to minus infinity.
*
* This has to be computed BEFORE the write: the raw file holds the vectors
* that exist when it is written, and a graph on the sheet can only draw
* what is in the raw file.
let logid = log10(maximum(id, 1e-14))
write tft_diode.raw
if $?batchmode = 0
  plot id id6
  plot logid
end
.endc
"}
C {devices/title.sym} 160 -30 0 0 {name=l5 author="UCI/INRF - MMM Lab"}
C {devices/launcher.sym} 1460 40 0 0 {name=hw
descr="Ctrl-click here to load or unload the waveforms by hand.
The graphs load themselves after a simulation; this is for
looking at a run made earlier."
tclcommand="
xschem raw_read $netlist_dir/[file tail [file rootname [xschem get current_name]]].raw
"
}
