"""Per-pixel geometry checks shared by the airborne readers.

Topographic and BRDF correction both lean on ``slope``, ``aspect`` and
``cos_i``, and at least one product family (AVIRIS-3) ships them in a
convention nothing downstream expects. Rather than hard-code which instrument
is affected, these helpers *measure* it against the granule's own DEM. They
live here, not in a sensor module, so that AVIRIS and NEON - and whatever comes
next - test the same way and neither imports the other.
"""

from __future__ import annotations

import numpy as np
import xarray as xr


def check_geometry(ds: xr.Dataset, window: int = 256) -> dict:
    """Test whether ``slope`` is measured from horizontal, as everything expects.

    AVIRIS-3 stores it from *vertical* and computes ``cos_i`` from that value,
    which leaves both unusable for topographic correction. Rather than hard-code
    which instrument is affected, this measures it:

    1. **Median slope.** Over a whole flightline real terrain sits well under
       45 deg. AVIRIS-3 reads 76-78 with a 99th percentile of 89.5, piled
       against 90; Classic, NG and AVIRIS-5 read 1.5, 13.1 and 10.1.
    2. **DEM correlation**, when an elevation layer is present - the decisive
       test. Differentiating the DEM gives true slope, and whichever of
       ``stored`` or ``90 - stored`` correlates with it is the convention in
       use. On AVIRIS-3 that is +0.906 for the complement against -0.906 for
       the stored value.

    Reads one ``window`` x ``window`` block from the middle of the swath, so it
    costs a couple of seconds rather than a pass over the cube.

    Returns:
        A dict with ``needs_fix``, ``convention``, ``evidence``, the median
        slopes, and the two correlations when a DEM was available.
    """
    out = {"sensor": ds.attrs.get("sensor", "?"), "checked": False,
           "needs_fix": False, "convention": "unknown",
           "evidence": "no slope layer"}
    if "slope" not in ds:
        return out
    ny, nx = ds.sizes["y"], ds.sizes["x"]
    w = min(window, ny, nx)
    # Try the centre first, then a quarter and three quarters of the way along
    # the strip: a flight line's centre window can lie in the void of a
    # rotated grid, and an unchecked product must not pass as checked.
    sl, sel = None, None
    for fy in (0.5, 0.25, 0.75):
        cand = dict(y=slice(int((ny - w) * fy), int((ny - w) * fy) + w),
                    x=slice((nx - w) // 2, (nx - w) // 2 + w))
        arr = np.asarray(ds["slope"].isel(**cand).values, dtype="float64")
        if np.isfinite(arr).sum() > 100:
            sl, sel = arr, cand
            break
    if sl is None:
        out["evidence"] = "slope layer empty over the sampled windows; convention not checked"
        return out
    med = float(np.nanmedian(sl))
    out.update(checked=True, median_slope=round(med, 2))
    suspect = med > 45.0
    out["evidence"] = f"median slope {med:.1f} deg (no DEM to check against)"

    if "elev" in ds and "transform" in ds.attrs:
        z = np.asarray(ds["elev"].isel(**sel).values, dtype="float64")
        gt = ds.attrs["transform"]
        px = float(np.hypot(gt[1], gt[4]))        # true pixel size under rotation
        if np.isfinite(z).sum() > 100 and px > 0:
            dzdy, dzdx = np.gradient(z, px, px)
            dem = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
            m = np.isfinite(dem) & np.isfinite(sl)
            if m.sum() > 100 and np.nanstd(dem[m]) > 1e-6:
                r_stored = float(np.corrcoef(dem[m], sl[m])[0, 1])
                r_compl = float(np.corrcoef(dem[m], (90.0 - sl)[m])[0, 1])
                out.update(dem_median_slope=round(float(np.nanmedian(dem)), 2),
                           r_stored=round(r_stored, 3),
                           r_complement=round(r_compl, 3))
                # Decide on the correlation only when the two hypotheses are
                # clearly separated; on low-relief windows both are weak and
                # the sign alone could flip a correct product. Otherwise the
                # median test above stands.
                if abs(r_compl - r_stored) > 0.2:
                    suspect = r_compl > r_stored
                    how = "correlation"
                else:
                    how = f"correlations too close (|dr|={abs(r_compl - r_stored):.2f}); median test"
                out["evidence"] = (
                    f"DEM slope {np.nanmedian(dem):.1f} deg vs stored {med:.1f}; "
                    f"r(stored)={r_stored:+.3f}, r(90-stored)={r_compl:+.3f}; decided by {how}")
    out["needs_fix"] = bool(suspect)
    out["convention"] = "vertical" if suspect else "horizontal"
    return out


def fix_slope_convention(ds: xr.Dataset) -> xr.Dataset:
    """Flip ``slope`` to be measured from horizontal, and rebuild ``cos_i``.

    Applied when :func:`check_geometry` says a product stores slope from
    vertical - AVIRIS-3, on everything seen so far. The shipped ``cos_i`` is
    reproduced exactly (r = 1.000) by feeding that complement into the standard
    incidence formula, so it inherits the error: one AVIRIS-3 line here has a
    median ``cos_i`` of -0.216, meaning most of the scene faces away from the
    sun, when 14 deg terrain under a 45.6 deg sun confines it to 0.51-0.85.
    SCS+C and C-correction both divide by that.

    Modifies ``ds`` in place and returns it.
    """
    if "slope" not in ds:
        return ds
    ds["slope"] = 90.0 - ds["slope"]
    ds["slope"].attrs.update(
        units="degrees", long_name="terrain slope from horizontal",
        note="rebuilt as 90 - the stored value, which is measured from vertical")
    if all(v in ds for v in ("aspect", "sza", "saa")):
        sl, sz = np.radians(ds["slope"]), np.radians(ds["sza"])
        rel = np.radians(ds["saa"] - ds["aspect"])
        ds["cos_i"] = (np.cos(sl) * np.cos(sz)
                       + np.sin(sl) * np.sin(sz) * np.cos(rel)).astype("float32")
        ds["cos_i"].attrs.update(
            units="1", long_name="cosine of the solar incidence angle on the slope",
            note="recomputed from the corrected slope; the shipped band used "
                 "the from-vertical value and is not usable")
        ds.attrs["geometry_fixed"] = "slope = 90 - stored; cos_i recomputed"
    else:
        ds.attrs["geometry_fixed"] = "slope = 90 - stored"
    return ds
