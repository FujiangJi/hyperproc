"""Run topographic and BRDF corrections on the cubes the readers return.

The flow is *sample -> fit -> apply -> export*, and each step is a function
you can call on its own:

* :func:`sample_image` reads a spread of whole reader chunks from one cube
  (all bands, ~10% of the image, capped) and keeps everything a fit needs:
  reflectance, geometry, NDVI, the six Zhai index bands, the swath footprint.
  Chunk-aligned reads matter: the cubes live on slow disks and a request that
  straddles two compressed chunks costs both.
* :func:`fit_topo` fits one image's SCS+C (or cosine / C / SCS) coefficients
  and runs the illumination diagnostic whose verdict says whether the
  correction is warranted for that product.
* :func:`fit_brdf` pools the samples of a group of images - the lines of one
  site and flight day - and fits FlexBRDF, after checking that the group's
  view geometry is diverse enough for the coefficients to be identifiable.

This module is for **airborne** imaging spectroscopy (NEON AOP, the AVIRIS
family): the corrections rely on per-pixel terrain layers and on the
across-track view-angle diversity of flightline swaths. Satellite products
(EMIT, EnMAP, PRISMA, DESIS, PACE, Tanager) are refused at every entry point.
* :func:`apply` builds the corrected cube lazily (dask), block by block, so
  export streams; :func:`export` writes GeoTIFF + band table + provenance.
* :func:`view_dependence` and :func:`overlap_agreement` are the real-data
  consistency checks the notebooks report.

Nothing here needs a coefficient file from anywhere else; the fits are made
from the cubes themselves and written with :mod:`hyperproc.correct.coefficients`.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import xarray as xr

from hyperproc.correct import brdf as B
from hyperproc.correct import masks as M
from hyperproc.correct import topo as T
from hyperproc.correct.coefficients import (BRDFCoefficients, TopoCoefficients,
                                            align_wavelengths, provenance)
from hyperproc.correct.kernels import kernel_pair

# --- default mask specifications ------------------------------------------------------
#: Pixels a topographic C is fitted on: vegetated, sloped, lit, not cloud/shadow.
TOPO_CALC = {"ndvi": [0.1, 1.0], "slope_min_deg": 5.0, "cos_i_min": 0.12,
             "cloud": {"T1": 1.0, "t2": 0.5, "t3": 1 / 3, "t4": 2 / 3, "T7": 15, "T8": 15}}
#: Pixels the topographic correction is applied to.
TOPO_APPLY = {"ndvi": [0.1, 1.0], "slope_min_deg": 5.0, "cos_i_min": 0.12}
#: Pixels a BRDF fit is drawn from: vegetated, away from nadir and the swath edge, not cloud/shadow.
BRDF_CALC = {"ndvi": [0.1, 1.0], "vza_min_deg": 2.0, "edge_px": 30,
             "cloud": {"T1": 0.01, "t2": 0.1, "t3": 0.25, "t4": 0.5, "T7": 9, "T8": 9}}
#: Pixels the BRDF normalisation is applied to.
BRDF_APPLY = {"ndvi": [0.05, 1.0]}
#: Nominal wavelengths of the index bands (NDVI and the Zhai cloud test).
INDEX_BANDS = {"blue": 440.0, "green": 550.0, "red": 660.0, "nir": 850.0, "swir1": 1570.0, "swir2": 2110.0}
GEOMETRY = ("sza", "saa", "vza", "vaa", "slope", "aspect")
#: Sensors whose swath geometry supports fitting FlexBRDF: airborne pushbroom/whiskbroom lines.
AIRBORNE_SENSORS = ("NEON", "AVIRIS", "AVIRIS-3", "AVIRIS-NG", "AVIRIS-CLASSIC", "AVIRIS-5")


def is_airborne(sensor) -> bool:
    """True for the airborne sensors this module serves."""
    s = str(sensor or "").upper()
    return s in AIRBORNE_SENSORS or s.startswith("AVIRIS") or s.startswith("NEON")


def _require_airborne(sensor, what: str) -> None:
    if not is_airborne(sensor):
        raise ValueError(f"hyperproc.correct {what} is for airborne data (NEON, AVIRIS); {sensor!r} is not supported")


def _main_var(ds: xr.Dataset) -> str:
    from hyperproc.io import main_var
    return main_var(ds)


def _index_bands(wavelength: np.ndarray) -> dict:
    """Band index of each index band present in this cube (within 40 nm)."""
    wl = np.asarray(wavelength, float)
    out = {}
    for name, w in INDEX_BANDS.items():
        i = int(np.argmin(np.abs(wl - w)))
        if abs(wl[i] - w) <= 40.0:
            out[name] = i
    for req in ("red", "nir"):
        if req not in out:
            raise ValueError(f"cube has no band near {INDEX_BANDS[req]:.0f} nm; cannot form NDVI")
    return out


def _cloud_stats(index: dict, valid=None) -> dict:
    """Zhai scene statistics, or ``{"n": 0}`` (no cloud test) when the cube has
    no blue/green index band - a ``wl_range`` starting above 480 nm, say."""
    if "blue" not in index or "green" not in index:
        import warnings
        warnings.warn("no band near 440/550 nm in this cube: the cloud/shadow test is skipped for its samples")
        return {"n": 0}
    return M.zhai_stats(index["blue"], index["green"], index["red"], index["nir"],
                        index.get("swir1"), index.get("swir2"), valid=valid)


def _cloud_mask(index: dict, valid, stats, params) -> np.ndarray:
    """Zhai cloud/shadow flags, all False when the statistics are empty."""
    if not stats or stats.get("n", 0) == 0 or "blue" not in index or "green" not in index:
        return np.zeros(index["nir"].shape, dtype=bool)
    return M.zhai_cloud(index["blue"], index["green"], index["red"], index["nir"],
                        index.get("swir1"), index.get("swir2"), valid=valid, stats=stats, **params)


def _geometry_2d(ds: xr.Dataset, keys=GEOMETRY, need=GEOMETRY) -> dict:
    """Geometry layers as float64 radians (NaN where missing). Layers in
    ``need`` must exist; the others are filled with NaN when absent, so a
    scene with angles but no terrain layers can still take a BRDF
    normalisation (not a topographic correction)."""
    g = {}
    for k in keys:
        if k in ds:
            g[k] = np.radians(np.asarray(ds[k].values, dtype="float64"))
        elif k in need:
            raise ValueError(f"dataset lacks geometry layer {k!r}; open with geometry=True (or, for slope/aspect, "
                             f"a product with terrain layers - external DEM support is a later step)")
        else:
            g[k] = np.full((ds.sizes["y"], ds.sizes["x"]), np.nan)
    return g


# --- sampling ------------------------------------------------------------------------------
@dataclass
class Sample:
    """What a fit needs from one image, at a spread of sampled pixels."""

    stem: str
    sensor: str
    level: str
    path: str
    wavelength: np.ndarray            # (nb,)
    good: np.ndarray                  # (nb,) bool - the reader's good-band flag
    rho: np.ndarray                   # (n, nb) float32 reflectance
    sza: np.ndarray; saa: np.ndarray; vza: np.ndarray; vaa: np.ndarray   # (n,) radians
    slope: np.ndarray; aspect: np.ndarray                                # (n,) radians
    cos_i: np.ndarray; raa: np.ndarray; ndvi: np.ndarray                 # (n,)
    rows: np.ndarray; cols: np.ndarray                                   # (n,) image indices
    edge_ok: np.ndarray               # (n,) True when >= edge_px from the swath edge
    edge_px: int
    index: dict                       # name -> (n,) index band reflectance
    blocks: list                      # per block: dict(y0, x0, local, index2d, valid2d)
    all_ndvi: np.ndarray              # every valid pixel of the sampled blocks
    cloud_stats: dict                 # Zhai scene statistics from the sampled blocks
    fraction: float
    seed: int
    n_valid_total: int
    elapsed: float = 0.0
    strategy: str = "chunks"
    topo_sums: dict | None = None      # whole-image per-band regression sums over the topo calc mask (pixels strategy)
    cos_i_calc: np.ndarray | None = None   # cos i of (a large random subset of) the whole-image topo calc pixels
    n_calc_topo: int = 0
    _cloud_cache: dict = field(default_factory=dict, repr=False)
    _cloud_precomputed: dict = field(default_factory=dict, repr=False)

    @property
    def n(self) -> int:
        return int(self.rho.shape[0])

    def cloud_flags(self, params: dict) -> np.ndarray:
        """Zhai cloud/shadow flag per sampled pixel (True = bad), evaluated in 2-D
        on each sampled block with the scene-wide statistics (or, for the
        whole-image strategy, taken from the mask computed over the full image)."""
        key = json.dumps(params, sort_keys=True)
        if key in self._cloud_cache:
            return self._cloud_cache[key]
        if key in self._cloud_precomputed:
            return self._cloud_precomputed[key]
        if self.strategy == "pixels":
            raise ValueError("whole-image sample: cloud flags exist only for the calc-mask cloud parameters used at sampling time")
        out = np.zeros(self.n, dtype=bool)
        pos = 0
        for b in self.blocks:
            idx = b["index2d"]
            m2 = _cloud_mask(idx, b["valid2d"], self.cloud_stats, params)
            k = len(b["local"])
            out[pos:pos + k] = m2.ravel()[b["local"]]
            pos += k
        self._cloud_cache[key] = out
        return out

    def topo_calc_mask(self, spec: dict = TOPO_CALC) -> np.ndarray:
        lo, hi = spec["ndvi"]
        m = (np.isfinite(self.ndvi) & (self.ndvi >= lo) & (self.ndvi <= hi)
             & (self.slope >= np.radians(spec["slope_min_deg"])) & (self.cos_i >= spec["cos_i_min"]))
        if spec.get("cloud"):
            m &= ~self.cloud_flags(spec["cloud"])
        return m

    def topo_apply_mask(self, spec: dict = TOPO_APPLY) -> np.ndarray:
        lo, hi = spec["ndvi"]
        return (np.isfinite(self.ndvi) & (self.ndvi >= lo) & (self.ndvi <= hi)
                & (self.slope >= np.radians(spec["slope_min_deg"])) & (self.cos_i >= spec["cos_i_min"]))

    def brdf_calc_mask(self, spec: dict = BRDF_CALC, volume="ross_thick", geometric="li_dense_r",
                       b_r=1.0, h_b=2.0) -> np.ndarray:
        lo, hi = spec["ndvi"]
        kv, kg = kernel_pair(self.sza, self.vza, self.raa, volume, geometric, b_r, h_b)
        m = (np.isfinite(self.ndvi) & (self.ndvi >= lo) & (self.ndvi <= hi)
             & (self.vza >= np.radians(spec.get("vza_min_deg", 0.0))) & M.kernel_finite(kv, kg))
        if spec.get("edge_px", 0):
            if spec["edge_px"] != self.edge_px:
                raise ValueError(f"sample was taken with edge_px={self.edge_px}, spec asks {spec['edge_px']}")
            m &= self.edge_ok
        if spec.get("cloud"):
            m &= ~self.cloud_flags(spec["cloud"])
        return m

    def summary(self) -> str:
        if self.strategy == "pixels":
            return (f"{self.stem}: whole image read ({self.n_valid_total:,} valid px); random {self.fraction:.0%} kept for the BRDF fit "
                    f"= {self.n:,} px; topo C from all {self.n_calc_topo:,} calc-mask px; "
                    f"vza {np.degrees(np.nanpercentile(self.vza, 5)):.1f}-{np.degrees(np.nanpercentile(self.vza, 95)):.1f} deg, "
                    f"sza {np.degrees(np.nanmean(self.sza)):.1f} deg, read in {self.elapsed:.0f} s")
        return (f"{self.stem}: {self.n:,} sampled px from {len(self.blocks)} blocks "
                f"({self.fraction:.0%} of the image, {self.n_valid_total:,} valid px seen), "
                f"vza {np.degrees(np.nanpercentile(self.vza, 5)):.1f}-{np.degrees(np.nanpercentile(self.vza, 95)):.1f} deg, "
                f"sza {np.degrees(np.nanmean(self.sza)):.1f} deg, read in {self.elapsed:.0f} s")


def sample_image(ds: xr.Dataset, fraction: float = 0.10, max_pixels: int | None = None,
                 seed: int = 0, edge_px: int = 30, min_blocks: int = 4, strategy: str = "pixels",
                 topo_calc: dict = TOPO_CALC, brdf_calc: dict = BRDF_CALC) -> Sample:
    """Build the sample the fits are made from.

    ``strategy="pixels"`` (default) is the reference procedure: the **whole
    flightline** is read once to build every mask on every pixel (valid,
    NDVI, Zhai cloud/shadow with scene statistics, swath edge); a **random**
    ``fraction`` of the pixels passing the valid and NDVI masks is then drawn
    and its full spectra read for the BRDF fit; and the topographic C is later
    fitted on **all** pixels of the topo calc mask, from per-band regression
    sums accumulated while reading (exactly the all-pixel NNLS/OLS result,
    without holding the cube in memory). Cost: two passes over the cube.
    ``max_pixels`` caps the random draw (None = no cap; memory is
    n x bands x 4 bytes).

    ``strategy="chunks"`` is the cheap alternative: ``fraction`` of the reader
    chunks, spaced evenly over the chunk grid, are read and at most
    ``max_pixels`` (default 250,000) random pixels are kept from them; cloud
    statistics and the NDVI population come from the chunks read only. One
    tenth of a pass instead of two - use it for quick looks.
    """
    _require_airborne(ds.attrs.get("sensor"), "sampling")
    if strategy == "pixels":
        return _sample_pixels(ds, fraction, max_pixels, seed, edge_px, topo_calc, brdf_calc)
    if strategy != "chunks":
        raise ValueError("strategy must be 'pixels' or 'chunks'")
    return _sample_chunks(ds, fraction, 250_000 if max_pixels is None else max_pixels, seed, edge_px, min_blocks)


def _sample_chunks(ds: xr.Dataset, fraction: float, max_pixels: int, seed: int, edge_px: int, min_blocks: int) -> Sample:
    t0 = time.time()
    var = _main_var(ds)
    da = ds[var]
    if da.chunks is None:
        da = da.chunk({"y": 256, "x": -1, "wavelength": -1})
    elif len(da.chunks[da.get_axis_num("wavelength")]) > 1:
        da = da.chunk({"wavelength": -1})
    da = da.transpose("y", "x", "wavelength")
    ych, xch = da.chunks[0], da.chunks[1]
    yoff = np.concatenate([[0], np.cumsum(ych)]); xoff = np.concatenate([[0], np.cumsum(xch)])
    grid = [(iy, ix) for iy in range(len(ych)) for ix in range(len(xch))]
    n_blocks = int(np.clip(round(fraction * len(grid)), min(min_blocks, len(grid)), len(grid)))
    pick = [grid[int((i + 0.5) * len(grid) / n_blocks)] for i in range(n_blocks)]

    wl = np.asarray(ds.wavelength.values, float)
    good = (np.asarray(ds.good_wavelength.values, bool) if "good_wavelength" in ds.coords or "good_wavelength" in ds
            else np.ones(wl.size, bool))
    ib = _index_bands(wl)
    g2 = _geometry_2d(ds)
    footprint = np.isfinite(g2["vza"]) & np.isfinite(g2["sza"]) & np.isfinite(g2["slope"])
    edge_ok2 = M.edge_mask(footprint, edge_px) if edge_px else footprint

    rng = np.random.default_rng(seed)
    cap = max(1, max_pixels // n_blocks)
    rho_l, rows_l, cols_l, blocks, all_ndvi, n_valid = [], [], [], [], [], 0
    for iy, ix in pick:
        ys = slice(int(yoff[iy]), int(yoff[iy + 1])); xs = slice(int(xoff[ix]), int(xoff[ix + 1]))
        blk = np.asarray(da.isel(y=ys, x=xs).values, dtype="float32")             # (by, bx, nb)
        nir = blk[..., ib["nir"]]; red = blk[..., ib["red"]]
        valid = np.isfinite(nir) & np.isfinite(red) & footprint[ys, xs]
        index2d = {k: blk[..., i] for k, i in ib.items()}
        ndvi2d = M.ndi(nir, red)
        all_ndvi.append(ndvi2d[valid].astype("float32"))
        n_valid += int(valid.sum())
        flat = np.flatnonzero(valid)
        take = np.sort(rng.choice(flat, min(cap, flat.size), replace=False)) if flat.size else flat
        r, c = np.unravel_index(take, valid.shape)
        rho_l.append(blk[r, c, :]); rows_l.append(r + ys.start); cols_l.append(c + xs.start)
        blocks.append({"y0": ys.start, "x0": xs.start, "local": take, "index2d": index2d, "valid2d": valid})
    rho = np.concatenate(rho_l) if rho_l else np.zeros((0, wl.size), "float32")
    rows = np.concatenate(rows_l).astype(int); cols = np.concatenate(cols_l).astype(int)
    geo = {k: g2[k][rows, cols] for k in GEOMETRY}
    cos_i = T.cos_incidence(geo["sza"], geo["saa"], geo["slope"], geo["aspect"])
    index = {k: rho[:, i] for k, i in ib.items()}
    all_v = np.concatenate(all_ndvi) if all_ndvi else np.zeros(0, "float32")
    # scene statistics for the cloud thresholds, from every valid pixel of the blocks read
    cat = {k: np.concatenate([b["index2d"][k][b["valid2d"]] for b in blocks]) for k in ib}
    stats = _cloud_stats(cat)
    return Sample(stem=str(ds.attrs.get("stem") or ds.attrs.get("granule") or "image"),
                  sensor=str(ds.attrs.get("sensor", "?")), level=str(ds.attrs.get("level", "?")),
                  path=str(ds.attrs.get("source_path", ds.encoding.get("source", ""))),
                  wavelength=wl, good=good, rho=rho, sza=geo["sza"], saa=geo["saa"], vza=geo["vza"],
                  vaa=geo["vaa"], slope=geo["slope"], aspect=geo["aspect"], cos_i=cos_i,
                  raa=geo["vaa"] - geo["saa"], ndvi=M.ndi(index["nir"], index["red"]), rows=rows, cols=cols,
                  edge_ok=edge_ok2[rows, cols], edge_px=edge_px, index=index, blocks=blocks, all_ndvi=all_v,
                  cloud_stats=stats, fraction=n_blocks / len(grid), seed=seed, n_valid_total=n_valid,
                  elapsed=time.time() - t0, strategy="chunks")


def _iter_chunks(da):
    """Yield (ys, xs, block) for every reader chunk of a (y, x, wavelength) dask array, in order."""
    ych, xch = da.chunks[0], da.chunks[1]
    yoff = np.concatenate([[0], np.cumsum(ych)]); xoff = np.concatenate([[0], np.cumsum(xch)])
    for iy in range(len(ych)):
        for ix in range(len(xch)):
            ys = slice(int(yoff[iy]), int(yoff[iy + 1])); xs = slice(int(xoff[ix]), int(xoff[ix + 1]))
            yield ys, xs, np.asarray(da.isel(y=ys, x=xs).values, dtype="float32")


def _sample_pixels(ds: xr.Dataset, fraction: float, max_pixels, seed: int, edge_px: int, topo_calc: dict, brdf_calc: dict) -> Sample:
    """Whole-image masks, random pixel draw, all-pixel topographic sums (two passes)."""
    t0 = time.time()
    var = _main_var(ds)
    da = ds[var]
    if da.chunks is None:
        da = da.chunk({"y": 256, "x": -1, "wavelength": -1})
    elif len(da.chunks[da.get_axis_num("wavelength")]) > 1:
        da = da.chunk({"wavelength": -1})
    da = da.transpose("y", "x", "wavelength")
    ny, nx, nb = da.shape
    wl = np.asarray(ds.wavelength.values, float)
    good = (np.asarray(ds.good_wavelength.values, bool) if "good_wavelength" in ds.coords or "good_wavelength" in ds
            else np.ones(wl.size, bool))
    ib = _index_bands(wl)
    g2 = _geometry_2d(ds)
    footprint = np.isfinite(g2["vza"]) & np.isfinite(g2["sza"]) & np.isfinite(g2["slope"])
    edge_ok2 = M.edge_mask(footprint, edge_px) if edge_px else footprint
    cos_i2 = T.cos_incidence(g2["sza"], g2["saa"], g2["slope"], g2["aspect"])

    # ---- pass 1: every pixel's index bands -> masks on the whole image -----------------
    index2d = {k: np.full((ny, nx), np.nan, "float32") for k in ib}
    for ys, xs, blk in _iter_chunks(da):
        for k, i in ib.items():
            index2d[k][ys, xs] = blk[..., i]
    valid2d = np.isfinite(index2d["nir"]) & np.isfinite(index2d["red"]) & footprint
    ndvi2d = M.ndi(index2d["nir"], index2d["red"])
    stats = _cloud_stats(index2d, valid=valid2d)
    cloud2d = {}
    for spec in (topo_calc, brdf_calc):
        prm = spec.get("cloud")
        if prm:
            key = json.dumps(prm, sort_keys=True)
            if key not in cloud2d:
                cloud2d[key] = _cloud_mask(index2d, valid2d, stats, prm)
    lo, hi = topo_calc["ndvi"]
    calc_topo2d = (valid2d & (ndvi2d >= lo) & (ndvi2d <= hi) & (g2["slope"] >= np.radians(topo_calc["slope_min_deg"])) & (cos_i2 >= topo_calc["cos_i_min"]))
    if topo_calc.get("cloud"):
        calc_topo2d &= ~cloud2d[json.dumps(topo_calc["cloud"], sort_keys=True)]
    # random draw among valid pixels (the calc masks are applied later on the sample, as the fits do)
    rng = np.random.default_rng(seed)
    flat_valid = np.flatnonzero(valid2d)
    n_keep = int(round(fraction * flat_valid.size))
    if max_pixels is not None:
        n_keep = min(n_keep, int(max_pixels))
    keep = np.zeros(ny * nx, dtype=bool)
    keep[rng.choice(flat_valid, n_keep, replace=False)] = True
    keep2d = keep.reshape(ny, nx)

    # ---- pass 2: spectra of the drawn pixels + all-pixel topographic sums -------------
    rho_l, rows_l, cols_l, blocks = [], [], [], []
    sums = {k: np.zeros(nb, "float64") for k in ("n", "sx", "sy", "sxy", "sxx", "syy")}
    for ys, xs, blk in _iter_chunks(da):
        k2 = keep2d[ys, xs]
        if k2.any():
            r, c = np.nonzero(k2)
            rho_l.append(blk[r, c, :]); rows_l.append(r + ys.start); cols_l.append(c + xs.start)
            blocks.append({"y0": ys.start, "x0": xs.start, "local": np.ravel_multi_index((r, c), k2.shape), "valid2d": valid2d[ys, xs], "index2d": {}})
        m2 = calc_topo2d[ys, xs]
        if m2.any():
            x = cos_i2[ys, xs][m2].astype("float64"); Y = blk[m2, :].astype("float64")
            ok = np.isfinite(Y)
            Y0 = np.where(ok, Y, 0.0)
            sums["n"] += ok.sum(0); sums["sx"] += (x[:, None] * ok).sum(0); sums["sy"] += Y0.sum(0)
            sums["sxy"] += (x[:, None] * Y0).sum(0); sums["sxx"] += ((x ** 2)[:, None] * ok).sum(0); sums["syy"] += (Y0 ** 2).sum(0)
    rho = np.concatenate(rho_l) if rho_l else np.zeros((0, nb), "float32")
    rows = np.concatenate(rows_l).astype(int); cols = np.concatenate(cols_l).astype(int)
    geo = {k: g2[k][rows, cols] for k in GEOMETRY}
    index = {k: index2d[k][rows, cols] for k in ib}
    pre = {key: m[rows, cols] for key, m in cloud2d.items()}
    calc_ci = cos_i2[calc_topo2d]
    if calc_ci.size > 200_000:
        calc_ci = rng.choice(calc_ci, 200_000, replace=False)
    smp = Sample(stem=str(ds.attrs.get("stem") or ds.attrs.get("granule") or "image"),
                 sensor=str(ds.attrs.get("sensor", "?")), level=str(ds.attrs.get("level", "?")),
                 path=str(ds.attrs.get("source_path", ds.encoding.get("source", ""))),
                 wavelength=wl, good=good, rho=rho, sza=geo["sza"], saa=geo["saa"], vza=geo["vza"], vaa=geo["vaa"],
                 slope=geo["slope"], aspect=geo["aspect"], cos_i=cos_i2[rows, cols], raa=geo["vaa"] - geo["saa"],
                 ndvi=ndvi2d[rows, cols], rows=rows, cols=cols, edge_ok=edge_ok2[rows, cols], edge_px=edge_px,
                 index=index, blocks=blocks, all_ndvi=ndvi2d[valid2d].astype("float32"), cloud_stats=stats,
                 fraction=float(fraction), seed=seed, n_valid_total=int(valid2d.sum()), elapsed=time.time() - t0,
                 strategy="pixels", topo_sums=sums, cos_i_calc=np.asarray(calc_ci, "float64"), n_calc_topo=int(calc_topo2d.sum()))
    smp._cloud_precomputed = pre
    return smp


def merge_samples(samples, stem: str | None = None) -> Sample:
    """Pool the samples of several cubes that belong together - the chunks of
    one AVIRIS-5 flightline - into one :class:`Sample`, so a topographic C
    is fitted per flightline rather than per chunk. Cloud statistics are
    recomputed over all pooled blocks."""
    samples = list(samples)
    if len(samples) == 1:
        return samples[0]
    wl = samples[0].wavelength
    for s in samples[1:]:
        if s.wavelength.size != wl.size or np.max(np.abs(s.wavelength - wl)) > 1.0:
            raise ValueError("samples to merge must share one wavelength axis")
    cat = lambda k: np.concatenate([getattr(s, k) for s in samples])  # noqa: E731
    blocks = [dict(b, source=s.stem) for s in samples for b in s.blocks]
    ib = _index_bands(wl)
    if all(s.strategy == "pixels" for s in samples):
        # whole-image samples carry no per-block index bands; pool the per-image scene
        # statistics exactly (count-weighted means, min of mins, max of maxes). The cloud
        # flags of the pooled pixels were evaluated per image, as the reference does per file.
        st = [s.cloud_stats for s in samples if s.cloud_stats.get("n", 0) > 0]
        ntot = sum(x["n"] for x in st)
        stats = {"n": int(ntot), "ci2_mean": sum(x["ci2_mean"] * x["n"] for x in st) / ntot, "ci2_max": max(x["ci2_max"] for x in st),
                 "csi_min": min(x["csi_min"] for x in st), "csi_mean": sum(x["csi_mean"] * x["n"] for x in st) / ntot,
                 "blue_min": min(x["blue_min"] for x in st), "blue_mean": sum(x["blue_mean"] * x["n"] for x in st) / ntot} if ntot else {"n": 0}
    else:
        catidx = {k: np.concatenate([b["index2d"][k][b["valid2d"]] for b in blocks]) for k in ib}
        stats = _cloud_stats(catidx)
    sums = None
    if all(s.topo_sums is not None for s in samples):
        sums = {k: np.sum([s.topo_sums[k] for s in samples], axis=0) for k in samples[0].topo_sums}
    cic = np.concatenate([s.cos_i_calc for s in samples]) if all(s.cos_i_calc is not None for s in samples) else None
    pre = {}
    keys = set.intersection(*[set(s._cloud_precomputed) for s in samples]) if samples else set()
    for k in keys:
        pre[k] = np.concatenate([s._cloud_precomputed[k] for s in samples])
    merged = Sample(stem=stem or samples[0].stem.rsplit("_", 2)[0] + f"_pooled{len(samples)}", sensor=samples[0].sensor,
                  level=samples[0].level, path=";".join(s.path for s in samples), wavelength=wl, good=samples[0].good,
                  rho=cat("rho"), sza=cat("sza"), saa=cat("saa"), vza=cat("vza"), vaa=cat("vaa"), slope=cat("slope"),
                  aspect=cat("aspect"), cos_i=cat("cos_i"), raa=cat("raa"), ndvi=cat("ndvi"), rows=cat("rows"), cols=cat("cols"),
                  edge_ok=cat("edge_ok"), edge_px=samples[0].edge_px, index={k: cat_i for k, cat_i in
                  ((k, np.concatenate([s.index[k] for s in samples])) for k in samples[0].index)},
                  blocks=blocks, all_ndvi=cat("all_ndvi"), cloud_stats=stats,
                  fraction=float(np.mean([s.fraction for s in samples])), seed=samples[0].seed,
                  n_valid_total=int(sum(s.n_valid_total for s in samples)), elapsed=float(sum(s.elapsed for s in samples)),
                  strategy=samples[0].strategy, topo_sums=sums, cos_i_calc=cic, n_calc_topo=int(sum(s.n_calc_topo for s in samples)))
    merged._cloud_precomputed = pre
    return merged


def per_block_effects(sample: Sample, wavelengths=(549, 659, 849, 1651, 2202), spec: dict = TOPO_CALC,
                      min_pixels: int = 500, split: int = 1) -> list:
    """The illumination effect fitted separately in each sampled block.

    A single C per image assumes one relation between reflectance and cos i
    over the whole image. This shows whether that holds: blocks that agree in
    sign and size support a per-image C; blocks that disagree mean the pooled
    slope is driven by *which* regions were pooled, not by illumination, and
    the verdict should be read with that in mind. ``split`` divides every
    sampled block into ``split x split`` sub-blocks (no extra reading), which
    gives the consistency statistic more, smaller regions to compare.
    """
    wl = sample.wavelength
    bands = [int(np.argmin(np.abs(wl - w))) for w in wavelengths]
    m = sample.topo_calc_mask(spec)
    rows, pos = [], 0
    split = max(1, int(split))
    for b in sample.blocks:
        k = len(b["local"]); sl = slice(pos, pos + k); pos += k
        by, bx = b["valid2d"].shape
        r, c = np.unravel_index(np.asarray(b["local"], dtype=int), (by, bx))
        sub = (r * split // max(by, 1)) * split + (c * split // max(bx, 1))
        for q in range(split * split):
            sel = np.flatnonzero(sub == q) if split > 1 else np.arange(k)
            mm = np.zeros(k, dtype=bool); mm[sel] = m[sl][sel]
            row = {"source": b.get("source", sample.stem), "y0": int(b["y0"] + (q // split) * by // split),
                   "x0": int(b["x0"] + (q % split) * bx // split), "n": int(mm.sum()),
                   "ndvi_mean": float(np.nanmean(sample.ndvi[sl][mm])) if mm.any() else np.nan,
                   "cos_i_mean": float(np.nanmean(sample.cos_i[sl][mm])) if mm.any() else np.nan}
            for w, j in zip(wavelengths, bands):
                f = T.fit_c(sample.rho[sl][mm, j], sample.cos_i[sl][mm], method="ols") if mm.sum() >= min_pixels else None
                row[f"effect_{int(w)}"] = np.nan if (f is None or f.effect is None) else float(f.effect)
                row[f"t_{int(w)}"] = np.nan if (f is None or f.t is None) else float(f.t)
            rows.append(row)
    return rows


# --- topographic fit ---------------------------------------------------------------------------
def fit_topo(sample: Sample, method: str = "scs+c", fit: str = "nnls", calc: dict = TOPO_CALC,
             apply_spec: dict = TOPO_APPLY, diagnostic_bands: int = 40, min_samples: int = 100,
             block_agreement: float = 0.7, block_min_pixels: int = 500, block_split: int = 2,
             block_t: float = 2.0) -> TopoCoefficients:
    """Fit one image's topographic coefficients and judge whether to use them.

    Every good band gets a :func:`hyperproc.correct.topo.fit_c` - by default
    NNLS, which keeps the intercept and therefore C non-negative (an OLS fit
    on a product with an additive offset gives C < 0 and a singular factor;
    with ``fit="ols"`` such bands come back ``negative_intercept`` and are not
    corrected). The illumination diagnostic runs on up to ``diagnostic_bands`` good bands and
    its verdict (``correct | skip | refuse | inconclusive``) is stored with the
    coefficients. A ``correct`` or ``refuse`` verdict additionally requires
    the effect to be spatially consistent - at least ``block_agreement`` of the
    sampled blocks, each split into ``block_split x block_split`` sub-blocks
    with >= ``block_min_pixels`` fit pixels and a significant slope of their
    own (|t| >= ``block_t``), must share the pooled sign and their median
    effect must exceed ``min_effect`` - otherwise
    it is downgraded to ``inconclusive`` with the reason recorded. Bands the
    reader flags bad get status ``bad_band`` and no C.
    """
    m = sample.topo_calc_mask(calc)
    nb = sample.wavelength.size
    c = np.full(nb, np.nan); a = np.full(nb, np.nan); b = np.full(nb, np.nan); r = np.full(nb, np.nan)
    eff = np.full(nb, np.nan); t = np.full(nb, np.nan); status = ["bad_band"] * nb
    ci = sample.cos_i[m]
    use_sums = sample.topo_sums is not None and sample.cos_i_calc is not None and sample.cos_i_calc.size > 0
    if use_sums:                                   # every pixel of the whole-image calc mask, from the streamed sums
        p05, p95 = np.percentile(sample.cos_i_calc, [5, 95]); S = sample.topo_sums
    for k in np.flatnonzero(sample.good):
        if use_sums:
            f = T.fit_c_from_sums(S["n"][k], S["sx"][k], S["sy"][k], S["sxy"][k], S["sxx"][k], S["syy"][k], p05, p95,
                                  method=fit, min_samples=min_samples)
        else:
            f = T.fit_c(sample.rho[m, k], ci, method=fit, min_samples=min_samples)
        status[k] = f.status
        a[k] = np.nan if f.slope is None else f.slope; b[k] = np.nan if f.intercept is None else f.intercept
        r[k] = np.nan if f.r is None else f.r; eff[k] = np.nan if f.effect is None else f.effect
        t[k] = np.nan if f.t is None else f.t
        if f.status == "ok":
            c[k] = f.c
    goodidx = np.flatnonzero(sample.good)
    sel = goodidx[np.linspace(0, goodidx.size - 1, min(diagnostic_bands, goodidx.size)).round().astype(int)]
    d = T.illumination_diagnostic(sample.rho[:, sel], sample.cos_i, sample.sza, sample.slope, m,
                                  method=method, fit_method=fit)
    # Spatial consistency: a physical illumination effect shows the same sign in every
    # block with terrain; a between-cover confound (shaded slopes look greener) does not.
    # On one NEON line the pooled effect at 659 nm was -10% from 10 blocks, +6% from 32
    # and +11% from the whole line - so a pooled verdict alone is not trustworthy.
    chk = sample.wavelength[sel[np.linspace(0, sel.size - 1, min(5, sel.size)).round().astype(int)]]
    pb = per_block_effects(sample, wavelengths=chk, spec=calc, min_pixels=block_min_pixels, split=block_split)
    eb = np.array([np.nanmedian([r[k] for k in r if k.startswith("effect_")]) for r in pb if r["n"] >= block_min_pixels])
    tb = np.array([np.nanmedian([r[k] for k in r if k.startswith("t_")]) for r in pb if r["n"] >= block_min_pixels])
    ok_b = np.isfinite(eb) & np.isfinite(tb)
    eb, tb = eb[ok_b], tb[ok_b]
    sig = np.abs(tb) >= block_t                     # only blocks whose own slope is significant carry sign information
    pooled = d["median_effect_before"]
    if sig.sum() >= 5 and np.isfinite(pooled):
        agreement = float(np.mean(np.sign(eb[sig]) == np.sign(pooled)))
        block_median = float(np.median(eb[sig]))
        consistent = agreement >= block_agreement and abs(block_median) >= d["min_effect"]
    elif eb.size >= 3 and np.isfinite(pooled):      # too few significant blocks: no region shows the effect clearly
        agreement, block_median, consistent = float(np.mean(np.sign(eb) == np.sign(pooled))), float(np.median(eb)), False
    else:
        agreement, block_median, consistent = float("nan"), float("nan"), True
    verdict, reason = d["verdict"], None
    if verdict in ("correct", "refuse") and not consistent:
        verdict = "inconclusive"
        reason = (f"illumination effect not consistent across the image: {agreement:.0%} of {int(sig.sum())} blocks with a "
                  f"significant slope (|t|>={block_t:g}; {eb.size} blocks in all) share the pooled sign (need {block_agreement:.0%}), "
                  f"block median {block_median:+.3f} vs pooled {pooled:+.3f}")
    diagnostic = {"verdict": verdict, "verdict_pooled": d["verdict"], "reason": reason,
                  "block_agreement": agreement, "block_median_effect": block_median, "n_blocks": int(eb.size),
                  "n_blocks_significant": int(sig.sum()), "block_t_threshold": block_t,
                  "block_effects": [round(float(x), 4) for x in eb], "block_t": [round(float(x), 2) for x in tb],
                  "median_effect_before": d["median_effect_before"],
                  "median_effect_after": d["median_effect_after"], "median_t_before": d["median_t_before"],
                  "min_effect": d["min_effect"], "cos_i_spread": d["cos_i_spread"],
                  "n_fit": d["n_fit"], "n_test": d["n_test"],
                  "bands": {f"{sample.wavelength[j]:.4f}": {"effect_before": d["effect_before"][i],
                                                            "effect_after": d["effect_after"][i],
                                                            "t_before": d["t_before"][i], "status": str(d["status"][i])}
                            for i, j in enumerate(sel)}}
    return TopoCoefficients(method=method, fit_method=fit, wavelength=sample.wavelength, c=c, status=status,
                            slope=a, intercept=b, r=r, effect=eff, t=t, n_samples=int(sample.n_calc_topo if use_sums else m.sum()),
                            calc_mask=calc, apply_mask=apply_spec, diagnostic=diagnostic,
                            source={"stem": sample.stem, "sensor": sample.sensor, "level": sample.level,
                                    "path": sample.path},
                            meta={"cloud_stats": sample.cloud_stats,
                                  "sampling": {"strategy": sample.strategy, "fraction": sample.fraction, "n_blocks": len(sample.blocks),
                                               "n_pixels": sample.n, "seed": sample.seed,
                                               "c_fitted_on": "all pixels of the calc mask (streamed sums)" if use_sums else "the sampled pixels"},
                                  "provenance": provenance()})


# --- BRDF fit ------------------------------------------------------------------------------------
def angular_diversity(sza, vza, raa, mask=None, volume="ross_thick", geometric="li_dense_r",
                      b_r=1.0, h_b=2.0, span_min_deg=8.0, cond_max=2000.0) -> dict:
    """Can a kernel fit tell f_vol and f_geo apart on this geometry?

    Reports the p05-p95 span of view zenith, the circular spread of relative
    azimuth, and the condition number of the ``[k_vol, k_geo, 1]`` design
    matrix. Verdict ``ok`` needs a view-zenith span of at least
    ``span_min_deg`` and a condition number below ``cond_max``; narrow-swath
    narrow-swath scenes (2-3 degrees of view zenith) fail this, airborne swaths
    (15-20 degrees) pass.
    """
    sza = np.asarray(sza, float); vza = np.asarray(vza, float); raa = np.asarray(raa, float)
    m = np.isfinite(sza) & np.isfinite(vza) & np.isfinite(raa)
    if mask is not None:
        m &= np.asarray(mask, bool)
    n = int(m.sum())
    if n < 100:
        return {"verdict": "insufficient", "n": n, "reason": "fewer than 100 usable pixels"}
    kv, kg = kernel_pair(sza[m], vza[m], raa[m], volume, geometric, b_r, h_b)
    X = np.column_stack([kv, kg, np.ones(n)])
    ok = np.isfinite(X).all(axis=1)
    cond = float(np.linalg.cond(X[ok])) if ok.sum() > 3 else float("inf")
    span = float(np.degrees(np.percentile(vza[m], 95) - np.percentile(vza[m], 5)))
    raa_spread = float(np.degrees(np.sqrt(-2 * np.log(max(1e-12, abs(np.mean(np.exp(1j * raa[m]))))))))
    verdict = "ok" if (span >= span_min_deg and cond <= cond_max) else "insufficient"
    reason = None if verdict == "ok" else (f"view-zenith span {span:.1f} deg < {span_min_deg} deg"
                                            if span < span_min_deg else f"condition number {cond:.0f} > {cond_max:.0f}")
    return {"verdict": verdict, "n": n, "vza_span_deg": span, "vza_p05_deg": float(np.degrees(np.percentile(vza[m], 5))),
            "vza_p95_deg": float(np.degrees(np.percentile(vza[m], 95))), "raa_spread_deg": raa_spread,
            "sza_mean_deg": float(np.degrees(np.nanmean(sza[m]))), "sza_span_deg": float(np.degrees(np.ptp(sza[m]))),
            "condition_number": cond, "span_min_deg": span_min_deg, "cond_max": cond_max, "reason": reason}


def _topo_correct_sample(s: Sample, tc: TopoCoefficients | None, wl: np.ndarray) -> np.ndarray:
    """The sample's spectra topographically corrected with ``tc``, on the
    sample's *own* wavelength axis (``wl`` must be ``s.wavelength``; a group
    member's axis may differ from the first sample's by up to 1 nm, more than
    the 0.5 nm coefficient alignment tolerates)."""
    if tc is None:
        return s.rho
    c = tc.c_for(wl)
    if np.isfinite(tc.c).any() and not np.isfinite(c).any():
        raise ValueError(f"{s.stem}: none of the topographic coefficients ({tc.source.get('stem')}) align with this "
                         "sample's wavelength axis (tolerance 0.5 nm); the BRDF fit would silently see uncorrected "
                         "reflectance for this image")
    cl = [None if not np.isfinite(v) else float(v) for v in c]
    return T.apply_topo(s.rho, s.cos_i, s.sza, s.slope, method=tc.method, c=cl, mask=s.topo_apply_mask(tc.apply_mask or TOPO_APPLY))


def fit_brdf(samples, topo=None, calc: dict = BRDF_CALC, apply_spec: dict = BRDF_APPLY,
             volume: str = "ross_thick", geometric: str = "li_dense_r", b_r: float = 1.0, h_b: float = 2.0,
             sza_ref="group", num_bins: int = 18, ndvi_min: float = 0.05, ndvi_max: float = 1.0,
             perc_min: float = 10, perc_max: float = 95, second_split: bool = True,
             group_id: str | None = None, force: bool = False, force_topo: bool = False,
             **diversity_kw) -> BRDFCoefficients:
    """Fit FlexBRDF on a group of samples (one site, one flight day) - airborne only.

    If ``topo`` (a list of :class:`TopoCoefficients`, one per sample, or
    None entries) is given, each sample is topographically corrected first, so
    the BRDF fit sees the reflectance it will later be applied to. ``sza_ref``
    is ``"group"`` (mean solar zenith of the fitted pixels) or degrees. The
    angular-diversity check runs first; an ``insufficient`` verdict raises
    unless ``force=True``, because coefficients fitted on a narrow view range
    are noise.

    A sample is topographically corrected only when its coefficients' verdict
    is ``"correct"``; for ``skip``/``refuse``/``inconclusive`` the sample is
    used as delivered (with a warning), so the BRDF fit matches what
    :func:`apply` will do with the same default. ``force_topo=True`` applies
    the coefficients regardless - then pass ``force_topo=True`` to ``apply``
    as well, so fit and product agree.
    """
    samples = list(samples)
    if not samples:
        raise ValueError("no samples")
    not_air = [s.stem for s in samples if not is_airborne(s.sensor)]
    if not_air:
        raise ValueError("FlexBRDF is an airborne-swath method: it needs the across-track view-angle diversity of a "
                         f"flightline group. Not airborne: {not_air}.")
    topo = list(topo) if topo is not None else [None] * len(samples)
    if len(topo) != len(samples):
        raise ValueError("topo must have one entry per sample")
    wl = samples[0].wavelength
    for s in samples[1:]:
        if s.wavelength.size != wl.size or np.max(np.abs(s.wavelength - wl)) > 1.0:
            raise ValueError(f"{s.stem}: wavelength axis differs from {samples[0].stem}; group images of one instrument")
    rho_l, sza_l, vza_l, raa_l, ndvi_l, all_ndvi = [], [], [], [], [], []
    per_image = {}
    for s, tc in zip(samples, topo):
        m = s.brdf_calc_mask(calc, volume, geometric, b_r, h_b)
        if tc is not None and tc.verdict != "correct" and not force_topo:
            import warnings
            warnings.warn(f"{s.stem}: topographic verdict is '{tc.verdict}', so the sample enters the BRDF fit "
                          "uncorrected (pass force_topo=True to apply the coefficients anyway)")
            tc = None
        rho = _topo_correct_sample(s, tc, s.wavelength)
        rho_l.append(rho[m]); sza_l.append(s.sza[m]); vza_l.append(s.vza[m]); raa_l.append(s.raa[m]); ndvi_l.append(s.ndvi[m])
        all_ndvi.append(s.all_ndvi)
        per_image[s.stem] = {"n_fit": int(m.sum()), "topo_applied": tc is not None,
                             "topo_verdict": None if tc is None else tc.verdict}
    rho = np.concatenate(rho_l); sza = np.concatenate(sza_l); vza = np.concatenate(vza_l)
    raa = np.concatenate(raa_l); ndvi = np.concatenate(ndvi_l)
    div = angular_diversity(sza, vza, raa, volume=volume, geometric=geometric, b_r=b_r, h_b=h_b, **diversity_kw)
    if div["verdict"] != "ok" and not force:
        raise ValueError(f"BRDF fit not identifiable on this group: {div.get('reason')}. force=True fits anyway.")
    bins = B.dynamic_bins(np.concatenate(all_ndvi), num_bins=num_bins, ndvi_min=ndvi_min, ndvi_max=ndvi_max,
                          perc_min=perc_min, perc_max=perc_max, second_split=second_split)
    ref = float(np.nanmean(sza)) if sza_ref == "group" else float(np.radians(sza_ref))
    fit = B.fit_group(rho, sza, vza, raa, ndvi, wavelength=wl, volume=volume, geometric=geometric,
                      b_r=b_r, h_b=h_b, sza_ref=ref, bins=bins)
    fit.meta.update({"n_pixels_fit": int(rho.shape[0]), "sza_ref_deg": float(np.degrees(ref))})
    gid = group_id or f"{samples[0].sensor}_{samples[0].stem}_group{len(samples)}"
    return BRDFCoefficients(fit=fit, mode="fit", group=[s.stem for s in samples], calc_mask=calc,
                            apply_mask=apply_spec, diversity=div,
                            source={"group_id": gid, "sensor": samples[0].sensor, "level": samples[0].level,
                                    "images": per_image},
                            meta={"bins_from": "all valid pixels of the sampled blocks, pooled over the group",
                                  "ndvi_bins": {"num_bins": num_bins, "ndvi_min": ndvi_min, "ndvi_max": ndvi_max,
                                                "perc_min": perc_min, "perc_max": perc_max, "second_split": second_split},
                                  "provenance": provenance()})


# --- apply -------------------------------------------------------------------------------------
def apply(ds: xr.Dataset, topo: TopoCoefficients | None = None, brdf: BRDFCoefficients | None = None,
          block_bytes: float = 200e6, notes: dict | None = None, force_topo: bool = False,
          brdf_ratio_max: float | None = 5.0) -> xr.Dataset:
    """The corrected cube, lazily: topo first (if given), then BRDF.

    The topographic coefficients are applied only when their verdict is
    ``"correct"``. Otherwise the topo stage is skipped with a warning and the
    product is named for the stages actually applied, unless
    ``force_topo=True`` (recorded in the provenance as ``topo_forced``).
    ``brdf_ratio_max`` bounds the BRDF factor per pixel and band (see
    :func:`hyperproc.correct.brdf.apply_flex`); None disables the bound.

    Returns a copy of ``ds`` whose cube is a dask array evaluated block by
    block when written; geometry layers and coefficients are aligned to the
    cube's wavelength axis here. ``attrs['stem']`` gains ``_topo``, ``_brdf``
    or ``_topo_brdf`` so exports never overwrite the input's name.
    """
    import dask.array as dsk

    if topo is None and brdf is None:
        raise ValueError("nothing to apply: pass topo and/or brdf coefficients")
    _require_airborne(ds.attrs.get("sensor"), "apply")
    var = _main_var(ds)
    da = ds[var].transpose("y", "x", "wavelength")
    ny, nx, nb = da.shape
    wl = np.asarray(ds.wavelength.values, float)
    ib = _index_bands(wl)
    if topo is not None and topo.verdict != "correct" and not force_topo:
        import warnings
        warnings.warn(f"{ds.attrs.get('stem')}: topographic verdict is '{topo.verdict}'; the topo stage is skipped "
                      "(pass force_topo=True to apply the coefficients anyway)")
        topo = None
    # A BRDF-only normalisation needs the four angles; terrain layers only for topo.
    g = _geometry_2d(ds, need=GEOMETRY if topo is not None else GEOMETRY[:4])
    # Keep only what the block function uses, as float32: the seven float64
    # layers of a full AVIRIS line held ~1.9 GB in the closure of every lazy
    # corrected cube.
    sza32 = g["sza"].astype("float32")
    slope32 = g["slope"].astype("float32") if topo is not None else None
    cos_i = T.cos_incidence(g["sza"], g["saa"], g["slope"], g["aspect"]).astype("float32") if topo is not None else None
    c_list = None
    n_topo_bands = 0
    topo_forced = False
    if topo is not None:
        topo_forced = topo.verdict != "correct"
        c = topo.c_for(wl)
        # A negative or non-finite C is refused here, on entry, not later
        # inside a dask block half-way through an export.
        T._check_c([v for v in c if np.isfinite(v)])
        c_list = [None if not np.isfinite(v) else float(v) for v in c]
        n_topo_bands = sum(v is not None for v in c_list)
        if n_topo_bands == 0:
            # Every band was refused (inverted / negative intercept): the stage is a
            # no-op for this image. That is a legitimate outcome in a batch - say so
            # in the provenance rather than abort the run.
            import warnings
            warnings.warn(f"{ds.attrs.get('stem')}: topo coefficients have no C for any band; the topo stage changes nothing")
            c_list = None
    kv = kg = None
    if brdf is not None:
        f = brdf.fit
        if f.wavelength is not None:
            idx = align_wavelengths(f.wavelength, wl, tol=1.0)
            if (idx < 0).any():
                raise ValueError("BRDF coefficients do not cover every band of this cube")
            f = B.FlexFit(bins=f.bins, coeffs=f.coeffs[idx], volume=f.volume, geometric=f.geometric, b_r=f.b_r,
                          h_b=f.h_b, sza_ref=f.sza_ref, n_per_bin=f.n_per_bin, r2=f.r2[idx], wavelength=wl, meta=f.meta)
        kv, kg = kernel_pair(g["sza"], g["vza"], g["vaa"] - g["saa"], f.volume, f.geometric, f.b_r, f.h_b)
        kv = kv.astype("float32"); kg = kg.astype("float32")
        brdf_fit = f
    del g
    t_spec = (topo.apply_mask or TOPO_APPLY) if topo is not None else None
    b_spec = (brdf.apply_mask or BRDF_APPLY) if brdf is not None else None
    t_method = topo.method if topo is not None else None

    rows_max = int(np.clip(block_bytes // (nx * nb * 4), 8, ny))
    if da.chunks is not None:
        # Blocks must not straddle the reader's chunk rows: a block that needs two
        # compressed source chunks costs both, and dask holds the merged slab while
        # splitting it. So use the source chunk height, or an exact divisor of it.
        # Split every source chunk into ceil(h / rows_max) near-equal parts, so no
        # block straddles two compressed source chunks and none degenerates to a
        # single row (the old exact-divisor search did that for a prime height).
        parts = []
        for h in da.chunks[0]:
            k = int(np.ceil(h / rows_max)); base, extra = divmod(int(h), k)
            parts += [base + 1] * extra + [base] * (k - extra)
        rows = max(parts)
        src = da.data.rechunk((tuple(parts), nx, nb))
    else:
        rows = rows_max
        src = dsk.from_array(da.values, chunks=(rows, nx, nb))

    def _block(rho, block_info=None):
        (y0, y1), (x0, x1), _ = block_info[0]["array-location"]
        nir = rho[..., ib["nir"]]; red = rho[..., ib["red"]]
        valid = np.isfinite(nir) & np.isfinite(red)
        ndvi = M.ndi(nir, red)
        out = rho
        if c_list is not None:
            ci = cos_i[y0:y1, x0:x1]; sl = slope32[y0:y1, x0:x1]
            valid &= np.isfinite(ci)
            lo, hi = t_spec["ndvi"]
            m = valid & (ndvi >= lo) & (ndvi <= hi) & (sl >= np.radians(t_spec["slope_min_deg"])) & (ci >= t_spec["cos_i_min"])
            out = T.apply_topo(out, ci, sza32[y0:y1, x0:x1], sl, method=t_method, c=c_list, mask=m)
        if kv is not None:
            lo, hi = b_spec["ndvi"]
            m = valid & (ndvi >= lo) & (ndvi <= hi)
            out = B.apply_flex(out, kv[y0:y1, x0:x1], kg[y0:y1, x0:x1], ndvi, brdf_fit, mask=m, ratio_max=brdf_ratio_max)
        return np.asarray(out, dtype="float32")

    corrected = src.map_blocks(_block, dtype="float32")
    stages = ([] if topo is None else ["topo"]) + ([] if brdf is None else ["brdf"])
    out = ds.copy()
    out[var] = xr.DataArray(corrected, dims=("y", "x", "wavelength"), coords=da.coords, attrs=dict(da.attrs))
    out[var].attrs["corrections"] = ",".join(stages)
    stem = str(ds.attrs.get("stem") or ds.attrs.get("granule") or "cube")
    out.attrs["stem"] = f"{stem}_{'_'.join(stages)}" if stages else stem
    out.attrs["corrections"] = ",".join(stages)
    out.attrs["correction_provenance"] = json.dumps({
        "stages": stages,
        "topo": None if topo is None else {"method": topo.method, "fit_method": topo.fit_method, "verdict": topo.verdict,
                                          "n_bands_with_c": int(np.isfinite(topo.c).sum()), "n_bands_applied": int(n_topo_bands),
                                          "topo_forced": bool(topo_forced), "apply_mask": t_spec, "source": topo.source},
        "brdf": None if brdf is None else {"mode": brdf.mode, "volume": brdf.fit.volume, "geometric": brdf.fit.geometric,
                                          "b/r": brdf.fit.b_r, "h/b": brdf.fit.h_b,
                                          "sza_ref_deg": float(np.degrees(brdf.fit.sza_ref)), "group": brdf.group,
                                          "ratio_max": brdf_ratio_max, "apply_mask": b_spec, "source": brdf.source},
        "input": {"stem": stem, "sensor": ds.attrs.get("sensor"), "level": ds.attrs.get("level")},
        "notes": notes or {},
        **provenance()})
    return out


# --- export ---------------------------------------------------------------------------------------
def export(ds: xr.Dataset, out_dir, wavelengths=None, window=None, suffix: str = "",
           compress: str = "deflate", workers: int = 4, overviews=None,
           overview_resampling: str = "average", format: str = "GTiff") -> Path:
    """Write the (corrected) cube as GeoTIFF or ENVI, + band CSV + provenance JSON.

    ``wavelengths`` selects bands by nearest wavelength (nm); ``window`` is
    ``(y0, y1, x0, x1)`` in pixels. Either makes the output a subset, and
    ``suffix`` should then say so in the file name. The provenance JSON
    records the stages, coefficient sources and any subsetting. ``workers``
    caps the dask threads while computing: every block holds a full-swath,
    all-band slab, so a 14-thread default can exceed memory on 400-band cubes.
    ``overviews`` (``True`` or a list of factors) adds internal pyramids for GIS
    display after the write, see :func:`hyperproc.build_overviews`.
    """
    import dask
    from hyperproc.io import FORMATS, bands_to_csv, default_name, to_raster

    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    sub = ds
    if window is not None:
        y0, y1, x0, x1 = window
        sub = sub.isel(y=slice(y0, y1), x=slice(x0, x1))
    if wavelengths is not None:
        wl_all = np.asarray(sub.wavelength.values, float)
        picked = np.unique([int(np.argmin(np.abs(wl_all - float(w)))) for w in wavelengths])   # no duplicate bands
        sub = sub.isel(wavelength=picked)
    if format not in FORMATS:
        raise ValueError(f"format must be one of {sorted(FORMATS)}; got {format!r}")
    ext = FORMATS[format]
    name = default_name(sub, suffix=suffix, ext=ext)
    extra = dict(compress=compress, overviews=overviews,
                 overview_resampling=overview_resampling) if format == "GTiff" else {}
    with dask.config.set(scheduler="threads", num_workers=max(1, int(workers))):
        path = to_raster(sub, out_dir / name, format=format, **extra)
    bands_to_csv(sub, out_dir / name.replace(ext, "_bands.csv"))
    prov = json.loads(ds.attrs.get("correction_provenance", "{}")) if ds.attrs.get("correction_provenance") else {}
    prov.update({"file": str(path), "format": format, "window": window, "wavelengths": None if wavelengths is None else list(map(float, sub.wavelength.values)),
                 "overviews": (list(overviews) if isinstance(overviews, (list, tuple)) else bool(overviews)),
                 "written": provenance()["created"]})
    (out_dir / name.replace(ext, "_provenance.json")).write_text(json.dumps(prov, indent=1, default=str))
    return path


def footprint_bounds(ds: xr.Dataset):
    """``(x0, y0, x1, y1)`` map bounding box of the cube's pixel footprint,
    rotation included (all four corners, not just two)."""
    from hyperproc.io import _transform_for
    A = _transform_for(ds)
    if A is None:
        raise ValueError("dataset has no georeferencing (attrs['transform'] and x/y coordinates are needed)")
    ny, nx = ds.sizes["y"], ds.sizes["x"]
    cs = [A * (0, 0), A * (nx, 0), A * (0, ny), A * (nx, ny)]
    return (min(c[0] for c in cs), min(c[1] for c in cs), max(c[0] for c in cs), max(c[1] for c in cs))


def footprint_polygon(ds: xr.Dataset):
    """The cube's pixel footprint as a shapely polygon (a rotated rectangle for
    flight-aligned grids). Bounding boxes overstate the overlap of rotated
    swaths - two lines that never touch can still have intersecting boxes."""
    from shapely.geometry import Polygon
    from hyperproc.io import _transform_for
    A = _transform_for(ds)
    if A is None:
        raise ValueError("dataset has no georeferencing (attrs['transform'] and x/y coordinates are needed)")
    ny, nx = ds.sizes["y"], ds.sizes["x"]
    return Polygon([A * (0, 0), A * (nx, 0), A * (nx, ny), A * (0, ny)])


def footprint_overlap(ds_a: xr.Dataset, ds_b: xr.Dataset):
    """Intersection of the two footprint polygons: ``(area, bounds)`` with
    ``bounds = (x0, y0, x1, y1)``, or ``(0.0, None)`` when they do not touch."""
    inter = footprint_polygon(ds_a).intersection(footprint_polygon(ds_b))
    if inter.is_empty or inter.area <= 0:
        return 0.0, None
    return float(inter.area), tuple(inter.bounds)


def _window_for_bbox(ds: xr.Dataset, bbox, max_rows: int | None):
    from hyperproc.io import _transform_for
    inv = ~_transform_for(ds)
    ny, nx = ds.sizes["y"], ds.sizes["x"]
    x0, y0, x1, y1 = bbox
    pts = [inv @ (x, y) for x in (x0, x1) for y in (y0, y1)]
    c0 = int(np.clip(np.floor(min(p[0] for p in pts)), 0, nx)); c1 = int(np.clip(np.ceil(max(p[0] for p in pts)), 0, nx))
    r0 = int(np.clip(np.floor(min(p[1] for p in pts)), 0, ny)); r1 = int(np.clip(np.ceil(max(p[1] for p in pts)), 0, ny))
    if max_rows and r1 - r0 > max_rows:                       # bound the read: the central rows of the overlap
        mid = (r0 + r1) // 2; r0, r1 = max(0, mid - max_rows // 2), min(ny, mid + max_rows // 2)
    return (r0, r1, c0, c1)


def _window_bounds(ds: xr.Dataset, win):
    from hyperproc.io import _transform_for
    A = _transform_for(ds); r0, r1, c0, c1 = win
    cs = [A * (c0, r0), A * (c1, r0), A * (c0, r1), A * (c1, r1)]
    return (min(c[0] for c in cs), min(c[1] for c in cs), max(c[0] for c in cs), max(c[1] for c in cs))


def overlap_windows(ds_a: xr.Dataset, ds_b: xr.Dataset, max_rows: int = 1200):
    """Pixel windows ``(y0, y1, x0, x1)`` in each cube covering one common map
    region inside the overlap of their footprints, with roughly ``max_rows``
    rows in each (a rotated grid needs somewhat more rows to cover an
    axis-aligned region). None when the footprints do not overlap."""
    area, bbox = footprint_overlap(ds_a, ds_b)             # true footprint intersection, not box-vs-box
    if bbox is None or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
        return None
    # Cap a's rows, cut b to a's region, cap b's rows too (rotation can make the
    # same map region span several times more rows in the other grid), then
    # recompute both windows over the region common to the two capped windows.
    wa = _window_for_bbox(ds_a, bbox, max_rows)
    if wa[1] <= wa[0] or wa[3] <= wa[2]:
        return None
    ra = _window_bounds(ds_a, wa)
    bbox2 = (max(bbox[0], ra[0]), max(bbox[1], ra[1]), min(bbox[2], ra[2]), min(bbox[3], ra[3]))
    wb = _window_for_bbox(ds_b, bbox2, max_rows)
    if wb[1] <= wb[0] or wb[3] <= wb[2]:
        return None
    rb = _window_bounds(ds_b, wb)
    bbox3 = (max(bbox2[0], rb[0]), max(bbox2[1], rb[1]), min(bbox2[2], rb[2]), min(bbox2[3], rb[3]))
    if bbox3[0] >= bbox3[2] or bbox3[1] >= bbox3[3]:
        return None
    wa = _window_for_bbox(ds_a, bbox3, None); wb = _window_for_bbox(ds_b, bbox3, None)
    if wa[1] <= wa[0] or wa[3] <= wa[2] or wb[1] <= wb[0] or wb[3] <= wb[2]:
        return None
    return {"a": wa, "b": wb, "bbox": bbox3}


def find_overlapping_pair(dss, exclude_same=None):
    """``(i, j, area)`` of the pair of cubes whose footprint *polygons* overlap
    most, or None. ``exclude_same(ds)`` returns a key; pairs with equal keys
    are skipped (e.g. chunks of one flightline when the question is *between*
    lines)."""
    polys = [footprint_polygon(d) for d in dss]
    best = None
    for i in range(len(dss)):
        for j in range(i + 1, len(dss)):
            if exclude_same is not None and exclude_same(dss[i]) == exclude_same(dss[j]):
                continue
            area = polys[i].intersection(polys[j]).area
            if area > 0 and (best is None or area > best[2]):
                best = (i, j, float(area))
    return best


def _common_grid(srcs, mode="union", res=None):
    """A north-up grid (crs, transform, width, height) over the union or
    intersection of the sources' footprints, at the finest pixel size."""
    import math
    from rasterio.transform import from_origin
    from rasterio.warp import transform_bounds
    crs = srcs[0].crs
    boxes = []
    for s in srcs:
        t = s.transform
        cs = [t * (0, 0), t * (s.width, 0), t * (0, s.height), t * (s.width, s.height)]
        b = (min(c[0] for c in cs), min(c[1] for c in cs), max(c[0] for c in cs), max(c[1] for c in cs))
        if s.crs != crs:
            b = transform_bounds(s.crs, crs, *b)
        boxes.append(b)
    if mode == "union":
        x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes); x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    else:
        x0, y0 = max(b[0] for b in boxes), max(b[1] for b in boxes); x1, y1 = min(b[2] for b in boxes), min(b[3] for b in boxes)
        if x0 >= x1 or y0 >= y1:
            return None
    res = res or min(math.sqrt(abs(s.transform.determinant)) for s in srcs)
    W = int(math.ceil((x1 - x0) / res)); H = int(math.ceil((y1 - y0) / res))
    return crs, from_origin(x0, y1, res, res), W, H


