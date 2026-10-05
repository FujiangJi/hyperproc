# hyperproc.correct.cfactor.nbar

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def nbar(ds: xr.Dataset, params=None, *, var: str | None=None, sza_ref=45.0, vza_ref: float=0.0, raa_ref: float=0.0, spectral: str='nearest', volume: str='ross_thick', geometric: str='li_sparse_r', b_r: float=1.0, h_b: float=2.0, clip=DEFAULT_CLIP, fill: str='none', qa_max: int | None=3, mask_snow: bool=True, keep_c: bool=True, source: str='gee', cache_dir=None, date: str | None=None, days: int=8, res: float | None=None, pad: float=0.05, project: str | None=None, sampling: str='bilinear', verbose: bool=True) -> xr.Dataset
```

Normalise a satellite reflectance cube to a common Sun/view geometry.

Args:
    ds: a hyperproc dataset with a reflectance cube and per-pixel ``sza``,
        ``vza`` and ``raa`` (or ``vaa``/``saa``) layers, on either a map
        grid or a swath grid with ``lon``/``lat``. The L2A product of any
        of the readers qualifies, and so does the output of
        :func:`hyperproc.atmos.correct`.
    params: MCD43A1 parameters as a :class:`~hyperproc.correct.mcd43.Params`
        or a path to a stack. Downloaded for the scene when omitted.
    var: the variable to correct; the main cube by default.
    sza_ref, vza_ref, raa_ref: target geometry (see the module docstring).
    spectral: ``"nearest"`` (default, each band takes the closest MODIS
        band's c-factor) or ``"interp"`` (linear in wavelength between the
        seven, smoother but not a measured shape).
    volume, geometric, b_r, h_b: kernel choice; leave at the MODIS pair.
    clip: bounds on the c-factor, or None.
    fill: what to do where MODIS has no retrieval. ``"none"`` leaves the
        reflectance untouched (c = 1) and flags the pixel, ``"median"``
        uses the scene median c, ``"nearest"`` copies the nearest valid c.
    qa_max: keep MODIS cells whose band quality is <= this. The default 3
        keeps every retrieval; a magnitude inversion scales all three
        weights together and that factor cancels in the ratio. Pass 1 for
        full inversions only, at the cost of holes in the correction.
    mask_snow: drop cells the MODIS product flags as snow-covered.
    keep_c: attach the seven c-factors as a ``c_factor`` variable.
    source, cache_dir, date, days, pad, res, project: passed to
        :func:`hyperproc.correct.mcd43.fetch` when ``params`` is None.
        ``res=None`` lets the MODIS grid adapt to this image's own pixel
        size (see :func:`hyperproc.correct.mcd43.step_for`).
    sampling: ``"bilinear"`` or ``"nearest"`` sampling of the MODIS grid.

Returns:
    A copy of ``ds`` with the cube replaced by the normalised one (lazy,
    so nothing is computed until it is written), a ``brdf_valid`` flag
    layer, optional ``c_factor``, and ``brdf_*`` attributes recording what
    was done. ``attrs["stem"]`` gains a ``_brdf`` suffix.

Raises:
    ValueError: the dataset has no geometry, or an argument is out of range.

[Module and aliases](../hyperproc-correct-cfactor.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.cfactor.nbar --runtime`.
