# Release notes

## Current checkout — {{ source_version }}

The version comes from `hyperproc/__init__.py`. `CITATION.cff` identifies version 0.1.0 with a release date of 2026-09-29. These are local metadata declarations; no remote tag or package-index publication is checked by the website build.

The current package provides:

- Provider readers, common xarray data/geometry conventions, and unified quality flags.
- Optional ISOFIT retrieval, airborne topographic/FlexBRDF correction, and satellite MCD43-based BRDF normalization.
- Spectral transforms, resampling, indices, alignment, and GeoTIFF/ENVI export.
- Archive search and download across NASA CMR, NEON Data API, and DLR EOC STAC, plus an optional interactive notebook map.
- Packaging metadata, installation extras, the atmospheric setup console command, an MIT license, and software citation metadata.

## Website update for the current package

- Installation instructions now follow `pyproject.toml` and its optional extras.
- Data-access and search workflows document collection coverage, credentials, NEON flightline listing, and DLR sign-on.
- API navigation includes a dedicated Archive section and the search/download notebook joins the tutorial library.
- Version labels and coverage counts refresh from the build manifest.
- Maintainer, repository, license, and citation details replace the older missing-metadata placeholders.
- The existing spectral Earth logos and light/dark theme are retained.

The site documents the current source rather than reconstructing an unverified historical release sequence. Migration/deprecation policy, remote release history, and versioned hosting are not established by this build.
