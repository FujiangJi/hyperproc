# hyperproc.readers.prisma._read_arm

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _read_arm(f, swath: str, arm: str, err: bool=False)
```

Read one spectrometer: rescale, drop unacquired bands, fix axis order.

Returns ``(data, wavelength, fwhm, arm_label, band_index, err)`` where
``err`` is the lazily read error matrix with the same band selection, or
None. Every later selection (overlap, sort, wl_range) goes through
:func:`_take` so the six stay aligned.

[Module and aliases](../hyperproc-readers-prisma.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.prisma._read_arm --runtime`.
