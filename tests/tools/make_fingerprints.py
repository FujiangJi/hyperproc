"""Generate tests/fingerprints.json: one compact signature per reader case.

Run this only when a change to a reader is *intended*, then read the diff
before committing it:

    python tests/tools/make_fingerprints.py
    git diff tests/fingerprints.json

A fingerprint regenerated without reading the diff is worse than no test at
all, because it looks like coverage while asserting whatever the code now does.
"""
import hashlib, json, sys, time, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
import numpy as np, hyperproc as hp

# tests/tools/make_fingerprints.py -> parents[2] is the repository root, so this
# works from a clone anywhere rather than only on the machine it was written on.
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tests" / "data"

CASES = [
    ("EMIT",           "L1B",  "EMIT/EMIT_L1B_RAD_*.nc", {}),
    ("EMIT",           "L1B",  "EMIT/EMIT_L1B_RAD_*.nc", {"ortho": False}),
    ("EMIT",           "L2A",  "EMIT/EMIT_L2A_RFL_*.nc", {}),
    ("AVIRIS3",        "L1B",  "AVIRIS3/extracted/AV320231005t181518_L1B_RDN_*_RDN_ORT", {}),
    ("AVIRIS3",        "L2A",  "AVIRIS3/extracted/AV320231005t181518_L2A_OE_*_RFL_ORT", {}),
    ("AVIRIS5",        "L1B",  "AVIRIS5/AV520250508t173511_000_L1B_RDN_*_RDN.nc", {}),
    ("AVIRIS5",        "L2A",  "AVIRIS5/AV520250508t173511_000_L2A_OE_*_RFL_ORT.nc", {}),
    ("AVIRIS-NG",      "L1B",  "AVIRIS_NG/ang20220224t210144_rdn_v2aa1", {}),
    ("AVIRIS-NG",      "L2A",  "AVIRIS_NG/ang20220224t210144_rfl_v2aa1", {}),
    ("AVIRIS-CLASSIC", "L1B",  "AVIRIS_Classic/f201013t01p00r10rdn_e", {}),
    ("AVIRIS-CLASSIC", "L2A",  "AVIRIS_Classic/f201013t01p00r10_rfl_v1l1", {}),
    ("DESIS",          "L1B",  "DESIS/DESIS-HSI-L1B-*-SPECTRAL_IMAGE.tif", {}),
    ("DESIS",          "L1C",  "DESIS/DESIS-HSI-L1C-*-SPECTRAL_IMAGE.tif", {}),
    ("DESIS",          "L2A",  "DESIS/DESIS-HSI-L2A-*-SPECTRAL_IMAGE.tif", {}),
    ("ENMAP",          "L1C",  "EnMAP/ENMAP01-____L1C-*-SPECTRAL_IMAGE.TIF", {}),
    ("ENMAP",          "L2A",  "EnMAP/ENMAP01-____L2A-*-SPECTRAL_IMAGE.TIF", {}),
    ("NEON",           "L1",   "NEON_AOP/NEON_D01_BART_DP1_20190825_144302_reflectance.h5", {}),
    ("PACE",           "L1B",  "PACE/PACE_OCI.20260422T195047.L1B.V3.nc", {}),
    ("PACE",           "L2",   "PACE/PACE_OCI.20260422T195047.L2.SFREFL.V3_1.nc", {}),
    ("PRISMA",         "L1",   "PRISMA/PRS_L1_STD_OFFL_*.he5", {}),
    ("PRISMA",         "L2C",  "PRISMA/PRS_L2C_STD_*.he5", {}),
    ("PRISMA",         "L2D",  "PRISMA/PRS_L2D_STD_*.he5", {}),
    ("TANAGER",        "L1B",  "Tanager/*_ortho_radiance_hdf5.h5", {}),
    ("TANAGER",        "L2A",  "Tanager/*_ortho_sr_hdf5.h5", {}),
]

GEOM = ("sza", "saa", "vza", "vaa", "raa", "elev", "cos_i", "slope", "aspect")


def digest(a):
    return hashlib.md5(np.ascontiguousarray(np.round(np.asarray(a, "float64"), 6))).hexdigest()[:16]


def rng(a, cap=1_000_000):
    """Range over a strided sample: exact enough, and a full flightline is 28 M values."""
    a = np.asarray(a)
    if a.size > cap:
        step = int(np.ceil(np.sqrt(a.size / cap))) if a.ndim == 2 else int(np.ceil(a.size / cap))
        a = a[::step, ::step] if a.ndim == 2 else a[::step]
    a = np.asarray(a, dtype="float64")
    f = a[np.isfinite(a)]
    return [round(float(f.min()), 4), round(float(f.max()), 4)] if f.size else None


