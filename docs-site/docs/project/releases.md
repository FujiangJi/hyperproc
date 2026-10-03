# Release notes

## Current checkout — {{ source_version }}

The version comes from `hyperproc/__init__.py`. `CITATION.cff` identifies version {{ source_version }} with a release date of {{ citation_date }}. These are local metadata declarations; no remote tag or package-index publication is checked by the website build.

The current package provides:

- Provider readers, common xarray data/geometry conventions, and unified quality flags.
- Optional ISOFIT retrieval, airborne topographic/FlexBRDF correction, and satellite MCD43-based BRDF normalization.
- Spectral transforms, resampling, indices, alignment, and GeoTIFF/ENVI export.
- Archive search and download across NASA CMR, NEON Data API, and DLR EOC STAC, plus an optional interactive notebook map.
- Packaging metadata, installation extras, the atmospheric setup console command, an MIT license, and software citation metadata.

## Changes for 0.1.2

- DLR downloads resume incomplete `*.part` files, retry dropped connections,
  and detect short transfers when the server announces a total size. Progress
  resets the retry counter; permission failures are not retried.
- A new internal netCDF configuration helper detects missing final newlines
  in `.ncrc`, `.daprc`, and `.dodsrc`. Atmospheric setup repairs home-directory
  files, `--check` reports them, and CMR/ISOFIT entry points warn when needed.
- Atmospheric neighbor caps use a conservative estimate that existing
  segmentation labels can lower but cannot raise, improving small-window reuse.
- Installation guidance distinguishes core Python requirements from ISOFIT's
  supported range, clarifies Windows/WSL expectations, and includes Miniconda,
  the SRF/notebook extras, and optional ISOFIT example assets.
- Example pipeline inputs and outputs move beside the scripts under
  `py_tests/0_src_code/`. Terminal credential prompts, explicit download failure
  messages, scene pairing, and DLR policy acceptance are documented.
- Package version and software citation metadata identify 0.1.2 with the
  declared release date {{ citation_date }}. Publication is a separate action.

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
