## Geometry and masks

Some angles are scene-level values. `sceneAzimuth` is not silently treated as view azimuth. Geometry may therefore be insufficient for a requested downstream operation even when reflectance can be read correctly.

Quality layers are available through `quality=True`, with optional band-level quality. Land/water cloud flags and other provider classes are translated where available. Missing fields remain missing rather than being invented.
