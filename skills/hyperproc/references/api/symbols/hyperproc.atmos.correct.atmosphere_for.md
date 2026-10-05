# hyperproc.atmos.correct.atmosphere_for

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def atmosphere_for(lat: float, month: int) -> str
```

MODTRAN atmosphere class for a scene at ``lat`` degrees in ``month``.

Tropical below 23.5 degrees, mid-latitude below 60, sub-arctic above.
Summer variants are the default; the winter variant is used only for
Nov-Feb in the north and May-Aug in the south, because ISOFIT derives the
upper bound of the water-vapour grid from the class (summer 5.35 g/cm²,
winter 1.37 at sea level) and a humid scene under a winter class rails.

[Module and aliases](../hyperproc-atmos-correct.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.correct.atmosphere_for --runtime`.
