#!/usr/bin/env python3
"""Plot an ngspice raw file, without the netlist having asked for it.

A testbench that carries `plot` in its .control block decides for you what
gets drawn and when.  This decides nothing: point it at any raw file and it
shows what is in it.

    python3 plot_raw.py run.raw                  # everything worth plotting
    python3 plot_raw.py run.raw i(vd) v(out)     # just these
    python3 plot_raw.py run.raw --list           # what is in the file
    python3 plot_raw.py run.raw --out fig.png    # write instead of show
    python3 plot_raw.py run.raw --log            # log y axis

It reads the raw format itself - binary or ascii, real or complex, one plot
or several - so it needs nothing but the file.  ngspice does not have to be
installed, let alone running.

WHY THIS EXISTS.  Three reasons, in order of how often they come up:

  * A run that has already happened.  The raw file is on disk; re-running the
    simulation to look at it is wasteful and, for a long transient, slow.
  * Batch runs.  `ngspice -b` cannot draw anything, so a testbench meant to
    be checked automatically must not plot - and then there is nothing to look
    at when it fails.  This looks at it afterwards.
  * Comparing two runs.  Pass two files and they are drawn on the same axes,
    which no amount of `plot` inside one netlist can do.
"""

import os
import struct
import sys


def read_raw(path):
    """Parse an ngspice rawfile into a list of plots.

    Each plot is {"title", "name", "vars": [name...], "type": [type...],
    "data": {name: [values]}, "complex": bool}.  Written from the format
    rather than shelling out, so this works on a machine with no ngspice.
    """
    with open(path, "rb") as f:
        blob = f.read()

    plots = []
    pos = 0
    while pos < len(blob):
        # The header is ascii even in a binary file; find where the numbers
        # start by looking for the Binary:/Values: marker.
        head_end_b = blob.find(b"Binary:\n", pos)
        head_end_a = blob.find(b"Values:\n", pos)
        if head_end_b == -1 and head_end_a == -1:
            break
        binary = head_end_b != -1 and (head_end_a == -1 or head_end_b < head_end_a)
        head_end = head_end_b if binary else head_end_a
        header = blob[pos:head_end].decode("latin-1", "replace")

        info = {"title": "", "name": "", "vars": [], "type": [],
                "complex": False, "npoints": 0, "nvars": 0}
        in_vars = False
        for line in header.splitlines():
            low = line.lower()
            if low.startswith("title:"):
                info["title"] = line.split(":", 1)[1].strip()
            elif low.startswith("plotname:"):
                info["name"] = line.split(":", 1)[1].strip()
            elif low.startswith("flags:"):
                info["complex"] = "complex" in low
            elif low.startswith("no. variables:"):
                info["nvars"] = int(line.split(":")[1])
            elif low.startswith("no. points:"):
                info["npoints"] = int(line.split(":")[1])
            elif low.startswith("variables:"):
                in_vars = True
            elif in_vars:
                parts = line.split()
                if len(parts) >= 3 and parts[0].isdigit():
                    info["vars"].append(parts[1])
                    info["type"].append(parts[2])

        nv, npt = info["nvars"], info["npoints"]
        cols = [[] for _ in range(nv)]
        if binary:
            start = head_end + len(b"Binary:\n")
            width = 16 if info["complex"] else 8
            need = nv * npt * width
            raw = blob[start:start + need]
            fmt = "<" + ("d" * (2 if info["complex"] else 1))
            k = 0
            for _ in range(npt):
                for v in range(nv):
                    vals = struct.unpack_from(fmt, raw, k)
                    k += width
                    cols[v].append(complex(*vals) if info["complex"]
                                   else vals[0])
            pos = start + need
        else:
            start = head_end + len(b"Values:\n")
            text = blob[start:].decode("latin-1", "replace")
            got = 0
            for line in text.splitlines():
                parts = line.split()
                if not parts:
                    continue
                if parts[0].isdigit() and len(parts) > 1:
                    parts = parts[1:]          # row index
                for p in parts:
                    if got >= nv * npt:
                        break
                    v = got % nv
                    try:
                        if "," in p:
                            re_, im_ = p.split(",")
                            cols[v].append(complex(float(re_), float(im_)))
                        else:
                            cols[v].append(float(p))
                        got += 1
                    except ValueError:
                        pass
                if got >= nv * npt:
                    break
            pos = len(blob)

        info["data"] = dict(zip(info["vars"], cols))
        plots.append(info)
        if not binary:
            break
    return plots


