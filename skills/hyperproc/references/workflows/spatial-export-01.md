## Establish the grid

Inspect full affine + CRS and whether coordinates are map axes or detector indices. x/y arrays alone cannot describe rotation/shear. Pixel windows are half-open slices and belong to the source grid; applying the same indices to a different acquisition is only justified when the ground mapping is actually known to match.

`hp.georeference` uses available lat/lon through sensor-appropriate gridding, or match via `like=`. Choose EPSG, resolution and radius deliberately if defaults do not serve the question. `utm_epsg` derives a zone, not physical orthorectification. `latlon_grid` supports grid coordinate conversion; retain CRS/affine conventions. EMIT has a dedicated GLT route. Nearest-source gathering is not a universal raw-instrument orthorectification engine. Do not fill missing geolocation with an invented transform.
