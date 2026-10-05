# hyperproc.geometry.fix_slope_convention

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def fix_slope_convention(ds: xr.Dataset) -> xr.Dataset
```

Flip ``slope`` to be measured from horizontal, and rebuild ``cos_i``.

Applied when :func:`check_geometry` says a product stores slope from
vertical - AVIRIS-3, on everything seen so far. The shipped ``cos_i`` is
reproduced exactly (r = 1.000) by feeding that complement into the standard
incidence formula, so it inherits the error: one AVIRIS-3 line here has a
median ``cos_i`` of -0.216, meaning most of the scene faces away from the
sun, when 14 deg terrain under a 45.6 deg sun confines it to 0.51-0.85.
SCS+C and C-correction both divide by that.

Modifies ``ds`` in place and returns it.

[Module and aliases](../hyperproc-geometry.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.geometry.fix_slope_convention --runtime`.
