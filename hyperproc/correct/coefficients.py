"""Coefficient files.

A correction is only as trustworthy as its coefficients, so hyperproc writes
them to JSON where they can be read, reused and audited. Design choices:

* **Keyed by wavelength** (nanometres, 4 decimals), never by band index. Band
  indices change with band subsets and mean nothing across sensors; a
  wavelength key can be aligned to any cube of the same instrument.
* **Diagnostics next to the numbers.** Every topographic C carries the fit's
  slope, intercept, r, effect size, t statistic, sample count and status; a
  BRDF fit carries its bins, samples per bin, r2 per band and bin, and the
  angular-diversity check that says whether the fit was identifiable.
* **Provenance.** Which inputs (by stem), which masks, which settings, which
  software version, when. The pairing of a coefficient file with its image is
  written *inside* the file - the failure mode where files get matched by
  directory listing order is not reproducible here.

Two containers: :class:`TopoCoefficients` (one image) and
:class:`BRDFCoefficients` (one group of images).
"""
from __future__ import annotations

import datetime as _dt
import json
import platform
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from hyperproc.correct.brdf import FlexFit

FORMAT = "hyperproc.correction"
VERSION = 1


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def provenance(**extra) -> dict:
    """The standard provenance block: software, time, host, plus anything passed."""
    try:
        import hyperproc
        version = getattr(hyperproc, "__version__", "unknown")
    except Exception:  # pragma: no cover
        version = "unknown"
    return {"software": f"hyperproc {version}", "created": _now(),
            "host": platform.node(), **extra}


def _jsonable(o):
    """Recursively convert numpy scalars/arrays so ``json.dump`` accepts them."""
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return _jsonable(o.tolist())
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if not np.isfinite(f) else f
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, Path):
        return str(o)
    return o


def _wl_key(w: float) -> str:
    return f"{float(w):.4f}"


def align_wavelengths(have: np.ndarray, want: np.ndarray, tol: float = 0.5) -> np.ndarray:
    """Index into ``have`` for each wavelength in ``want`` (nearest within
    ``tol`` nm), -1 where none is close enough."""
    have = np.asarray(have, float); want = np.asarray(want, float)
    if have.size == 0:
        return np.full(want.shape, -1, dtype=int)
    order = np.argsort(have)
    pos = np.searchsorted(have[order], want)
    lo = np.clip(pos - 1, 0, have.size - 1); hi = np.clip(pos, 0, have.size - 1)
    pick = np.where(np.abs(have[order][hi] - want) < np.abs(have[order][lo] - want), hi, lo)
    idx = order[pick]
    idx[np.abs(have[idx] - want) > tol] = -1
    return idx


# --- topographic --------------------------------------------------------------------
@dataclass
class TopoCoefficients:
    """Per-image topographic correction coefficients with their fit diagnostics."""

    method: str                        # scs+c | scs | c | cosine
    fit_method: str                    # ols | nnls
    wavelength: np.ndarray             # (n,) nm
    c: np.ndarray                      # (n,) C per band; NaN where no C should be applied
    status: list                       # (n,) ok | insufficient | degenerate | inverted
    slope: np.ndarray                  # (n,) regression slope a
    intercept: np.ndarray              # (n,) regression intercept b
    r: np.ndarray                      # (n,) Pearson r (information only)
    effect: np.ndarray                 # (n,) a (p95 - p05 cos i) / mean rho
    t: np.ndarray                      # (n,) slope t statistic
    n_samples: int                     # pixels in the fit
    calc_mask: dict = field(default_factory=dict)
    apply_mask: dict = field(default_factory=dict)
    diagnostic: dict = field(default_factory=dict)   # verdict and its numbers
    source: dict = field(default_factory=dict)       # stem, sensor, level, path
    meta: dict = field(default_factory=dict)         # anything else (cloud stats, sampling)

    # -- convenience -----------------------------------------------------------------
    @property
    def n_ok(self) -> int:
        return int(np.sum(np.asarray(self.status) == "ok"))

    @property
    def verdict(self) -> str:
        return str(self.diagnostic.get("verdict", "unknown"))

    def c_for(self, wavelength, tol: float = 0.5) -> np.ndarray:
        """C aligned to another wavelength axis (NaN where absent or no C)."""
        idx = align_wavelengths(self.wavelength, wavelength, tol)
        out = np.full(len(idx), np.nan)
        ok = idx >= 0
        out[ok] = self.c[idx[ok]]
        return out

    def summary(self) -> str:
        st = np.asarray(self.status)
        parts = [f"{k}: {int((st == k).sum())}" for k in ("ok", "inverted", "degenerate", "insufficient") if (st == k).any()]
        med = np.nanmedian(self.c) if np.isfinite(self.c).any() else np.nan
        return (f"topo {self.method}/{self.fit_method}: {len(st)} bands ({', '.join(parts)}), "
                f"median C {med:.3f}, n={self.n_samples:,}, verdict={self.verdict}")

    # -- serialisation ---------------------------------------------------------------
    def to_dict(self) -> dict:
        per_band = {}
        for i, w in enumerate(self.wavelength):
            per_band[_wl_key(w)] = {"c": self.c[i], "status": self.status[i], "slope": self.slope[i],
                                    "intercept": self.intercept[i], "r": self.r[i],
                                    "effect": self.effect[i], "t": self.t[i]}
        return _jsonable({
            "format": FORMAT, "version": VERSION, "kind": "topo",
            "method": self.method, "fit_method": self.fit_method,
            "n_samples": self.n_samples, "n_bands": len(self.wavelength),
            "calc_mask": self.calc_mask, "apply_mask": self.apply_mask,
            "diagnostic": self.diagnostic, "source": self.source, "meta": self.meta,
            "provenance": self.meta.get("provenance") or provenance(),
            "bands": per_band,
        })

    def to_json(self, path) -> Path:
        path = Path(path)
        if path.suffix != ".json":
            path.mkdir(parents=True, exist_ok=True)
            stem = self.source.get("stem", "image")
            path = path / f"{stem}_topo_coeffs.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=1))
        return path

    @classmethod
    def from_dict(cls, d: dict) -> "TopoCoefficients":
        if d.get("kind") != "topo":
            raise ValueError(f"not a hyperproc topo coefficient file (kind={d.get('kind')!r})")
        keys = sorted(d["bands"], key=float)
        get = lambda k, f: np.array([np.nan if d["bands"][w].get(k) is None else d["bands"][w][k] for w in keys], dtype=float) if f else [d["bands"][w][k] for w in keys]  # noqa: E731
        return cls(method=d["method"], fit_method=d["fit_method"],
                   wavelength=np.array([float(w) for w in keys]),
                   c=get("c", True), status=get("status", False), slope=get("slope", True),
                   intercept=get("intercept", True), r=get("r", True), effect=get("effect", True),
                   t=get("t", True), n_samples=int(d.get("n_samples", 0)),
                   calc_mask=d.get("calc_mask", {}), apply_mask=d.get("apply_mask", {}),
                   diagnostic=d.get("diagnostic", {}), source=d.get("source", {}),
                   meta={**d.get("meta", {}), "provenance": d.get("provenance", {})})

    @classmethod
    def from_json(cls, path) -> "TopoCoefficients":
        return cls.from_dict(json.loads(Path(path).read_text()))


