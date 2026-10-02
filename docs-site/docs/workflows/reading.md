# Read and inspect

## Discover the supported interface

```python
import hyperproc as hp
print(hp.summary())
hp.list_readers()  # prints the supported reader table; returns None
```

`hp.sniff(path)` identifies a provider product from its filename pattern without reading the spectral cube. `hp.open(path, sensor=None, level=None, **kwargs)` resolves the registry entry, opens the product, and passes keyword arguments to its reader. Read the sensor-specific signature before supplying options; not every reader accepts `chunks`, `geometry`, or `good_bands_only`.

## Inspect before processing

```python
ds = hp.open("/path/to/provider_product")
hp.describe(ds)
var = hp.main_var(ds)
print(ds[var].dims, ds[var].dtype)
print(ds.attrs.get("units"), ds.attrs.get("level"))
print(ds.attrs.get("crs"), ds.attrs.get("transform"))
```

Confirm units, scaling, bad-band handling, source metadata, expected geometry, and the amount of valid data. `describe()` reads sampled values; it is not purely a metadata operation. Scalar angles may be expanded spatially without gaining additional physical information.

## Subset explicitly

```python
window = ds.isel(y=slice(3000, 3500), x=slice(400, 900))
visible = hp.open("/path/to/provider_product", wl_range=(400, 900))
```

The spatial example is only appropriate when those indices exist and intersect valid observations. Wavelength subsets change available spectral features. Removing necessary bands before atmospheric inversion or a vegetation mask can make a later operation impossible.

## Error interpretation

Unknown naming/level information normally raises `ValueError`; missing paths raise `FileNotFoundError`; registered but unwritten readers raise `NotImplementedError`. Explicit sensor/level parameters are appropriate for genuine naming ambiguity, not for forcing unsupported data through the wrong reader.

See the [core API](../api/hyperproc.md), [registry](../api/hyperproc-registry.md), and [sensor matrix](../sensors/index.md).
