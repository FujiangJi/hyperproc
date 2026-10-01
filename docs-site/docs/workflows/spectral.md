# Spectral processing

Spectral transforms produce another cube. They are distinct from feature extraction, which reduces spectra to maps. Keep a copy of the physically interpreted input and record every transform applied to it.

## Band selection by wavelength

```python
red = hp.band_at(ds, 660)
nir = hp.band_at(ds, 860)
```

The default nearest-band tolerance is 20 nm. This is a selection tolerance, not a claim that any band within 20 nm is adequate for a narrow feature. Inspect the actual selected wavelength and use tighter tolerances where scientifically needed.

## Smoothing without bridging unusable regions

```python
smoothed = hp.smooth_spectra(ds, window=7, order=2,
                             method="savgol", good_only=True)
```

Savitzky–Golay and moving-window options operate within usable-band runs. NaNs can be temporarily interpolated for filtering and then restored. The procedure alters spectral shape and is optional, not a substitute for atmospheric correction or wavelength calibration.

## Spline gap filling

```python
filled = hp.spline_gapfill(ds, df=60, threshold=0.018, despike=True)
```

This route intentionally fills selected spectral gaps after artifact masking and spline fitting, then masks designated water-absorption regions. `spline_filled` records interpolated values. The default exclusion windows are PRISMA-oriented; inspect their suitability before applying them to another sensor. An interpolated absorption is not an observation.

## Continuum removal

```python
continuum_removed = hp.continuum_removal(ds, window=(2000, 2300))
```

The spectrum is normalized by an upper convex hull within the selected interval and usable-band runs. The interval determines the continuum shoulders. Results depend on missing bands, noise, and the feature window; do not compare differently defined windows as if they were the same metric.

## Derivatives

```python
first_derivative = hp.spectral_derivative(ds, order=1, window=7, poly=2)
```

The implementation uses a Savitzky–Golay fit and the representative wavelength spacing of each run. Irregular spacing needs attention. Derivative values carry wavelength-dependent units and should not be described as surface reflectance despite sharing the source variable name.

## Uncertainty and feature preservation

Several transforms discard uncertainty rather than propagate it. Check output variables and attributes. Compare narrow-feature analyses against unsmoothed spectra and report sensitivity to smoothing choices. See [spectral API](../api/hyperproc-spectral.md).
