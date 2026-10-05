# hyperproc.readers._common.normalise_angles

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def normalise_angles(ds: xr.Dataset) -> None
```

One angle convention for every reader.

* scene-level scalars become attrs ``sza``/``saa``/``vza``/``vaa``
  (the provider's names are kept as well);
* a scalar with no matching layer is broadcast lazily to a constant
  ``(y, x)`` layer, so geometry export and ``describe`` treat every sensor
  alike (``long_name`` says it is scene-level);
* azimuths and aspect are wrapped to [0, 360);
* ``raa`` = (vaa - saa) mod 360 is added when both azimuth layers exist.

[Module and aliases](../hyperproc-readers-_common.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers._common.normalise_angles --runtime`.
