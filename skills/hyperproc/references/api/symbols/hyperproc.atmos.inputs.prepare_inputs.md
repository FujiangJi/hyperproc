# hyperproc.atmos.inputs.prepare_inputs

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def prepare_inputs(ds: xr.Dataset, work_dir: str | Path, window=None, overwrite: bool=False, verbose: bool=True, dem: bool=True) -> Inputs
```

Write the ``_rdn``, ``_loc`` and ``_obs`` files for ``ds`` under ``work_dir/input``.

Args:
    ds: a hyperproc **L1B radiance** dataset (any sensor in :data:`SENSORS`).
        Reflectance products are refused.
    work_dir: the ISOFIT working directory; ``input/`` is created inside it.
    window: optional subset, ``{"y": (y0, y1), "x": (x0, x1)}`` or
        ``((y0, y1), (x0, x1))``, for validation runs on a piece of a scene.
    overwrite: rewrite files that already exist with the right shape.
    dem: when the dataset has no ``elev`` layer, sample one from the
        Copernicus DEM (:func:`hyperproc.atmos.dem.add_elevation`).

Returns:
    :class:`Inputs` with every path, the ISOFIT sensor code and file id,
    and summary statistics of the geometry. Also saved as
    ``input/inputs.json`` so a later step can pick the run up.

[Module and aliases](../hyperproc-atmos-inputs.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.inputs.prepare_inputs --runtime`.