def _reproject(src, crs, transform, W, H, resampling="nearest"):
    """One rasterio dataset's bands on the common grid, NaN where absent."""
    from rasterio.warp import Resampling, reproject
    arr = np.full((src.count, H, W), np.nan, "float32")
    data = src.read().astype("float32")
    if src.nodata is not None and not np.isnan(src.nodata):
        data[data == src.nodata] = np.nan
    reproject(data, arr, src_transform=src.transform, src_crs=src.crs, dst_transform=transform, dst_crs=crs,
              src_nodata=np.nan, dst_nodata=np.nan, resampling=getattr(Resampling, resampling))
    return arr


def mosaic_geotiffs(paths, out_path, method: str = "first", resampling: str = "nearest", res: float | None = None,
                    overviews=None, overview_resampling: str = "average") -> Path:
    """Merge GeoTIFFs into one north-up file.

    Flight-aligned (rotated) grids - every AVIRIS line - are reprojected onto a
    common north-up grid at the finest pixel size first, so lines with
    different rotations can be mosaicked. ``method="first"`` keeps the first
    file's value where they overlap (seams stay visible, which is what a
    seam check wants); ``"mean"`` averages the overlap. ``overviews`` adds
    internal pyramids to the result (see :func:`hyperproc.build_overviews`).
    """
    import rasterio
    from hyperproc.io import build_overviews
    srcs = [rasterio.open(p) for p in paths]
    try:
        crs, transform, W, H = _common_grid(srcs, "union", res)
        count = srcs[0].count
        acc = np.full((count, H, W), np.nan, "float32")
        cnt = np.zeros((count, H, W), "int16") if method == "mean" else None
        for src in srcs:                                        # one at a time to bound memory
            arr = _reproject(src, crs, transform, W, H, resampling)
            fin = np.isfinite(arr)
            if method == "first":
                fill = fin & ~np.isfinite(acc)
                acc[fill] = arr[fill]
            else:
                acc[fin & ~np.isfinite(acc)] = 0.0
                acc[fin] += arr[fin]; cnt[fin] += 1
        if method == "mean":
            acc = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan).astype("float32")
        out_path = Path(out_path)
        meta = dict(driver="GTiff", dtype="float32", count=count, height=H, width=W, crs=crs, transform=transform,
                    nodata=np.nan, compress="deflate", tiled=True, BIGTIFF="IF_SAFER")
        with rasterio.open(out_path, "w", **meta) as dst:
            dst.write(acc)
            for i in range(count):
                dst.set_band_description(i + 1, srcs[0].descriptions[i] or "")
        if overviews:
            build_overviews(out_path, None if overviews is True else overviews, resampling=overview_resampling)
        return out_path
    finally:
        for s in srcs:
            s.close()


