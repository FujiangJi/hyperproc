# hyperproc.readers.aviris._search

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _search(start: Path, granule: str, globs: tuple[str, ...], roots: list[Path] | None=None) -> Path | None
```

Find a granule's sibling file, looking in nearby directories.

NG and Classic split a flightline into ``*_rdn_*`` and ``*_rfl_*`` folders
and put the OBS in the radiance one, so opening reflectance means looking
one level up and back down.

[Module and aliases](../hyperproc-readers-aviris.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.aviris._search --runtime`.
