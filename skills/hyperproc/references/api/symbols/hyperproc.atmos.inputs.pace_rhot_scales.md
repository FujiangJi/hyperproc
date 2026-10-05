# hyperproc.atmos.inputs.pace_rhot_scales

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def pace_rhot_scales(ds: xr.Dataset)
```

Per-band and per-pixel factors turning OCI ``rhot`` into µW cm-2 nm-1 sr-1.

The L1B stores ``rhot = Lt * pi * d2 / (F0 * cos(sza))`` with ``F0`` in
W m-2 um-1 per band and ``d2`` (``earth_sun_distance_correction``) as a
global attribute; ``band_index`` says which F0 each band of the sorted
cube came from. So ``Lt = rhot * F0 * cos(sza) / (pi * d2) * 0.1``.

[Module and aliases](../hyperproc-atmos-inputs.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.inputs.pace_rhot_scales --runtime`.
