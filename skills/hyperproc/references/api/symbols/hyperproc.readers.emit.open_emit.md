# hyperproc.readers.emit.open_emit

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def open_emit(path: str | Path, ortho: bool=True, wl_range: tuple[float, float] | None=None, good_bands_only: bool=False, masks: bool=True, geometry: bool=True) -> xr.Dataset
```

Open an EMIT L2A reflectance or L1B radiance granule.

Args:
    path: ``EMIT_L2A_RFL_*.nc`` or ``EMIT_L1B_RAD_*.nc``.
    ortho: orthorectify onto the map grid using the granule's GLT.
        False keeps the raw ``(downtrack, crosstrack)`` sensor grid.
    wl_range: ``(min_nm, max_nm)`` band subset, applied *before*
        orthorectification so the full ~5 GB ortho cube is never built.
    good_bands_only: set the bands EMIT flags as unusable to NaN (the
        1320-1440 and 1770-1960 nm water-vapour windows). The band count is
        unchanged - all 285 stay, 41 of them blanked - so band indices keep
        lining up with the sensor's native grid. EMIT stores a constant
        -0.01 sentinel in those bands, which otherwise reads as real data.
        L2A only; L1B granules carry no ``good_wavelengths`` flag.
    masks: fold in the ``L2A_MASK`` sibling if it sits alongside ``path``.
    geometry: fold in the ``L1B_OBS`` sibling if it sits alongside ``path``.

Returns:
    Dataset with ``reflectance`` or ``radiance`` on ``(y, x, wavelength)``,
    ``wavelength``/``fwhm`` coordinates in nm, plus mask and geometry
    variables where the siblings exist.

Raises:
    ValueError: not an EMIT granule, or a product this reader does not
        handle (MASK / OBS / RFLUNCERT are read as siblings, not directly).

[Module and aliases](../hyperproc-readers-emit.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.emit.open_emit --runtime`.
