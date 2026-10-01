#---------------------------------------------------------------
# Setup file for netgen LVS
# UCI/INRF IGZO TFT process (igzo_mmm_lab)
#
# Structure follows gf180mcuD/libs.tech/netgen/setup.tcl (Apache-2.0,
# GlobalFoundries PDK Authors).  The schematic is always circuit2.
#---------------------------------------------------------------

permute default
property default
property parallel none

# Allow override of the default number of output columns
catch {format $env(NETGEN_COLUMNS)}

set cells1 [cells list -all -circuit1]
set cells2 [cells list -all -circuit2]

#-------------------------------------------
# igzo_tft - the only active device
#
# Pins, in the order the subcircuit declares them:
#   1 d   2 g   3 s        (a TFT has no bulk - there is no fourth pin)
# Source and drain are physically identical - the same Au on the same island -
# so they permute.
#
# WIDTH TOLERANCE.  This is the one place where layout and schematic legitimately
# disagree.  Magic measures the gated island; the island is drawn past each
# electrode end for alignment margin (5 um per side on the test chip), and that
# overhang is gated but carries no source-to-drain current.  For the drawn
# matrix that is about 13 % more width than the device has, so w is compared
# with a 20 % tolerance while l - which extracts exactly - is held to 1 %.
#
# Do not read the loose w tolerance as slack in the process.  Tightening it is
# a drawing change: an island flush with the electrodes extracts exactly.
#-------------------------------------------

set device igzo_tft

if {[lsearch $cells1 $device] >= 0 && [lsearch $cells2 $device] >= 0} {
    permute "-circuit1 $device" 1 3
    permute "-circuit2 $device" 1 3
    property "-circuit1 $device" tolerance {w 0.20} {l 0.01}
    property "-circuit2 $device" tolerance {w 0.20} {l 0.01}

    # ov and nf exist only on the schematic side: the overlap is a drawn
    # dimension the extractor folds into capacitance, and fingering is a
    # layout choice with no electrical signature (measured).
    property "-circuit2 $device" remove ov nf

    # A multi-finger device extracts as one TFT per finger.  Fingers in
    # parallel with the same L are one device of the summed W, on both sides,
    # so a 5 x 5 mm layout matches a W = 25 mm schematic.
    property "-circuit1 $device" parallel enable
    property "-circuit1 $device" parallel {l critical}
    property "-circuit1 $device" parallel {w add}
    property "-circuit2 $device" parallel enable
    property "-circuit2 $device" parallel {l critical}
    property "-circuit2 $device" parallel {w add}
}

#-------------------------------------------
# cap_mim - the S/D-metal / Al2O3 / gate-metal overlap capacitor
#-------------------------------------------

set device cap_mim

if {[lsearch $cells1 $device] >= 0 && [lsearch $cells2 $device] >= 0} {
    permute "-circuit1 $device" 1 2
    permute "-circuit2 $device" 1 2
    property "-circuit1 $device" tolerance {w 0.01} {l 0.01}
    property "-circuit2 $device" tolerance {w 0.01} {l 0.01}
}

#-------------------------------------------
# There is no substrate in this process - a TFT sits on glass - and no bulk pin
# on either side.  Magic emits three terminals because the msubcircuit line in
# the techfile carries no substrate arguments.
#-------------------------------------------

#-------------------------------------------
# smd_cap - a surface-mount capacitor on two pads
#
# The value is carried by the smd_cap PCell's smd.body marker (1 um^2 per nF)
# and extracts as c; the schematic writes c directly.  1 % covers the 10 nm
# grid the marker is drawn on.  The two pads are interchangeable.  esr exists
# only on the schematic side - it is a property of the part, not the layout.
#-------------------------------------------

set device smd_cap

if {[lsearch $cells1 $device] >= 0 && [lsearch $cells2 $device] >= 0} {
    permute "-circuit1 $device" 1 2
    permute "-circuit2 $device" 1 2
    property "-circuit1 $device" tolerance {c 0.01}
    property "-circuit2 $device" tolerance {c 0.01}
    property "-circuit2 $device" remove esr
    # capacitors in parallel add: five 10 uF parts match one 50 uF, and
    # five 10 uF parts on the schematic
    property "-circuit1 $device" parallel enable
    property "-circuit1 $device" parallel {c add}
    property "-circuit2 $device" parallel enable
    property "-circuit2 $device" parallel {c add}
}

#-------------------------------------------
# ind_igzo - the planar inductor
#
# Extracted from the ind_igzo PCell's ind.id marker, whose overlap with the
# metal carries ls (1 um^2 per nH).  2 % covers the grid and the schematic's
# rounding of the value printed on the cell.  rs exists only on the
# schematic side.
#-------------------------------------------

set device ind_igzo

if {[lsearch $cells1 $device] >= 0 && [lsearch $cells2 $device] >= 0} {
    permute "-circuit1 $device" 1 2
    permute "-circuit2 $device" 1 2
    property "-circuit1 $device" tolerance {ls 0.02}
    property "-circuit2 $device" tolerance {ls 0.02}
    property "-circuit2 $device" remove rs
}
