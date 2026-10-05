# hyperproc.readers.pace._add_scanline

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _add_scanline(ds: xr.Dataset, path: Path) -> None
```

Geometry the L2 granule carries itself, so it is usable standalone.

``csol_z`` is a per-scan-line *centre* solar zenith and ``tilt`` the OCI
tilt used to dodge sunglint. Both vary only along track, so they are
broadcast across it - approximate off-centre, but far better than nothing
when no L1B sibling is present.

[Module and aliases](../hyperproc-readers-pace.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.pace._add_scanline --runtime`.
