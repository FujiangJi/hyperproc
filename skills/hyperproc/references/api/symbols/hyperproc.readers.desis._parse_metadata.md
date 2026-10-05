# hyperproc.readers.desis._parse_metadata

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _parse_metadata(path: Path)
```

Wavelengths, FWHM, per-band gain/offset and the scene-level scalars.

``<band>`` appears under two parents in DESIS metadata - ``bandCharacterisation``
(spectral) and ``interiorOrientation`` (geometric) - so the search is scoped
to the former. Reading them unscoped silently doubles the band count.

[Module and aliases](../hyperproc-readers-desis.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.desis._parse_metadata --runtime`.
