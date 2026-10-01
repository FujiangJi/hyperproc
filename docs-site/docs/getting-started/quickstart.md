# Your first dataset

Start with a provider **surface-reflectance** product and a small spatial subset. This avoids downloading atmospheric models or running a retrieval just to learn the data interface.

## 1. Install and import

Follow [installation](installation.md) to install this checkout with Python {{ python_requires }}. If you need an input scene first, use the [search and download workflow](../workflows/search.md).

```python
import hyperproc as hp
print(hp.__version__)
print(hp.summary())
```

## 2. Open and inspect

```python
ds = hp.open("/path/to/provider_reflectance_product")
hp.describe(ds)
print(ds.attrs)
print(ds.wavelength.values)
```

`hp.open()` selects a reader using the filename, or explicit `sensor=` and `level=` where supported. The returned cube generally has `(y, x, wavelength)` dimensions. Opening is lazy for the cube, but reading metadata, geometry checks, and `describe()` can still access data.

## 3. Work on a window

```python
small = ds.isel(y=slice(0, 200), x=slice(0, 200))
q = hp.quality_flags(small)
usable = hp.quality_apply(small, q)
ndvi = hp.spectral_index(usable, "NDVI")
```

Choose a window inside valid observations, not automatically the upper-left corner of a rotated or padded scene. Missing provider flags do not prove clear-sky conditions.

## 4. Export a mapped product

```python
mapped = usable if usable.attrs.get("crs") else hp.georeference(usable)
hp.to_geotiff(mapped, "products/first_scene.tif")
hp.bands_to_csv(mapped, "products/first_scene_bands.csv")
```

Export writes files and triggers computation. For a swath without usable latitude/longitude, do not invent a CRS; obtain the required geolocation first.
