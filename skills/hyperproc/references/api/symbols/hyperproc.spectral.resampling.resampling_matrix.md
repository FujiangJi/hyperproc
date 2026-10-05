# hyperproc.spectral.resampling.resampling_matrix

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def resampling_matrix(source_wl, target_wl, source_fwhm=None, target_fwhm=None, method: str='gaussian', response=None, response_wl=None, usable=None, min_coverage: float=0.5, allow_sharpening: bool=False) -> tuple
```

The weights that turn source bands into target bands.

Args:
    source_wl, target_wl: band centres, nm.
    source_fwhm, target_fwhm: band widths, nm. Inferred from the spacing by
        :func:`build_fwhm` when omitted, which is a guess, not a fact.
    method: one of :data:`METHODS`.
    response, response_wl: for ``method="response"``, the measured response
        ``(n_target, n_fine)`` on the grid ``response_wl``.
    usable: boolean mask of source bands to use. Unusable bands get zero
        weight and are excluded from the coverage.
    min_coverage: target bands covered less than this become NaN.
    allow_sharpening: permit a target narrower than the source.

Returns:
    ``(matrix, coverage)``: ``(n_target, n_source)`` weights whose rows sum
    to 1, and the coverage fraction per target band. Rows below
    ``min_coverage`` are all NaN.

Raises:
    ValueError: an unknown method, or a target finer than the source while
        ``allow_sharpening`` is False.

[Module and aliases](../hyperproc-spectral-resampling.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral.resampling.resampling_matrix --runtime`.