def overlap_agreement_tifs(path_a, path_b, resampling: str = "nearest", min_value: float = 0.005) -> dict:
    """Do two GeoTIFFs agree where they overlap? Both are put on a common
    north-up grid over the intersection; per band: median and p90 absolute
    relative difference, median ratio, correlation. The reprojected arrays
    (``a``, ``b``, ``valid``) come back too, for difference maps."""
    import rasterio
    srcs = [rasterio.open(p) for p in (path_a, path_b)]
    try:
        grid = _common_grid(srcs, "intersection")
        if grid is None:
            return {"n": 0, "note": "no overlap"}
        crs, transform, W, H = grid
        a = _reproject(srcs[0], crs, transform, W, H, resampling); b = _reproject(srcs[1], crs, transform, W, H, resampling)
        wl = [float(d.split()[0]) if d else np.nan for d in srcs[0].descriptions]
    finally:
        for s in srcs:
            s.close()
    ok = np.isfinite(a).all(0) & np.isfinite(b).all(0) & (a > min_value).all(0) & (b > min_value).all(0)
    n = int(ok.sum())
    if n < 100:
        return {"n": n, "note": "too few common valid pixels", "a": a, "b": b, "valid": ok}
    A, B = a[:, ok], b[:, ok]
    rel = np.abs(A / B - 1.0)
    return {"n": n, "wavelength": wl, "median_abs_rel_diff": np.median(rel, axis=1).tolist(),
            "p90_abs_rel_diff": np.percentile(rel, 90, axis=1).tolist(), "median_ratio": np.median(A / B, axis=1).tolist(),
            "correlation": [float(np.corrcoef(A[k], B[k])[0, 1]) for k in range(len(wl))],
            "grid": {"crs": str(crs), "transform": tuple(transform)[:6], "width": W, "height": H},
            "a": a, "b": b, "valid": ok}


