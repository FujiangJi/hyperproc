# hyperproc.readers.prisma._add_l1_geometry

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _add_l1_geometry(ds: xr.Dataset, f, sib: Path | None) -> None
```

Per-pixel angles for L1: from the L2 sibling when given, else ephemeris + scene sun angles.

[Module and aliases](../hyperproc-readers-prisma.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.prisma._add_l1_geometry --runtime`.
