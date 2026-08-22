v {xschem version=3.4.5 file_version=1.2

* The three cells of this PDK together: a TFT driving an LC tank.
*
* The tank is the one the project actually wants - resonant at 100 MHz - and
* the values are what the PCells report for a drawn coil and a drawn plate:
*
*   ind_igzo  square, series, n=16, d_in=400u, w=20u, gap=10u
*             50 nm of gold : 263.5 nH,  1.438 kOhm,  Q = 0.12
*             1  um of gold : 263.5 nH,  71.88 Ohm,   Q = 2.30
*   cap_mim   78.4 x 78.4 um -> 9.61 pF, which resonates with 263.5 nH at
*             100 MHz
*
* The netlist below carries the 1 um case.  Swap rs to 1438 to see what the
* process as it stands today does to the same tank: the peak disappears.  That
* comparison is the point of this testbench - the inductor is drawable long
* before it is useful, and the lever is metal thickness, not turns.
}
G {}
K {}
V {}
S {}
E {}
N 0 0 80 0 {
lab=in}
N 120 -80 120 -30 {
lab=out}
N 120 -80 220 -80 {
lab=out}
N 220 -80 220 -60 {
lab=out}
N 120 -140 120 -110 {
lab=vdd}
N 120 -170 120 -140 {
lab=vdd}
N 220 0 220 30 {
lab=0}
N 120 30 120 60 {
lab=0}
C {devices/code_shown.sym} 20 160 0 0 {name=MODELS only_toplevel=true
format="tcleval( @value )"
value="
.include $::IGZO_MODELS/design.ngspice
.lib $::IGZO_MODELS/igzo_mmm_lab.ngspice tt
"}
C {devices/lab_pin.sym} 0 0 0 0 {name=l1 sig_type=std_logic lab=in}
C {devices/lab_pin.sym} 120 -170 0 0 {name=l2 sig_type=std_logic lab=vdd}
C {devices/lab_pin.sym} 120 -80 0 1 {name=l3 sig_type=std_logic lab=out}
C {devices/gnd.sym} 120 60 0 0 {name=g1 lab=0}
C {devices/gnd.sym} 220 30 0 0 {name=g2 lab=0}
C {symbols/tft_igzo.sym} 100 0 0 0 {name=M1
W=1000u
L=8u
ov=5u
nf=1
m=1
model=igzo_tft
spiceprefix=X
}
C {symbols/ind_igzo.sym} 120 -110 0 0 {name=L1
ls=263.5n
rs=71.88
model=ind_igzo
spiceprefix=X
}
C {symbols/cap_mim.sym} 220 -30 0 0 {name=C1
W=78.4u
L=78.4u
model=cap_mim
spiceprefix=X
}
C {devices/code_shown.sym} 320 -160 0 0 {name=NGSPICE only_toplevel=true
value="
vdd vdd 0 5
vin in 0 dc 2 ac 1
.control
save all
ac dec 200 1meg 1g
write tank_ac.raw
print v(out) > /dev/null
.endc
"}
C {devices/title.sym} 160 200 0 0 {name=l5 author="UCI/INRF - MMM Lab"}
