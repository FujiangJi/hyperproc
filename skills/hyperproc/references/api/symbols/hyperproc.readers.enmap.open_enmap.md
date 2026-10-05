# hyperproc.readers.enmap.open_enmap

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def open_enmap(path: str | Path, cube: str | None=None, wl_range: tuple[float, float] | None=None, quality: bool=True, pixelmask: bool=False, angles: bool=True, apply_scale: bool=True) -> xr.Dataset
```

Open an EnMAP granule.

Args:
    path: the ``*-SPECTRAL_IMAGE.TIF``, or for L1B one of
        ``*-SPECTRAL_IMAGE_VNIR.TIF`` / ``*_SWIR.TIF``. DLR's cloud-optimised
        copies, ``*_COG.TIF``, are read the same way and find their
        ``_COG`` siblings.
    cube: L1B only. ``"vnir"`` (91 bands, 418-993 nm) or ``"swir"`` (133
        bands, 902-2445 nm); the default follows the file you passed.
        ``"full"`` raises on L1B - the detectors are not co-registered until
        L1C, so a merged L1B cube would mix ground locations band to band.
        L1C and L2A always ship one merged cube and ignore this.
    wl_range: ``(min_nm, max_nm)`` band subset.
    quality: attach the single-band quality rasters - ``cloud``,
        ``cloudshadow``, ``cirrus``, ``haze``, ``snow``, ``classes``,
        ``testflags``.
    pixelmask: attach the per-band pixel mask as ``pixelmask``
        ``(y, x, wavelength)``, lazy and band-aligned with the cube (same
        detector, order and ``wl_range``).
        Adds a uint8 array the size of the cube.
    angles: interpolate the corner angles into per-pixel ``sza``, ``saa``,
        ``vza``, ``vaa`` grids.
    apply_scale: apply the per-band gain and offset. ``False`` gives raw DN.

Returns:
    Dataset with ``radiance`` or ``reflectance`` on ``(y, x, wavelength)``.

[Module and aliases](../hyperproc-readers-enmap.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.enmap.open_enmap --runtime`.
