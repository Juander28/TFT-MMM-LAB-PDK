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
#   1 d   2 g   3 s   4 b
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
# There is no substrate in this process - a TFT sits on glass.  The b pin of
# igzo_tft is inert and magic names it GND, so tie B to GND in schematics.
#-------------------------------------------
