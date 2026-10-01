# PACE OCI

This reader handles **L1B TOA reflectance** and **L2 SFREFL surface reflectance**. It is not a general reader for every PACE L2 ocean-colour variable.

```python
ds = hp.open("/path/to/PACE_OCI.product.L2.SFREFL.nc")
print(ds.attrs.get("level"), ds.attrs.get("units"))
```

## Spectral organization

The L1B route combines blue, red, and SWIR detector arrays, sorts wavelengths, and retains source-band indexing. Bandpass information differs across spectral regions; nominal VNIR widths and available SWIR widths should not be assumed equally precise.

The main variable is named `reflectance` for both levels, but its **physical meaning changes**. L1B TOA reflectance must not be analyzed as retrieved land surface reflectance without the appropriate scientific treatment.

## Geometry and mapping

PACE data are read as a latitude/longitude swath. L1B geometry can supplement L2; scanline summaries or incomplete geometry are not equivalent to a complete angle field. Keep corresponding products available where the workflow needs them.

`hp.georeference()` has PACE-specific defaults, including a geographic target grid. Choose resolution and footprint handling deliberately; a wide swath and coarse spatial support require different assumptions from a metre-scale airborne line.

## Atmospheric and terrestrial use

The atmospheric route converts TOA reflectance using its dedicated irradiance/geometry logic and keeps the supported radiative-transfer band grid. Preserve source indices and the output band table. For terrestrial work, also verify cloud, water, mixed-pixel, and surface-product assumptions. A land-oriented product writing values over water does not validate those values for terrestrial methods.

[Reader API](../api/hyperproc-readers-pace.md) · [Window tutorial](../tutorials/pace-window-tutorial.md)