def seam_check(ds_a: xr.Dataset, ds_b: xr.Dataset, cor_a: xr.Dataset, cor_b: xr.Dataset, out_dir,
               wavelengths=(450, 550, 650, 850, 1650, 2200), max_rows: int = 1200, tag: str = "seam",
               overviews=None) -> dict:
    """Do two adjacent images still mismatch where they overlap after correction?

    Exports the overlap windows of both images at a few wavelengths, raw and
    corrected, mosaics each pair with the first image on top (so the seam is
    where any colour mismatch shows), and measures the agreement in the
    overlap for both. Returns the paths and the two agreement dicts.
    """
    win = overlap_windows(ds_a, ds_b, max_rows)
    if win is None:
        return {"note": "no overlap between the two footprints"}
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    res = {"windows": win}
    for label, (da_, db_) in (("raw", (ds_a, ds_b)), ("corrected", (cor_a, cor_b))):
        pa = export(da_, out, wavelengths=wavelengths, window=win["a"], suffix=f"_{tag}_a", overviews=overviews)
        pb = export(db_, out, wavelengths=wavelengths, window=win["b"], suffix=f"_{tag}_b", overviews=overviews)
        mos = mosaic_geotiffs([pa, pb], out / f"{tag}_{label}_mosaic.tif", method="first", overviews=overviews)
        res[label] = {"a": pa, "b": pb, "mosaic": mos, "agreement": overlap_agreement_tifs(pa, pb)}
    return res


