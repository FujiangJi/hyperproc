## Translation-based registration

`tie_points`, `estimate_shift`, `apply_shift`, `coregister` form a translation-oriented interface. Read [alignment](../api/hyperproc-align.md) before combining them. Phase correlation at a selected wavelength (default 860 nm) and tile consistency can be invalidated by clouds, weak texture, seasonal changes, mismatched support, or deformation. Inspect peak strength, offsets/scatter and geographic conventions before applying. Do not set `force=True` simply to bypass poor evidence.

`coregister(..., resample=False)` changes georeferencing without interpolating spectral pixels; `resample=True` samples the reference grid. Distinguish grid metadata translation, resampling, and proven ground alignment. This is not a nonlinear warp/bundle-adjustment system. Rotated and complex cross-sensor cases need dedicated checks rather than claims of universal accuracy.
