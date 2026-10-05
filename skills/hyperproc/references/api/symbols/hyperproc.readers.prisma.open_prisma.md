# hyperproc.readers.prisma.open_prisma

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def open_prisma(path: str | Path, cube: str='full', join_priority: str='swir', wl_range: tuple[float, float] | None=None, good_bands_only: bool=False, angles: bool=True, latlon: bool=False, err_matrix: bool=False, extras: bool=True, angles_source: str='l2', geolocation: str='l2') -> xr.Dataset
```

Open a PRISMA granule.

Args:
    path: ``PRS_<level>_STD_*.he5``.
    cube: ``"full"`` merges both spectrometers, ``"vnir"`` (~407-977 nm) or
        ``"swir"`` (~943-2497 nm) returns one alone.
    join_priority: which spectrometer wins in the ~943-977 nm overlap when
        ``cube="full"``. ``"swir"`` (prismaread's default here) or ``"vnir"``.
    wl_range: ``(min_nm, max_nm)`` subset, applied after the join.
    good_bands_only: not supported - ASI ships no per-band quality flag.
        Raises, with a pointer to ``wl_range``.
    angles: attach per-pixel ``sza``, ``vza``, ``raa`` (degrees).
    latlon: attach the per-pixel ``lat``/``lon`` arrays. Always attached for
        L1/L2B/L2C, where they are the only georeferencing there is.
    err_matrix: attach the per-band pixel error matrix, band-aligned with
        the cube (same subset, order and overlap resolution), lazy uint8:
        ``l2_err`` for L2 (0 = no error flag), ``l1_sat_err`` for L1
        (0 ok, 1 saturated, 2 error, 3 both). Adds a uint8 array the size
        of the cube.
    extras: for L2C, attach the AOT / AEX / COT / WVM maps.
    angles_source: L1 only. ``"l2"`` borrows the per-pixel angles from an
        L2C/L2B file of the same acquisition beside the L1 when there is
        one, else falls back to ``"ephemeris"`` (view angles from the
        satellite positions in the file, sun angles scene-level).
    geolocation: L1 only. ``"l2"`` uses the L2C/L2B geolocation (ASI
        refines it during L2 processing; it differs from L1's by up to a
        few pixels), ``"l1"`` keeps the L1 arrays.

Returns:
    Dataset with ``reflectance`` or ``radiance`` on ``(y, x, wavelength)``,
    ``wavelength`` and ``fwhm`` coordinates in nm, ascending.

[Module and aliases](../hyperproc-readers-prisma.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.prisma.open_prisma --runtime`.
