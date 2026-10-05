# hyperproc.spectral.srf.fetch

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def fetch(sensor: str, cache: Path | None=None, overwrite: bool=False, verbose: bool=True) -> dict
```

The response functions of ``sensor``, downloading and caching on first use.

Args:
    sensor: an instrument name or alias; see :func:`available`.
    cache: where to keep the files; ``$HYPERPROC_CACHE_DIR/srf`` by default.
    overwrite: re-download even when the cache has it.
    verbose: say what is being fetched.

Returns:
    dict with ``wavelength`` and ``fwhm`` per band, ``bands`` (names),
    ``label``, ``kind`` (``"measured"`` or ``"nominal"``) and, for a
    measured instrument, ``response`` ``(n_band, n_fine)`` on ``response_wl``.

Raises:
    ValueError: unknown sensor.
    RuntimeError: the published file could not be retrieved.

[Module and aliases](../hyperproc-spectral-srf.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral.srf.fetch --runtime`.
