## On-disk verification

Reopen with rasterio or an appropriate raster reader, not `hp.open` under an invented provider filename. Check count, shape, dtype, CRS, nodata, full affine and rotated corners, descriptions, band CSV alignment, several corresponding values/NaN masks, and known-window ground extent. Header/binary pairs and scene sidecars must exist. Overviews should not alter class meanings. A file's existence or nonzero size is only a first check.

If reconstructing xarray from an exported raster, recover units, wavelength/FWHM/good bands, source grid and necessary geometry from valid provenance; notebook-local `load_product` is not released API and does not restore all metadata. Do not copy same-shaped geometry from another image without verified correspondence.

For mosaics and overlaps, use airborne pipeline footprint/window/mosaic APIs only with valid spatial inputs. `mosaic_geotiffs`, `overlap_agreement_tifs`, `seam_check`, `view_dependence`, `overlap_agreement`, `find_overlapping_pair`, `overlap_windows`, `footprint_bounds`, `footprint_polygon`, `footprint_overlap` expose geometry and diagnostics. They do not make arbitrary scenes temporally/ecologically comparable.
