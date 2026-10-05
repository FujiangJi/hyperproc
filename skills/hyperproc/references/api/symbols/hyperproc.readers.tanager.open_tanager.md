# hyperproc.readers.tanager.open_tanager

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def open_tanager(path: str | Path, wl_range: tuple[float, float] | None=None, good_bands_only: bool=False, masks: bool=True, geometry: bool=True, extras: bool=True, uncertainty: bool=False) -> xr.Dataset
```

Open a Tanager-1 orthorectified granule.

Args:
    path: ``*_ortho_sr_hdf5.h5`` or ``*_ortho_radiance_hdf5.h5``.
    wl_range: ``(min_nm, max_nm)`` band subset. The sensor covers
        376-2499 nm in 426 bands.
    good_bands_only: set the bands Planet flags unusable to NaN, keeping
        all 426 so band indices stay aligned with the sensor's own grid.
        Roughly 76% of those values are exactly -0.01 and the rest are
        failed retrievals; all of them pass ``isfinite`` and read as real
        data otherwise. **SR only** - the radiance
        product ships no ``good_wavelengths`` attribute.
    masks: attach ``cloud``, ``cirrus`` and ``nodata``.
    geometry: attach per-pixel ``sza``, ``saa``, ``vza``, ``vaa``,
        ``path_length``, plus a derived ``raa``.
    extras: SR only - attach ``aot`` and ``wv_cm``.
    uncertainty: SR only - attach ``reflectance_uncertainty``. Doubles the
        memory, so off by default.

Returns:
    Dataset with ``reflectance`` or ``radiance`` on ``(y, x, wavelength)``,
    already projected: ``crs`` and ``transform`` come straight from the file.

[Module and aliases](../hyperproc-readers-tanager.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.tanager.open_tanager --runtime`.
