# hyperproc.geometry.check_geometry

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def check_geometry(ds: xr.Dataset, window: int=256) -> dict
```

Test whether ``slope`` is measured from horizontal, as everything expects.

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

[Module and aliases](../hyperproc-geometry.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.geometry.check_geometry --runtime`.
