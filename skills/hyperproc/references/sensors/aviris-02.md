## Options and cautions

- `wl_range` subsets wavelengths; `sort_bands` controls spectral ordering.
- `geometry` attaches available observation/terrain information.
- `fix_geometry="auto"` checks a slope convention and repairs it when diagnosed; it is not a general correction for arbitrary metadata errors.
- `good_bands_only` uses bad-band handling specific to this reader; the current path can mask flagged values rather than remove the spectral coordinates.
- `map_coords=True` can expose two-dimensional map coordinates for rotated grids.
- `ortho=False` is meaningful only for supported variant pathways; do not assume it unprojects an already orthorectified ENVI product.
- Optional uncertainty and ancillary retrieval layers increase I/O.

For AVIRIS-5, distinguish a file chunk from a physical flightline when pooling samples and choosing overlap pairs. For all variants, use the full affine transform for spatial comparisons.
