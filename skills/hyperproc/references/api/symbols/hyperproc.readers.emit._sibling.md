# hyperproc.readers.emit._sibling

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _sibling(path: Path, level: str, product: str, rest: str) -> Path | None
```

The sibling granule, tolerating a different processing-version suffix.

``rest`` ends in the version (``..._2311213_002``); a MASK or OBS
reprocessed to ``_003`` next to an RFL at ``_002`` is still the same scene,
so fall back to the newest version of the same scene id.

[Module and aliases](../hyperproc-readers-emit.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.emit._sibling --runtime`.