# --- consistency checks -----------------------------------------------------------------------------
def view_dependence(samples, brdf: BRDFCoefficients | None = None, topo=None, wavelengths=(550, 660, 850, 1650, 2200),
                    ndvi_classes=((0.3, 0.5), (0.5, 0.7), (0.7, 0.9)), calc: dict | None = None) -> dict:
    """How much does reflectance still depend on view geometry, per NDVI class?

    Within each NDVI class (a proxy for one cover type) the least-squares
    slope of reflectance on the volume kernel, times the kernel's p05-p95
    span, over the mean reflectance: the view-driven change as a fraction of
    the mean. Reported before and, if ``brdf`` is given, after normalisation.
    A working correction should cut it several-fold. Pixels come from the
    BRDF calc mask - the one the coefficients were fitted with, or ``calc``.
    """
    samples = list(samples)
    topo = list(topo) if topo is not None else [None] * len(samples)
    wl = samples[0].wavelength
    bands = [int(np.argmin(np.abs(wl - w))) for w in wavelengths]
    vol = brdf.fit.volume if brdf is not None else "ross_thick"; geo = brdf.fit.geometric if brdf is not None else "li_dense_r"
    b_r = brdf.fit.b_r if brdf is not None else 1.0; h_b = brdf.fit.h_b if brdf is not None else 2.0
    spec = calc or (brdf.calc_mask if (brdf is not None and brdf.calc_mask) else BRDF_CALC)
    rho_b, rho_a, kv_l, ndvi_l = [], [], [], []
    for s, tc in zip(samples, topo):
        m = s.brdf_calc_mask(spec, vol, geo, b_r, h_b) if brdf is None or brdf.mode == "fit" else np.isfinite(s.ndvi)
        rho = _topo_correct_sample(s, tc, wl)[m][:, bands]
        kv, kg = kernel_pair(s.sza[m], s.vza[m], s.raa[m], vol, geo, b_r, h_b)
        rho_b.append(rho); kv_l.append(kv); ndvi_l.append(s.ndvi[m])
        if brdf is not None:
            f = brdf.fit
            idx = align_wavelengths(f.wavelength, wl[bands], tol=1.0) if f.wavelength is not None else np.array(bands)
            if (np.asarray(idx) < 0).any():
                raise ValueError("BRDF coefficients do not cover the requested wavelengths of these samples")
            sub = B.FlexFit(bins=f.bins, coeffs=f.coeffs[idx], volume=f.volume, geometric=f.geometric, b_r=f.b_r, h_b=f.h_b,
                            sza_ref=f.sza_ref, n_per_bin=f.n_per_bin, r2=f.r2[idx])
            rho_a.append(B.apply_flex(rho, kv, kg, s.ndvi[m], sub))
    rho_b = np.concatenate(rho_b); kv = np.concatenate(kv_l); ndvi = np.concatenate(ndvi_l)
    rho_a = np.concatenate(rho_a) if rho_a else None
    out = {"wavelength": [float(wl[b]) for b in bands], "classes": []}

    def effect(x, y):
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() < 200 or np.std(x[ok]) == 0:
            return np.nan
        a = np.polyfit(x[ok], y[ok], 1)[0]
        return float(a * (np.percentile(x[ok], 95) - np.percentile(x[ok], 5)) / np.mean(y[ok]))
    for lo, hi in ndvi_classes:
        c = (ndvi > lo) & (ndvi <= hi)
        row = {"ndvi": [lo, hi], "n": int(c.sum()),
               "before": [effect(kv[c], rho_b[c, k]) for k in range(len(bands))]}
        if rho_a is not None:
            row["after"] = [effect(kv[c], rho_a[c, k]) for k in range(len(bands))]
        out["classes"].append(row)
    return out


