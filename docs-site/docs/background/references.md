# Scientific and technical references

These sources explain the methods and data concepts used in the documentation. They are **not** a publication or validation record for hyperproc itself.

## Imaging spectroscopy and ecosystems

- [NEON imaging spectrometer](https://www.neonscience.org/data-collection/imaging-spectrometer): instrument context and ecological applications.
- [NEON Airborne Observation Platform](https://www.neonscience.org/data-collection/airborne-remote-sensing): airborne observation context.

## Atmospheric retrieval

- [ISOFIT documentation](https://isofit.github.io/isofit/latest/): inversion framework, installation, models, and upstream references. hyperproc orchestrates this framework rather than replacing it.
- Thompson et al. (2018), *Optimal estimation for imaging spectrometer atmospheric correction*, Remote Sensing of Environment, **216**, 355–373. [Publisher record / DOI: 10.1016/j.rse.2018.07.003](https://www.sciencedirect.com/science/article/pii/S0034425718303304).

## Directional reflectance

- Queally et al. (2022), *FlexBRDF: A Flexible BRDF Correction for Grouped Processing of Airborne Imaging Spectroscopy Flightlines*. [DOI: 10.1029/2021JG006622](https://doi.org/10.1029/2021JG006622).
- [NASA MCD43A1 Version 6.1 dataset description](https://data.nasa.gov/dataset/modis-terraaqua-brdf-albedo-model-parameters-daily-l3-global-500m-v061-53475): BRDF/albedo model-parameter product, temporal support, and spatial scale.
- Roy et al. (2016), c-factor normalization: cited in `hyperproc.correct.cfactor`. **Full bibliographic record awaiting verification**; no unverified DOI is supplied here.

## Topographic and spectral methods

The implementation docstrings identify Teillet, Guindon & Goodenough (1982), Gu & Gillespie (1998), and Soenen, Peddle & Coburn (2005) as the foundations of cosine/C/SCS/SCS+C corrections. **A complete, verified bibliography is under construction.** The spectral-index registry also carries per-index references; these are source metadata, not a completed citation audit.

The spline implementation documents a port of R's smoothing-spline behavior. Its numerical equivalence claims require retained, independently reproducible comparison evidence before use in a manuscript.

## Documentation and neighboring software

- [HyperCoast](https://hypercoast.org/) and [ISOFIT](https://isofit.github.io/isofit/latest/) inspired this site's navigation and reference/tutorial separation.
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/getting-started/) supplies the documentation theme.
- [MkDocs configuration](https://www.mkdocs.org/user-guide/configuration/) describes local builds and site settings.

## Citing hyperproc

**Awaiting maintainer confirmation:** authors, release archive, repository URL, license, and preferred citation. Do not cite another package's paper as if it were the hyperproc software paper.
