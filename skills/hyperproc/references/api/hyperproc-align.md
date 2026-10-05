# hyperproc.align

Release baseline **0.1.2**; source `hyperproc/align.py`. Choose a callable below rather than loading every declaration.

Coregistration: measuring and removing the misalignment between two scenes.

Two products of the same ground rarely land on the same pixel. Geolocation
errors of one to two pixels are normal even in operational products, and they
are fatal to anything that compares scenes pixel by pixel: fusing a coarse
hyperspectral cube with a fine multispectral one, stacking dates into a time
series, or validating one sensor against another. Cropping both to a common
extent and trusting the headers, which is the usual shortcut, aligns the
corners and leaves the content offset.

    import hyperproc as hp
    fit = hp.estimate_shift(emit, planet)      # how far off, and how sure
    print(fit["report"])
    aligned = hp.coregister(emit, planet)      # same, then fixed

How it measures
---------------
Phase correlation between one band of each scene, resampled onto the
reference's grid. It uses the phase of the cross-power spectrum and not its
amplitude, so a brightness or calibration difference between two sensors does
not move the answer, which is what makes it usable across instruments. The
peak is refined by a parabolic fit to about a tenth of a pixel.

Whether to believe it
---------------------
A correlation peak always exists, even between unrelated images, so two
numbers come back with the shift. ``snr`` is the peak height against the rest
of the surface, and the scene is also split into tiles that are matched
independently: a real misregistration is the same in every tile, while a
spurious one scatters. ``consistent`` is False when the tiles disagree, and
that is the signal to look at the images rather than to apply the shift.

How it corrects
---------------
By default the georeferencing is moved and the pixels are left alone, which is
exact and costs nothing. ``resample=True`` puts the cube on the reference's
own grid instead, which is what pixel-to-pixel work needs, at the cost of one
interpolation.

## Declared exports

`estimate_shift`, `tie_points`, `apply_shift`, `coregister`, `DEFAULT_WAVELENGTH`

## Declared callables and classes

- [_grid_of](symbols/hyperproc.align._grid_of.md) — internal
- [_band_on](symbols/hyperproc.align._band_on.md) — internal
- [_prepare](symbols/hyperproc.align._prepare.md) — internal
- [_common_box](symbols/hyperproc.align._common_box.md) — internal
- [_phase_shift](symbols/hyperproc.align._phase_shift.md) — internal
- [tie_points](symbols/hyperproc.align.tie_points.md)
- [_to_metres](symbols/hyperproc.align._to_metres.md) — internal
- [_nearest_band](symbols/hyperproc.align._nearest_band.md) — internal
- [estimate_shift](symbols/hyperproc.align.estimate_shift.md)
- [apply_shift](symbols/hyperproc.align.apply_shift.md)
- [coregister](symbols/hyperproc.align.coregister.md)
- [_to_reference_grid](symbols/hyperproc.align._to_reference_grid.md) — internal

## Constant expressions

- [DEFAULT_WAVELENGTH](constants/hyperproc.align.DEFAULT_WAVELENGTH.md)