def overlap_agreement(ds_a: xr.Dataset, ds_b: xr.Dataset, wavelengths=(550, 660, 850, 1650, 2200),
                      n_points: int = 20000, n_strips: int = 4, seed: int = 0) -> dict:
    """Do two overlapping north-up cubes on one grid agree where they overlap?

    Samples map coordinates inside the intersection (in a few row strips, to
    keep the chunk reads bounded), takes the nearest pixel from each cube and
    reports the median absolute relative difference and correlation per band.
    Run it on the raw cubes and on the corrected ones: a real BRDF correction
    must bring the two views of the same ground closer together.
    """
    va, vb = _main_var(ds_a), _main_var(ds_b)
    xa, ya = ds_a.x.values, ds_a.y.values; xb, yb = ds_b.x.values, ds_b.y.values
    x0, x1 = max(xa.min(), xb.min()), min(xa.max(), xb.max())
    y0, y1 = max(ya.min(), yb.min()), min(ya.max(), yb.max())
    if x0 >= x1 or y0 >= y1:
        return {"n": 0, "note": "no overlap"}
    rng = np.random.default_rng(seed)
    strips = np.linspace(y0, y1, n_strips + 1)
    ys = np.concatenate([rng.uniform(strips[i], strips[i] + (y1 - y0) / (n_strips * 6), n_points // n_strips) for i in range(n_strips)])
    xs = rng.uniform(x0, x1, ys.size)
    px = xr.DataArray(xs, dims="pt"); py = xr.DataArray(ys, dims="pt")
    wls = list(wavelengths)
    a = ds_a[va].sel(wavelength=wls, method="nearest").sel(x=px, y=py, method="nearest").values
    b = ds_b[vb].sel(wavelength=wls, method="nearest").sel(x=px, y=py, method="nearest").values
    ok = np.isfinite(a).all(axis=1) & np.isfinite(b).all(axis=1) & (a > 0.005).all(axis=1) & (b > 0.005).all(axis=1)
    if ok.sum() < 100:
        return {"n": int(ok.sum()), "note": "too few common valid pixels"}
    a, b = a[ok], b[ok]
    rel = np.abs(a / b - 1.0)
    return {"n": int(ok.sum()), "wavelength": [float(w) for w in ds_a.wavelength.sel(wavelength=wls, method="nearest").values],
            "median_abs_rel_diff": np.median(rel, axis=0).tolist(),
            "p90_abs_rel_diff": np.percentile(rel, 90, axis=0).tolist(),
            "median_ratio": np.median(a / b, axis=0).tolist(),
            "correlation": [float(np.corrcoef(a[:, k], b[:, k])[0, 1]) for k in range(len(wls))],
            "bounds": [float(x0), float(y0), float(x1), float(y1)]}
