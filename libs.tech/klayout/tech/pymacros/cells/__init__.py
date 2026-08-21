"""
PCell library for the UCI/INRF IGZO TFT process (igzo_mmm_lab).

Registration follows gf180mcuD/libs.tech/klayout/tech/pymacros/cells/__init__.py:
a pya.Library subclass that registers the PCells and then itself, instantiated
from igzo_mmm_lab.lym at KLayout start-up.
"""

import pya

from .tft import cap_mim, tft_igzo

__all__ = ["igzo_mmm_lab_pr", "tft_igzo", "cap_mim"]


class igzo_mmm_lab_pr(pya.Library):
    """Primitive devices of the UCI/INRF IGZO TFT process."""

    def __init__(self):
        self.description = "UCI/INRF IGZO TFT primitive devices"

        self.layout().register_pcell("tft_igzo", tft_igzo())
        self.layout().register_pcell("cap_mim", cap_mim())

        self.register("igzo_mmm_lab_pr")
