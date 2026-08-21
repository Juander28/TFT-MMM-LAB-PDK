#!/usr/bin/env python3
"""
Run the igzo_mmm_lab DRC deck on a layout.

    python3 run_drc.py --path <layout.gds> [--topcell <cell>] [--output <dir>]

Wrapper around `klayout -b -r igzo_mmm_lab.drc`, following
gf180mcuD/libs.tech/klayout/tech/drc/run_drc.py.  Exits non-zero if the deck
reports any violation, so it can be used in a check script.
"""

import argparse
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
DECK = os.path.join(HERE, "igzo_mmm_lab.drc")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", required=True, help="layout to check (GDS/OASIS)")
    ap.add_argument("--topcell", default=None, help="top cell name")
    ap.add_argument("--output", default=".", help="directory for the report")
    ap.add_argument("--threads", default="4")
    args = ap.parse_args()

    name = os.path.splitext(os.path.basename(args.path))[0]
    report = os.path.join(args.output, name + ".lyrdb")

    cmd = ["klayout", "-b", "-r", DECK,
           "-rd", "input=" + os.path.abspath(args.path),
           "-rd", "report=" + os.path.abspath(report),
           "-rd", "thr=" + args.threads]
    if args.topcell:
        cmd += ["-rd", "topcell=" + args.topcell]

    print(" ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        return result.returncode

    if not os.path.exists(report):
        print("no report produced", file=sys.stderr)
        return 1

    tree = ET.parse(report)
    items = tree.getroot().findall(".//item")
    by_rule = {}
    for item in items:
        cat = item.findtext("category", "").strip("'")
        by_rule[cat] = by_rule.get(cat, 0) + 1

    if not by_rule:
        print("DRC clean: %s" % args.path)
        return 0

    print("DRC violations in %s:" % args.path)
    for rule in sorted(by_rule):
        print("  %-12s %d" % (rule, by_rule[rule]))
    print("report: %s" % report)
    return 1


if __name__ == "__main__":
    sys.exit(main())
