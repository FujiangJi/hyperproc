# hyperproc.atmos.correct.correct

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def correct(ds: xr.Dataset, work_dir: str | Path, engine: str='sRTMnet', workers: int=24, atmosphere: str='auto', aerosol_model: str='continental', segmentation_size: int=40, line: str='analytical', presolve: bool=True, surface=None, window=None, overwrite: bool=False, redo: str | None=None, dry_run: bool=False, timeout: float | None=None, verbose: bool=True, **kwargs) -> xr.Dataset | dict
```

Atmospherically correct an L1B radiance dataset with ISOFIT.

Writes the inputs under ``work_dir/input``, runs ``apply_oe`` (see
:func:`build_command` for every parameter), and returns the products
through :func:`read_outputs` with ``ds`` as the template.

``work_dir`` is resumable the way ISOFIT is: an existing look-up table,
presolve or reflectance file is reused, so a second call on the same
directory returns in seconds. ``overwrite=True`` clears ISOFIT's
``config``, ``lut_*`` and ``output`` directories first (the inputs are
rewritten only when their size no longer matches).

``redo="line"`` keeps the look-up tables and the superpixel retrieval and
redoes only the analytical line, which is what a change of
``num_neighbors`` needs; ``redo="all"`` is the same as ``overwrite``.

``dry_run=True`` writes the inputs and returns ``{"inputs", "command"}``
without launching ISOFIT.

[Module and aliases](../hyperproc-atmos-correct.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.correct.correct --runtime`.
