# hyperproc.correct.brdf.fit_group

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def fit_group(rho, sza, vza, raa, ndvi, wavelength=None, volume='ross_thick', geometric='li_dense_r', b_r=1.0, h_b=2.0, sza_ref=None, bins=None, bin_ndvi=None, **bin_kwargs)
```

Fit a :class:`FlexFit` from pooled samples of one or many images.

``sza_ref`` defaults to the mean solar zenith of the samples, which for a
group is the group mean.

``bin_ndvi`` is the population the dynamic bin edges are cut from when
``bins`` is not given. FlexBRDF cuts them from the NDVI of *every* valid
pixel of every image in the group, and only then restricts the fit to the
masked, subsampled pixels; passing the fit sample instead (the default
when ``bin_ndvi`` is None) shifts the edges upward because the vegetation
mask has already removed the low-NDVI tail.

[Module and aliases](../hyperproc-correct-brdf.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.brdf.fit_group --runtime`.
