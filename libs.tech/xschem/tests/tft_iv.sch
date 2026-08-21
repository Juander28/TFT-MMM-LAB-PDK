v {xschem version=3.4.5 file_version=1.2

* IGZO TFT output characteristics - UCI/INRF process (igzo_mmm_lab)
*
* Sweeps Id against Vds at several Vgs on the device the model was validated
* against: W = 1000 um, L = 8 um.  At Vgs = 6 V, Vds = 10 V the measurement
* gives 670-701 uA and this netlist gives ~654 uA.
*
* Both limits of the model are visible here: it is DC-only, and it is valid
* for Vgs <= 6 V and Vds <= 10 V.  The sweep deliberately stops there.
}
G {}
K {}
V {}
S {}
E {}
N 130 -490 130 -440 {
lab=D}
N 50 -410 90 -410 {
lab=G}
N 130 -380 130 -310 {
lab=S}
C {devices/code_shown.sym} 20 -160 0 0 {name=MODELS only_toplevel=true
format="tcleval( @value )"
value="
.include $::IGZO_MODELS/design.ngspice
.lib $::IGZO_MODELS/igzo_mmm_lab.ngspice best
"}
C {devices/lab_pin.sym} 50 -410 0 0 {name=l1 sig_type=std_logic lab=G}
C {devices/lab_pin.sym} 130 -490 0 0 {name=l2 sig_type=std_logic lab=D}
C {devices/lab_pin.sym} 130 -310 0 0 {name=l3 sig_type=std_logic lab=S}
C {symbols/tft_igzo.sym} 110 -410 0 0 {name=M1
W=1000u
L=8u
ov=5u
nf=1
m=1
model=igzo_tft
spiceprefix=X
}
C {devices/code_shown.sym} 300 -450 0 0 {name=NGSPICE only_toplevel=true
value="
vd d 0 0
vg g 0 0
vs s 0 0
.control
save all
dc vd 0 10 0.1 vg 0 6 1
write tft_iv.raw
.endc
"}
C {devices/title.sym} 160 -30 0 0 {name=l5 author="UCI/INRF - MMM Lab"}
