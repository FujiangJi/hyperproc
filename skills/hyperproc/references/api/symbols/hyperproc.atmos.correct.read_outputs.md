# hyperproc.atmos.correct.read_outputs

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def read_outputs(source: Inputs | str | Path, template: xr.Dataset | None=None, uncertainty: bool=True) -> xr.Dataset
```

The ISOFIT products as a hyperproc dataset.

Args:
    source: the :class:`Inputs` of the run, or its work directory.
    template: the L1B dataset the inputs were written from (already cut
        to the same window). Its coordinates, 2-D layers and attributes
        are carried over so the result is a drop-in for the correction
        and export steps. Without it the result has bare indices.
    uncertainty: also attach the posterior reflectance uncertainty cube.

Returns:
    ``reflectance (y, x, wavelength)`` lazy float32, plus ``aot550`` and
    ``h2o`` (per pixel, from ``_atm_interp`` on the analytical/empirical
    routes or from ``_state`` on the per-pixel route), ``segment`` where a
    superpixel label image exists, and ``uncertainty`` when asked.

[Module and aliases](../hyperproc-atmos-correct.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.correct.read_outputs --runtime`.
