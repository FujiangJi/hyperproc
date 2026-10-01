"""6S and libRadtran look-up-table engines with the aerosol model exposed.

ISOFIT ships both engines but fixes their aerosol: the 6S input template writes
model 1 (continental) with 0.30 atm-cm ozone, and the libRadtran template uses
``aerosol_default`` (rural). ``apply_oe`` cannot pick them at all; it only
writes an sRTMnet or MODTRAN engine block. hyperproc keeps ``apply_oe``'s
orchestration and swaps the engine block after it is written
(:mod:`hyperproc.atmos._runner`); the subclasses here read their settings from
a small JSON file beside the look-up table, written by the runner, so the
settings travel to the Ray workers inside the pickled engine instance.

Importing this module imports ISOFIT's engines (and through them torch), so
:mod:`hyperproc.atmos.correct` does not import it; only the runner does.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from isofit.atmosphere.engines import Engines
from isofit.atmosphere.engines.libradtran import LibRadTranRT
from isofit.atmosphere.engines.six_s import SixSRT

from hyperproc.atmos.aerosols import LRT_AEROSOL, SIXS_AEROSOL

SIDECAR = "hyperproc_engine.json"


def read_settings(sim_path) -> dict:
    p = Path(sim_path) / SIDECAR
    return json.loads(p.read_text()) if p.is_file() else {}


def write_settings(sim_path, **settings) -> Path:
    p = Path(sim_path) / SIDECAR
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(settings, indent=1))
    return p


class SixS(SixSRT):
    """6S with a selectable aerosol model and ozone column, at instrument wavelengths.

    Two things differ from ISOFIT's class. The aerosol model (line 5 of the
    6S input) and, when ``ozone`` is given, the ozone column (lines 4 and 10,
    atm-cm) are edited into each input file after the parent writes it. And
    the look-up table is stored at the instrument's wavelengths: ISOFIT keeps
    6S output on 6S's own 2.5 nm grid and lets the forward model resample,
    which the analytical line does not do (it fails with an 861 x 285 shape
    mismatch), so each simulation is resampled here with the instrument's
    FWHM, exactly as the sRTMnet route ends up at instrument resolution.

    Ray workers run ``makeSim``/``readSim`` from the pickled instance, so the
    settings are read before the parent's constructor, which may already
    build the table.
    """

    SIM_RANGE = (350.0, 2500.0)     # nm; 6S runs on its 2.5 nm grid over this range

    def __init__(self, full_config, wl=(), fwhm=(), **kwargs):
        s = read_settings(full_config.forward_model.atmosphere.sim_path)
        self.hp_aerosol = SIXS_AEROSOL[s.get("aerosol_model", "continental")]
        self.hp_ozone = s.get("ozone")
        if not len(wl):
            from isofit.core.common import load_wavelen
            wl, fwhm = load_wavelen(full_config.forward_model.instrument.wavelength_file)
        super().__init__(full_config, wl=np.asarray(wl, float), fwhm=np.asarray(fwhm, float), **kwargs)

    def rebuild_cmd(self, point, wlinf, wlsup):
        cmd = super().rebuild_cmd(point, *self.SIM_RANGE)
        inpt = Path(self.sim_path) / f"LUT_{self.point_to_filename(point)}.inp"
        lines = inpt.read_text().splitlines()
        if lines[4].strip() != "1":
            raise RuntimeError(f"unexpected 6S input template in {inpt}: line 5 should be the aerosol model (1)")
        lines[4] = str(self.hp_aerosol)
        if self.hp_ozone is not None:
            for i in (3, 9):                      # "H2O, O3[, CO2]" and "-H2O, -O3"
                parts = lines[i].split(",")
                sign = "-" if parts[1].strip().startswith("-") else ""
                parts[1] = f" {sign}{float(self.hp_ozone):g}"
                lines[i] = ",".join(parts)
        inpt.write_text("\n".join(lines) + "\n")
        return cmd

    @staticmethod
    def _sim_grid(file) -> np.ndarray:
        """The wavelengths (nm) of a 6S output file's spectral table."""
        grid, start = [], False
        for line in Path(file).read_text(errors="replace").splitlines():
            if line.startswith("*        trans  down   up"):
                start = True
                continue
            if start:
                tokens = re.findall(r"NaN|\d+\.?\d+", line.replace("******", "0.0"))
                if len(tokens) == 11:
                    grid.append(float(tokens[0]) * 1000.0)
                elif line.startswith("*") and grid:
                    break
        return np.asarray(grid)

    def readSim(self, point):
        from isofit.core.common import resample_spectrum
        file = Path(self.sim_path) / self.point_to_filename(point)
        data = self.parse_file(file=str(file), wl=None, multipart_transmittance=self.multipart_transmittance, wl_size=0)
        if not data:
            return data
        grid = self._sim_grid(file)
        out = {}
        for key, val in data.items():
            val = np.asarray(val)
            if val.ndim == 1 and val.size == grid.size:
                out[key] = resample_spectrum(val, grid, self.wl, self.fwhm)
            else:
                out[key] = val
        return out


class LibRadTran(LibRadTranRT):
    """libRadtran with a selectable Shettle haze type on top of ``aerosol_default``.

    Ozone and CO2 come from the MODTRAN template ISOFIT writes (``O3STR``,
    ``CO2MX``); the runner edits ``O3STR`` there when ``ozone`` is given.
    """

    def __init__(self, full_config, **kwargs):
        # ISOFIT 4.1.5's LibRadTranRT reads self.config in its own constructor
        # before the base class sets it, so it cannot be built standalone
        # without this line.
        self.config = full_config.forward_model.atmosphere
        s = read_settings(self.config.sim_path)
        haze = LRT_AEROSOL[s.get("aerosol_model", "rural")]
        if haze is not None:
            self.libradtran_inp_template = LibRadTranRT.libradtran_inp_template.replace(
                "aerosol_default\n", f"aerosol_default\naerosol_haze {haze}\n")
        super().__init__(full_config, **kwargs)


def register() -> None:
    """Make ISOFIT build ``6s`` and ``LibRadTran`` engines with these classes."""
    Engines["6s"] = SixS
    Engines["LibRadTran"] = LibRadTran
