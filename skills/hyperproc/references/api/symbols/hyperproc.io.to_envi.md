# hyperproc.io.to_envi

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def to_envi(ds: xr.Dataset, path: str | Path, var: str | None=None, interleave: str='bil') -> Path
```

Write a cube to an ENVI flat binary with its ``.hdr``.

The reason to choose this over :func:`to_geotiff` is the header. It states
``wavelength``, ``fwhm`` and ``bbl`` as fields, so ENVI, Spectronon and this
package's own readers recover the band centres, widths and bad-band list as
numbers. A GeoTIFF can only carry them as band labels, and cannot carry a
bad-band list at all.

The costs are real. ENVI has no compression, so a full EMIT product is
about 5.1 GB here against 2.2 GB as a deflated GeoTIFF, and it has no
internal pyramids, so a GIS redraws from full resolution.

Args:
    ds: dataset from :func:`hyperproc.open`, orthorectified.
    path: output ``.img``, or a directory to name the file inside. GDAL
        writes the header beside it as ``<stem>.hdr``.
    var: which variable to write. Defaults to the cube variable.
    interleave: ``"bil"`` (default), ``"bip"`` or ``"bsq"``.

Returns:
    The path of the binary. The header is ``<stem>.hdr`` beside it.

Raises:
    ValueError: no CRS, or an unknown interleave.

[Module and aliases](../hyperproc-io.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.io.to_envi --runtime`.
