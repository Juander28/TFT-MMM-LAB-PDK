v {xschem version=3.4.8RC file_version=1.3
* IGZO TFT transfer characteristics - UCI/INRF process (igzo_mmm_lab)
*
* Id against Vgs, on three devices at once, because one curve does not show
* what this process actually limits you with.
*
*   XLONG   L = 160 um, Vds = 0.1 V   linear region, channel dominated
*   XSHORT  L =   8 um, Vds = 0.1 V   linear region, CONTACT dominated
*   XSAT    L =   8 um, Vds =  10 V   saturation
*
* WHAT THIS TEST IS FOR.  Extracting Vth by linear extrapolation off XLONG
* does not return the model's Vto.  The model says Vto = +0.09 V in the best
* corner; the extrapolation returns about -0.6 V.  The difference is the
* contact: 2*Rc*W = 6.6 MOhm*um, so a W = 1000 um device carries 6.6 kOhm in
* series, against ~46 kOhm of channel at L = 160 um.  The contact takes a
* growing share of Vds as the current rises, the slope falls, and the
* intercept moves.  That is the real device, not an artefact - the same bias
* sits on a measured wafer, which is why the extracted Vth in
* docs/extraction/ is not the Vto in the .model card either.
*
* At L = 8 um and Vds = 0.1 V the contact wins outright: XSHORT carries less
* than a tenth of what its W/L says it should.
*
* WHAT LEVEL 1 CANNOT SHOW.  There is no subthreshold region.  Below Vth the
* model current is exactly zero, so an on/off ratio, a subthreshold slope and
* an off current cannot be read off this curve at all.  They have to be
* measured.  The sweep starts at -1 V only to make that flat zero visible.
}
G {}
K {}
V {}
S {}
F {}
E {}
B 2 20 80 660 420 {flags=graph
y1=0
y2=0.0007
ypos1=0
ypos2=2
divy=5
subdivy=1
unity=u
x1=-1
x2=6
divx=5
subdivx=1
unitx=1
dataset=-1
autoload=1
rawfile=$netlist_dir/tft_transfer.raw
sim_type=dc
logx=0
logy=0
color="4"
node="i(id_sat)"
hilight_wave=-1
}
B 2 700 80 1340 420 {flags=graph
y1=0
y2=1.3e-05
ypos1=0
ypos2=2
divy=5
subdivy=1
unity=u
x1=-1
x2=6
divx=5
subdivx=1
unitx=1
dataset=-1
autoload=1
rawfile=$netlist_dir/tft_transfer.raw
sim_type=dc
logx=0
logy=0
color="6 7"
node="i(id_long)
i(id_short)"
hilight_wave=-1
}
N 130 -490 130 -440 {
lab=DLONG}
N 50 -410 90 -410 {
lab=G}
N 130 -380 130 -310 {
lab=S}
N 330 -490 330 -440 {
lab=DSHORT}
N 250 -410 290 -410 {
lab=G}
N 330 -380 330 -310 {
lab=S}
N 530 -490 530 -440 {
lab=DSAT}
N 450 -410 490 -410 {
lab=G}
N 530 -380 530 -310 {
lab=S}
C {devices/code_shown.sym} 20 -160 0 0 {name=MODELS only_toplevel=true
format="tcleval( @value )"
value="
.include $::IGZO_MODELS/design.ngspice
.lib $::IGZO_MODELS/igzo_mmm_lab.ngspice best
"}
C {devices/lab_pin.sym} 50 -410 0 0 {name=l1 sig_type=std_logic lab=G}
C {devices/lab_pin.sym} 130 -490 0 0 {name=l2 sig_type=std_logic lab=DLONG}
C {devices/lab_pin.sym} 130 -310 0 0 {name=l3 sig_type=std_logic lab=S}
C {devices/lab_pin.sym} 250 -410 0 0 {name=l4 sig_type=std_logic lab=G}
C {devices/lab_pin.sym} 330 -490 0 0 {name=l5 sig_type=std_logic lab=DSHORT}
C {devices/lab_pin.sym} 330 -310 0 0 {name=l6 sig_type=std_logic lab=S}
C {devices/lab_pin.sym} 450 -410 0 0 {name=l7 sig_type=std_logic lab=G}
C {devices/lab_pin.sym} 530 -490 0 0 {name=l8 sig_type=std_logic lab=DSAT}
C {devices/lab_pin.sym} 530 -310 0 0 {name=l9 sig_type=std_logic lab=S}
C {symbols/tft_igzo.sym} 110 -410 0 0 {name=XLONG
W=1000u
L=160u
ov=5u
nf=1
m=1
model=igzo_tft
spiceprefix=X
}
C {symbols/tft_igzo.sym} 310 -410 0 0 {name=XSHORT
W=1000u
L=8u
ov=5u
nf=1
m=1
model=igzo_tft
spiceprefix=X
}
C {symbols/tft_igzo.sym} 510 -410 0 0 {name=XSAT
W=1000u
L=8u
ov=5u
nf=1
m=1
model=igzo_tft
spiceprefix=X
}
C {devices/code_shown.sym} 690 -740 0 0 {name=NGSPICE only_toplevel=true
value="
vlong dlong 0 0.1
vshort dshort 0 0.1
vsat dsat 0 10
vg g 0 0
vs s 0 0
.control
save all
dc vg -1 6 0.01
let id_long  = -i(vlong)
let id_short = -i(vshort)
let id_sat   = -i(vsat)
let gm_long  = deriv(id_long)
let gm_sat   = deriv(id_sat)

* Linear extrapolation on the long device, at Vgs = 5 V.
* Vth = Vgs - Id/gm - Vds/2
meas dc gm_l FIND gm_long AT=5
meas dc id_l FIND id_long AT=5
let vth_lin = 5 - id_l/gm_l - 0.05
print vth_lin

* Peak transconductance, and the current it belongs to
meas dc gm_peak MAX gm_sat
meas dc id_on   MAX id_sat

* How much of the long-channel linear resistance is contact and not channel
let r_total   = 0.1/id_l
let r_contact = 2*3.3/1000u
let contact_share = r_contact/r_total
print r_total r_contact contact_share

* What the contact costs the short device in the linear region
meas dc id_short_on MAX id_short
write tft_transfer.raw

* The two graphs on the sheet: saturation on the left, and the linear
* region on the right, where the long and the short device separate by a
* factor of fifty because of the contact.  Separate graphs, not one: at
* Vds = 0.1 V the currents are two orders of magnitude apart and one axis
* would flatten the linear pair onto zero.
if $?batchmode = 0
  plot id_sat
  plot id_long id_short
end
.endc
"}
C {devices/title.sym} 160 -30 0 0 {name=l10 author="UCI/INRF - MMM Lab"}
C {devices/launcher.sym} 1380 40 0 0 {name=hw
descr="Ctrl-click here to load or unload the waveforms by hand.
The graphs load themselves after a simulation; this is for
looking at a run made earlier."
tclcommand="
xschem raw_read $netlist_dir/[file tail [file rootname [xschem get current_name]]].raw
"
}