def pick_window(ds, var, size=10):
    """A 10x10 window that actually holds data, found cheaply.

    An orthorectified flightline is a diagonal band inside a north-up box: the
    AVIRIS Classic line here is 46 % valid on every row, but the valid columns
    move with the row, so the image centre is empty and a fingerprint taken
    there is a checksum of NaN, which catches nothing.

    A strided read of a whole band would find the data but is far too
    expensive - on EMIT it forces the geographic look-up table across the
    entire scene. So probe an 8x8 lattice of small windows instead: 64 reads of
    100 values each, which is enough to land on a band covering 46 % of every
    row, and costs nothing on any reader.
    """
    ny, nx = ds.sizes["y"], ds.sizes["x"]
    band = ds[var].isel(wavelength=ds.sizes["wavelength"] // 2)
    fracs = [(i + 0.5) / 8.0 for i in range(8)]
    best, best_frac = None, -1.0
    # nearest the centre first, so a well-behaved image keeps a central window
    order = sorted(((fy, fx) for fy in fracs for fx in fracs),
                   key=lambda f: (f[0] - 0.5) ** 2 + (f[1] - 0.5) ** 2)
    for fy, fx in order:
        y0 = int(min(max(0, ny * fy - size // 2), ny - size))
        x0 = int(min(max(0, nx * fx - size // 2), nx - size))
        finite = float(np.isfinite(
            band.isel(y=slice(y0, y0 + size), x=slice(x0, x0 + size)).values).mean())
        if finite >= 0.99:
            return y0, x0
        if finite > best_frac:
            best, best_frac = (y0, x0), finite
    return best if best is not None else (max(0, ny // 2 - size // 2), max(0, nx // 2 - size // 2))


def fingerprint(ds, var):
    y0, x0 = pick_window(ds, var)
    win = ds[var].isel(y=slice(y0, y0 + 10), x=slice(x0, x0 + 10)).values
    wl = np.asarray(ds[var]["wavelength"].values, "float64")
    out = {
        "sizes": {k: int(v) for k, v in sorted(ds.sizes.items())},
        "main_var": var,
        "data_vars": sorted(map(str, ds.data_vars)),
        "coords": sorted(map(str, ds.coords)),
        "wavelength": {"n": int(wl.size), "min": round(float(wl.min()), 3),
                       "max": round(float(wl.max()), 3), "digest": digest(wl)},
        "window": {"origin": [y0, x0], "digest": digest(np.nan_to_num(win, nan=-9999.0)),
                   "finite": round(float(np.isfinite(win).mean()), 4),
                   "range": rng(win)},
        "attrs": {k: str(ds.attrs.get(k, "")) for k in ("sensor", "level", "units", "product")},
        "crs": str(ds.attrs.get("crs", "")),
        "geometry": {g: rng(ds[g].values) for g in GEOM if g in ds},
    }
    if "fwhm" in ds.coords:
        out["fwhm"] = rng(ds["fwhm"].values)
    if "good_wavelength" in ds.coords:
        out["good_bands"] = int(np.asarray(ds["good_wavelength"].values, bool).sum())
    return out


def main():
    out, timings = {}, {}
    for sensor, level, pattern, kw in CASES:
        hits = sorted(DATA.glob(pattern))
        key = f"{sensor}/{level}" + ("/sensor-grid" if kw.get("ortho") is False else "")
        if not hits:
            print(f"{key:28s} (no granule)"); continue
        t0 = time.time()
        try:
            ds = hp.open(hits[0], **kw)
            fp = fingerprint(ds, hp.main_var(ds))
            fp["file"] = hits[0].name
            out[key] = fp
            timings[key] = round(time.time() - t0, 2)
            print(f"{key:28s} {str(fp['sizes']):46s} {timings[key]:6.2f} s")
        except Exception as e:
            print(f"{key:28s} FAILED {type(e).__name__}: {str(e)[:60]}")
    path = ROOT / "tests" / "fingerprints.json"
    path.write_text(json.dumps(out, indent=1, sort_keys=True))
    print(f"\nwrote {path} ({path.stat().st_size/1024:.0f} KB, {len(out)} cases)")
    print(f"total open+fingerprint time: {sum(timings.values()):.1f} s")


if __name__ == "__main__":
    main()
