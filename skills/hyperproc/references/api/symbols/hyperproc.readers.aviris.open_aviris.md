# hyperproc.readers.aviris.open_aviris

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def open_aviris(path: str | Path, product: str | None=None, wl_range: tuple[float, float] | None=None, good_bands_only: bool=False, geometry: bool=True, extras: bool=True, uncertainty: bool=False, fix_geometry: bool | str='auto', sort_bands: bool=True, ortho: bool=True, fill: float | None=None, map_coords: bool=False, chunks: str | int | dict | None='auto') -> xr.Dataset
```

Open an AVIRIS-Classic, -NG, -3 or -5 flightline.

Args:
    path: the cube, its ``.hdr``, or the directory holding it. A directory
        is searched for a radiance or reflectance cube; if it holds both,
        pass ``product=`` to choose.
    product: ``"reflectance"`` or ``"radiance"``. Inferred from the
        filename when you point at a cube, required only to break a tie.
    wl_range: ``(min_nm, max_nm)``, applied before any data is read.
    good_bands_only: NaN out the water-vapour bands, keeping the band count
        so indices stay aligned with the instrument's own grid. Uses the
        product's ``bbl`` when it ships one (AVIRIS-3 flags 35 of 284
        bands) and :data:`WATER_BANDS` otherwise.
    geometry: attach the OBS layers - ``sza``, ``saa``, ``vza``, ``vaa``,
        ``slope``, ``aspect``, ``cos_i``, ``path_length`` - plus a derived
        ``raa``. Searches sibling directories for the granule's OBS file.
    extras: attach the atmospheric state - ``aot``/``wv`` for AVIRIS-3 and
        -5, the three-phase water retrieval for Classic.
    uncertainty: attach the per-band posterior uncertainty cube where one
        ships (AVIRIS-3, -5). Doubles the data volume.
    fix_geometry: ``"auto"`` (default) runs :func:`check_geometry`, which
        differentiates the granule's own DEM and corrects ``slope`` and
        ``cos_i`` only if the product actually stores slope from vertical -
        AVIRIS-3 does, the other three do not, and the verdict lands in
        ``attrs["geometry_check"]``. ``True`` forces the correction,
        ``False`` returns every layer exactly as the file has it.
    ortho: AVIRIS-5 only, and only for L1B. Its radiance ships on the raw
        2000 x 1239 sensor grid with a lookup table, unlike its already
        gridded L2A reflectance, so this applies that GLT to put the two
        levels on the same map grid. ``False`` returns the sensor grid,
        which then carries no CRS or transform. The ENVI instruments
        deliver orthorectified cubes and ignore this.
    sort_bands: put the bands in ascending wavelength order. AVIRIS-Classic
        reads out four spectrometers whose ranges overlap at the joins, so
        its wavelengths step *backwards* three times - 667.5 -> 655.5 nm at
        band 31, and again at 95 and 159. That leaves the coordinate
        non-monotonic, and ``sel(wavelength=..., method="nearest")`` raises
        rather than returning a band. Sorting is a permutation, so nothing
        is lost, and ``band_index`` keeps each band's original position in
        the file. A no-op for NG, AVIRIS-3 and -5, which are already sorted.
    fill: override the no-data value. Otherwise taken from the ENVI
        header's ``data ignore value``, falling back to -50 for Classic
        radiance, which declares none (see :data:`CLASSIC_RDN_FILL`), and
        to -9999 for AVIRIS-5.
    map_coords: add exact 2-D ``easting``/``northing``. The flight-aligned
        grids are rotated, so the 1-D ``x``/``y`` follow the top row and
        left column only; this computes the full affine per pixel at the
        cost of two float64 arrays the size of the image.
    chunks: dask chunking for the cube. ``"auto"`` keeps a 10-30 GB
        flightline lazy and chunks along ``y`` only, matching the
        line-major layout on disk so a spatial subset is one sequential
        read; ``None`` reads the cube into memory eagerly.

Returns:
    ``xarray.Dataset`` with ``reflectance`` or ``radiance`` on
    ``(y, x, wavelength)``, ``wavelength``/``fwhm`` coordinates in nm, and
    ``attrs["transform"]`` in GDAL order carrying the grid rotation.

Raises:
    FileNotFoundError: no cube matched, or a directory held none.
    ValueError: the filename is not a recognised AVIRIS granule, or a
        directory holds both products and ``product=`` was not given.

[Module and aliases](../hyperproc-readers-aviris.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.aviris.open_aviris --runtime`.
