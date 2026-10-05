# hyperproc.open

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def open(path: str | Path, sensor: str | None=None, level: str | None=None, **kwargs) -> xr.Dataset
```

Open a hyperspectral granule with the right reader for its sensor.

Args:
    path: the granule to read. For sensors that split a scene across
        several files (EMIT, PACE), pass the main reflectance/radiance
        file; siblings are located automatically.
    sensor: ``"EMIT"``, ``"PRISMA"``, ``"ENMAP"``, ``"DESIS"``, ``"PACE"``,
        ``"AVIRIS"``, ``"NEON"``. Guessed from the filename if omitted.
    level: ``"L1B"``, ``"L2A"``, ``"L2D"``, ... Guessed if omitted.
    **kwargs: passed through to the sensor's reader. EMIT accepts
        ``ortho``, ``wl_range``, ``good_bands_only``, ``masks``, ``geometry``.

Returns:
    ``xarray.Dataset``. See :func:`describe` for a quick look.

Raises:
    ValueError: the sensor/level is unknown, or the filename could not be
        identified and nothing was passed explicitly.
    NotImplementedError: the sensor/level is registered but its reader is
        not written yet. The message says what to write.

Examples:
    >>> ds = hyperproc.open("EMIT_L2A_RFL_001_20230422T195924_2311213_002.nc")
    >>> ds = hyperproc.open(p, sensor="EMIT", level="L2A", wl_range=(400, 900))

[Module and aliases](../hyperproc.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.open --runtime`.
