# hyperproc.atmos.inputs._write_cube

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _write_cube(da: xr.DataArray, path: Path, factor: float, verbose: bool, band_scale: np.ndarray | None=None, pixel_scale: np.ndarray | None=None) -> None
```

Stream ``da (y, x, wavelength)`` to ``path`` as BIL float32, NaN -> FILL.

``band_scale (wavelength,)`` and ``pixel_scale (y, x)`` multiply in as
well; they turn a TOA reflectance into radiance without a second pass.

[Module and aliases](../hyperproc-atmos-inputs.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.inputs._write_cube --runtime`.