# --- BRDF ------------------------------------------------------------------------------
@dataclass
class BRDFCoefficients:
    """One group's FlexBRDF coefficients with provenance."""

    fit: FlexFit
    mode: str                          # fit
    group: list = field(default_factory=list)        # stems of the images fitted together
    calc_mask: dict = field(default_factory=dict)
    apply_mask: dict = field(default_factory=dict)
    diversity: dict = field(default_factory=dict)    # angular-diversity check
    source: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    @property
    def wavelength(self) -> np.ndarray:
        return np.asarray(self.fit.wavelength, float)

    @property
    def feasible(self) -> bool:
        return self.diversity.get("verdict", "ok") == "ok"

    def summary(self) -> str:
        f = self.fit
        r2 = np.nanmedian(f.r2) if np.isfinite(f.r2).any() else np.nan
        return (f"brdf {self.mode} {f.volume}/{f.geometric} b/r={f.b_r} h/b={f.h_b}: "
                f"{f.coeffs.shape[0]} bands x {len(f.bins)} bins, sza_ref {np.degrees(f.sza_ref):.2f} deg, "
                f"median r2 {r2:.3f}, group of {len(self.group)}, diversity={self.diversity.get('verdict', '?')}")

    def to_dict(self) -> dict:
        d = self.fit.to_dict()
        d.update({"format": FORMAT, "version": VERSION, "kind": "brdf", "mode": self.mode,
                  "group": list(self.group), "calc_mask": self.calc_mask, "apply_mask": self.apply_mask,
                  "diversity": self.diversity, "source": self.source, "meta": self.meta,
                  "provenance": self.meta.get("provenance") or provenance()})
        return _jsonable(d)

    def to_json(self, path) -> Path:
        path = Path(path)
        if path.suffix != ".json":
            path.mkdir(parents=True, exist_ok=True)
            name = self.source.get("group_id") or (self.group[0] if self.group else "group")
            path = path / f"{name}_brdf_coeffs.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=1))
        return path

    @classmethod
    def from_dict(cls, d: dict) -> "BRDFCoefficients":
        if d.get("kind") != "brdf":
            raise ValueError(f"not a hyperproc BRDF coefficient file (kind={d.get('kind')!r})")
        return cls(fit=FlexFit.from_dict(d), mode=d.get("mode", "fit"), group=d.get("group", []),
                   calc_mask=d.get("calc_mask", {}), apply_mask=d.get("apply_mask", {}),
                   diversity=d.get("diversity", {}), source=d.get("source", {}),
                   meta={**d.get("meta", {}), "provenance": d.get("provenance", {})})

    @classmethod
    def from_json(cls, path) -> "BRDFCoefficients":
        return cls.from_dict(json.loads(Path(path).read_text()))


def load(path):
    """Open either kind of coefficient file by its ``kind`` field."""
    d = json.loads(Path(path).read_text())
    kind = d.get("kind")
    if kind == "topo":
        return TopoCoefficients.from_dict(d)
    if kind == "brdf":
        return BRDFCoefficients.from_dict(d)
    raise ValueError(f"{path}: unknown coefficient kind {kind!r}")