def interesting(plot):
    """The vectors worth drawing by default.

    Skips the sweep variable itself and the scalars that `meas` leaves
    behind - a raw file is usually half measurement results, and plotting a
    one-point vector against a thousand-point axis is noise.
    """
    if not plot["vars"]:
        return []
    scale = plot["vars"][0]
    npt = plot["npoints"]
    out = []
    for name in plot["vars"][1:]:
        col = plot["data"].get(name) or []
        if len(col) < npt or npt < 2:
            continue                       # a meas scalar, not a waveform
        vals = [abs(v) for v in col]
        if max(vals) == min(vals):
            continue                       # a constant, e.g. a fixed source
        out.append(name)
    return out


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    opts = [a for a in argv if a.startswith("--")]
    if not args:
        print(__doc__)
        return 1

    files, wanted = [], []
    for a in args:
        (files if os.path.exists(a) else wanted).append(a)
    if not files:
        print("no such file: %s" % args[0], file=sys.stderr)
        return 1

    out = None
    for o in opts:
        if o.startswith("--out"):
            i = opts.index(o)
            out = o.split("=", 1)[1] if "=" in o else None
    if out is None and "--out" in argv:
        k = argv.index("--out")
        if k + 1 < len(argv):
            out = argv[k + 1]
            if out in files:
                files.remove(out)
            if out in wanted:
                wanted.remove(out)

    everything = [(f, read_raw(f)) for f in files]

    if "--list" in opts:
        for f, plots in everything:
            print("%s:" % f)
            for p in plots:
                print("  plot %-14s %d points, %d vars%s"
                      % (p["name"] or "-", p["npoints"], p["nvars"],
                         "  (complex)" if p["complex"] else ""))
                for n, t in zip(p["vars"], p["type"]):
                    print("      %-24s %s" % (n, t))
        return 0

    import matplotlib
    if out:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Group by unit, not by name.  A raw file holds volts and amps together,
    # and a drain current of 600 uA drawn on the same axis as a 10 V sweep is
    # a flat line at zero.  One panel per unit is the only default that shows
    # anything.
    panels = {}
    for f, plots in everything:
        for p in plots:
            if not p["vars"]:
                continue
            scale = p["vars"][0]
            xs = [v.real if isinstance(v, complex) else v
                  for v in p["data"][scale]]
            names = wanted or interesting(p)
            for name in names:
                col = p["data"].get(name)
                if not col or len(col) != len(xs):
                    continue
                unit = dict(zip(p["vars"], p["type"])).get(name, "other")
                ys = [abs(v) if isinstance(v, complex) else v for v in col]
                label = name if len(everything) == 1 else "%s  %s" % (
                    os.path.basename(f), name)
                panels.setdefault(unit, {"scale": scale, "traces": []})
                panels[unit]["traces"].append((label, xs, ys))

    if not panels:
        print("nothing to plot - try --list to see what is in the file",
              file=sys.stderr)
        return 1

    order = [u for u in ("voltage", "current", "frequency", "time") if u in panels]
    order += [u for u in panels if u not in order]
    fig, axes = plt.subplots(len(order), 1, figsize=(9, 2.6 * len(order)),
                             sharex=True, squeeze=False)
    fig.patch.set_facecolor("white")
    drawn = 0
    for ax, unit in zip([a[0] for a in axes], order):
        for label, xs, ys in panels[unit]["traces"]:
            # A DC sweep with a second source is several curves concatenated:
            # the x axis restarts at each step.  Drawn as one line it zigzags
            # back across the plot, which is how a family of output curves
            # turns into a scribble.  Split on the restart.
            start = 0
            first = True
            for i in range(1, len(xs) + 1):
                if i == len(xs) or xs[i] < xs[i - 1]:
                    ax.plot(xs[start:i], ys[start:i], lw=1.4,
                            color="C%d" % (drawn % 10),
                            label=label if first else None)
                    first = False
                    start = i
            drawn += 1
        ax.set_ylabel(unit)
        if "--log" in opts:
            ax.set_yscale("log")
        if "--logx" in opts:
            ax.set_xscale("log")
        ax.grid(True, color="#e3e3e0", lw=0.5)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.legend(fontsize=8, frameon=False, ncol=2)
    axes[-1][0].set_xlabel(panels[order[0]]["scale"])
    axes[0][0].set_title(everything[0][1][0]["title"][:80], size=10,
                         loc="left")
    fig.tight_layout()
    if out:
        fig.savefig(out, dpi=150)
        print("wrote", out)
    else:
        plt.show()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
