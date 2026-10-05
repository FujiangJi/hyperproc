# hyperproc.atmos.inputs.write_envi_header

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def write_envi_header(path: Path, lines: int, samples: int, bands: int, dtype: str, description: str='', band_names=None, wavelength=None, fwhm=None, extra: dict | None=None) -> Path
```

Write ``path`` (the ``.hdr``) for a BIL cube, little-endian.

[Module and aliases](../hyperproc-atmos-inputs.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.inputs.write_envi_header --runtime`.
