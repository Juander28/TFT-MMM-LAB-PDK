"""
Where things live inside this PDK.

Every script that needs the measured data or the models imports this instead of
guessing at relative paths.  The point is that the repository is
self-sufficient: nothing here reaches outside the PDK directory, so renaming or
moving the folder it was copied from cannot break anything.

    from pdk_paths import DATA, MODELS, require_data

Override the data location with PDK_MEASUREMENTS if you keep the .xls files
somewhere else.
"""

import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
PDK_ROOT = os.path.dirname(TOOLS)

MODELS = os.path.join(PDK_ROOT, "libs.tech", "ngspice")
MODEL_FILE = os.path.join(MODELS, "igzo_mmm_lab.ngspice")
DESIGN_FILE = os.path.join(MODELS, "design.ngspice")

DATA = os.environ.get("PDK_MEASUREMENTS",
                      os.path.join(PDK_ROOT, "measurements", "TFT"))

# So that `from xls_reader import ...` works from anywhere.
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)


def require_data(*parts):
    """
    Absolute path inside the measurement tree, checked.

    Raises with something a person can act on rather than a bare
    FileNotFoundError three frames deep.
    """
    path = os.path.join(DATA, *parts)
    if not os.path.exists(path):
        raise SystemExit(
            "measurement data not found: %s\n"
            "The raw .xls files are not tracked in git (see "
            "measurements/README.md).\n"
            "Copy them into %s, or point PDK_MEASUREMENTS at wherever they are."
            % (path, DATA))
    return path
