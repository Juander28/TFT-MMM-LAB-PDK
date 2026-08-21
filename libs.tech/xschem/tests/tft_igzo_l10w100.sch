v {xschem version=3.4.5 file_version=1.2

* Schematic view of the primitive tft_igzo_l10w100.
*
* This is the LVS counterpart of libs.ref/igzo_mmm_lab_pr/mag/
* tft_igzo_l10w100.mag: same cell name, same pins, so
*
*     netgen -batch lvs "<layout>.spice tft_igzo_l10w100" \
*                       "<schematic>.spice tft_igzo_l10w100" \
*                       $PDKPATH/libs.tech/netgen/setup.tcl
*
* compares the drawn device against the schematic one.
*
* Three pins, D G S: a TFT has no body.  The igzo_tft subcircuit keeps the
* intrinsic device's bulk tied to its own source, inside.
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
C {devices/iopin.sym} 130 -490 0 0 {name=p1 lab=D}
C {devices/iopin.sym} 50 -410 0 1 {name=p2 lab=G}
C {devices/iopin.sym} 130 -310 0 0 {name=p3 lab=S}
C {symbols/tft_igzo.sym} 110 -410 0 0 {name=M1
W=100u
L=10u
ov=5u
nf=1
m=1
model=igzo_tft
spiceprefix=X
}
C {devices/title.sym} 160 -30 0 0 {name=l5 author="UCI/INRF - MMM Lab"}
