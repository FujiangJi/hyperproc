# hyperproc.align.tie_points

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def tie_points(moving: xr.Dataset, reference: xr.Dataset, wavelength: float=DEFAULT_WAVELENGTH, tiles: int=4, min_snr: float=3.0, min_finite: float=0.25, var: str | None=None, ref_var: str | None=None) -> dict
```

Match a grid of tiles independently, to see whether one shift describes the scene.

Args:
    moving: the dataset to be aligned.
    reference: the dataset defining the grid and the truth.
    wavelength: band used for matching, nm.
    tiles: the scene is split ``tiles`` x ``tiles``.
    min_snr: tiles whose correlation peak is weaker than this are dropped.
    min_finite: tiles with less than this fraction of valid pixels are dropped.
    var, ref_var: variable names; the main cube of each by default.

Returns:
    dict with per-tile ``dy``, ``dx``, ``snr``, their ``centre`` in pixels,
    and how many tiles were kept.

[Module and aliases](../hyperproc-align.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.align.tie_points --runtime`.
