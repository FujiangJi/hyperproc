# Release notes

## Current checkout — {{ source_version }}

The version comes from `hyperproc/__init__.py`. `CITATION.cff` identifies version {{ source_version }} with a release date of {{ citation_date }}. These are local metadata declarations; no remote tag or package-index publication is checked by the website build.

The current package provides:

- Provider readers, common xarray data/geometry conventions, and unified quality flags.
- Optional ISOFIT retrieval, airborne topographic/FlexBRDF correction, and satellite MCD43-based BRDF normalization.
- Spectral transforms, resampling, indices, alignment, and GeoTIFF/ENVI export.
- Archive search and download across NASA CMR, NEON Data API, and DLR EOC STAC, plus an optional interactive notebook map.
- Packaging metadata, installation extras, the atmospheric setup console command, an MIT license, and software citation metadata.

## Revisions in the current checkout

- Earthdata download errors now recommend a persisted `earthaccess.login(persist=True)` login or environment credentials.
- Atmospheric setup help documents the default `~/.isofit` asset base and a shared `--base` directory.
- Earth Engine and published SRF dependency errors recommend the `brdf` and `srf` extras.
- Setuptools discovers `hyperproc*` packages, so new subpackages such as `hyperproc.archive` are included without a hand-maintained package list.
- Package version, citation metadata, installation requirements, and example-pipeline setup guidance were updated.

## Website update for the current package

- Installation instructions now follow `pyproject.toml` and its optional extras.
- Data-access and search workflows document collection coverage, credentials, NEON flightline listing, and DLR sign-on.
- API navigation includes a dedicated Archive section and the search/download notebook joins the tutorial library.
- Version labels and coverage counts refresh from the build manifest.
- Maintainer, repository, license, and citation details replace the older missing-metadata placeholders.
- The Spectral Ribbon logo family and forest-and-mountain homepage support light and dark themes.
- API coverage checks include public class members; maintained Python examples are checked against source signatures and installation extras.
- Exact dependency requirements and the citation date refresh from package metadata at build time.

The site documents the current source rather than reconstructing an unverified historical release sequence. Migration/deprecation policy, remote release history, and versioned hosting are not established by this build.
