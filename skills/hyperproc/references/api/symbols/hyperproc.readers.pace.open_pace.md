# hyperproc.readers.pace.open_pace

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def open_pace(path: str | Path, wl_range: tuple[float, float] | None=None, flags: bool=True, geometry: bool=True, latlon: bool=True) -> xr.Dataset
```

Open a PACE OCI granule.

Args:
    path: ``PACE_OCI.*.L2.SFREFL.*.nc`` or ``PACE_OCI.*.L1B.*.nc``.
    wl_range: ``(min_nm, max_nm)`` band subset. L2 covers 346-2258 nm in
        122 bands; L1B covers 315-2258 nm in 291.
    flags: decode ``l2_flags`` into named boolean masks (L2 only).
    geometry: attach angles. L2 always gets its own ``csol_z`` (per-scan-line
        centre solar zenith) and ``tilt``; full per-pixel ``sza``, ``saa``,
        ``vza``, ``vaa`` need the L1B sibling and are used when it is found.
        Azimuths
        are converted from OCI's -180..180 convention to 0..360 so they
        match every other reader here. Present
        in L1B; for L2 the matching L1B granule is used if it sits alongside.
    latlon: attach the ``lat``/``lon`` arrays. These are the only
        georeferencing a PACE granule has, so they are needed for
        :func:`hyperproc.georeference`.

Returns:
    Dataset with ``reflectance`` on ``(y, x, wavelength)``. No CRS - both
    levels are swaths.

[Module and aliases](../hyperproc-readers-pace.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.pace.open_pace --runtime`.
