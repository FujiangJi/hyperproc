# hyperproc.readers.aviris._good_bands

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _good_bands(wl: np.ndarray, bbl: np.ndarray | None) -> tuple[np.ndarray, str]
```

The usable-band flag, and where it came from.

AVIRIS-3 is the only variant that ships a ``bbl``. For the other three the
flag is derived from :data:`WATER_BANDS` so the coordinate - and the band
CSV written from it - is populated for every instrument rather than blank
on three of four. ``good_bands_source`` in the attrs records which it is,
because the provider's judgement and ours are not the same thing.

[Module and aliases](../hyperproc-readers-aviris.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.aviris._good_bands --runtime`.
