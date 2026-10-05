# hyperproc.quality.build

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def build(ds: xr.Dataset, *, var: str | None=None, derive: tuple[str, ...]=('fill', 'terrain_shadow'), negative_fraction: float=0.1, slope_max: float=45.0, zhai: bool=False, sources: bool=True, verbose: bool=False) -> xr.DataArray
```

Fold every mask a dataset carries into one ``uint16`` flag layer.

Args:
    ds: any hyperproc dataset. Whatever mask layers it has are used; what
        it lacks is simply absent from the result, never guessed.
    var: the cube to read for the derived flags; the main one by default.
    derive: flags to compute rather than read. ``"fill"`` marks pixels with
        no finite value in any usable band, ``"terrain_shadow"`` needs
        ``cos_i``, ``"steep_terrain"`` needs ``slope``,
        ``"negative_reflectance"`` reads the cube. The two defaults are the
        ones worth their cost on every sensor.
    negative_fraction: fraction of usable bands that must be below zero
        before ``negative_reflectance`` is set.
    slope_max: degrees above which ``steep_terrain`` is set.
    zhai: also run the Zhai cloud index from
        :mod:`hyperproc.correct.masks` where the bands it needs exist.
        Off by default: it is a decision, not a measurement, and providers
        that ship a cloud mask should be trusted over it.
    sources: read the provider's own layers. False derives only.
    verbose: print which layers were folded in.

Returns:
    ``uint16`` ``(y, x)`` DataArray named ``quality``, with CF
    ``flag_masks`` and ``flag_meanings`` attributes so the bits travel with
    the data.

Raises:
    ValueError: the dataset has no ``y``/``x`` dimensions.

[Module and aliases](../hyperproc-quality.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.quality.build --runtime`.
