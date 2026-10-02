# Package revision and website review — 2026-10-02

The website has been rebuilt for the current **hyperproc 0.1.1** working tree.
This review includes committed package changes since `599513d`, the staged
version/citation/README changes, and the 11 edited tutorial notebooks. Existing
website branding, saved map previews, expanded outputs, and concise tutorial
navigation are retained. No package source or original notebook was modified
by this documentation review.

## Code revisions and their documentation consequences

| Source | Current behavior or revision | Website update |
|---|---|---|
| `hyperproc/__init__.py` | Version is now `0.1.1`. | Generated API module pages and package snapshot labels use this version. |
| `CITATION.cff` | Version `0.1.1`, release date `2026-10-02`. | Governance and release notes read the date from metadata; the build rejects inconsistent citation/package versions. |
| `hyperproc/archive/cmr.py` | Login failure guidance recommends persisted `earthaccess.login(persist=True)` or environment credentials. The download implementation still calls `ea.login()`. | Data-access, search, troubleshooting, and generated source reference reflect the login guidance. Removed the claim that downloads cannot prompt. |
| `hyperproc/atmos/setup.py` | `--base` help identifies `~/.isofit` as default and explains shared assets. | Installation, configuration, atmospheric workflow, troubleshooting, and generated API describe the base, configuration file, engine prerequisites, and `--check`. |
| `hyperproc/correct/mcd43.py` | Missing Earth Engine error recommends `hyperproc[brdf]`. | Satellite workflow and troubleshooting show the extra, authentication, and Earth Engine project configuration. |
| `hyperproc/spectral/srf.py` | Spreadsheet dependency error recommends `hyperproc[srf]`. | Resampling explains the extra, spreadsheet/HTTP dependencies, and SRF caching. |
| `README.md` and `pyproject.toml` | Expanded Python/environment guidance and current dependency declarations. Setuptools currently discovers `hyperproc*`. | Installation follows the current README and displays a generated table of every direct dependency and optional-extra requirement. Package discovery is documented in release notes. |
| 11 notebooks under `tests/0_src_code/` | Introductory installation instruction changes from `earthengine-api` to `hyperproc[brdf]`; their saved code/output cells are unchanged by these edits. | Regenerated DESIS, EMIT, EnMAP, PRISMA, and Tanager tutorials and window tutorials, plus the PACE window tutorial. All 17 downloadable notebook copies match the current originals. |

The four committed Python module changes above concern error/help wording;
they do not introduce new function signatures or scientific calculations.
The API nevertheless regenerates signatures, defaults, docstrings, source
listings, and exported-name links for every module in the current checkout.

## Additional mismatches corrected

- Credential availability is distinguished from successful authentication.
  `credentials()` / `can_download()` provide local availability hints; example
  pipelines can use them for preflight, but `hp.download()` does not itself
  guarantee a prompt-free download or validate credentials beforehand.
- Default DEM, SRF, and MCD43 cache locations are documented under
  `~/.cache/hyperproc`, with `HYPERPROC_CACHE_DIR` support.
  `nbar(cache_dir=...)` is distinguished from `mcd43.fetch(out_dir=...)`;
  `source='local'` uses saved parameters instead of fetching from Earth Engine.
- sRTMnet setup includes its 6S dependency and Fortran/build tools. LibRadTran
  setup describes C/Fortran tooling and GSL. `--check` inspects prerequisites
  without downloading assets.
- The reader-list example no longer assigns `hp.list_readers()` as though it
  returned a collection: it prints the registry and returns `None`.
- Validation and references acknowledge the retained regression suite,
  archive recordings, reader tests, and the R smoothing-reference fixture.
  Existing tests are distinguished from independent scientific validation.
- Citation/maintainer/license pages use available repository metadata rather
  than claiming those details are unknown. About, governance, and status
  wording follows the current Spectral Ribbon artwork.

## Coverage and prevention of stale pages

The review covered all **44 maintained Markdown guides**, including the
curated tutorial companions, and regenerated all API and notebook pages.
The built site contains **117 HTML pages**, **53 API modules**, **459 top-level
functions/classes**, and **68 public class methods/properties**. It includes
**17 notebooks**, **147 stored PNG figures**, and **14 archived map previews**
with **109 saved granule entries**.

New checks run as part of `manage.py build` / `manage.py check`:

1. Verify rendered anchors for public class methods/properties, in addition to
   the existing top-level API coverage check.
2. Parse the 44 maintained Python example blocks and bind 79 resolvable calls
   to current source signatures. Detect removed callable exports, unsupported
   keywords, missing required arguments, and unknown installation extras.
3. Track hashes of package source, README/metadata, maintained guides,
   templates, styles, scripts, artwork, vendored browser assets, and map
   recordings. Check notebook copies against their saved source hashes.
4. Generate dependency tables, citation date, version, and API coverage counts
   from source metadata. Reject citation/package version disagreement.

These checks are static. They do not execute examples, validate argument
values or data semantics, or fully analyze dynamic calls/class constructors.
Human-written explanations and source docstrings still require review when
behavior changes.

## Verification performed for this update

- Strict MkDocs build passed: 117 HTML pages and **50,097 local link, asset,
  and fragment references**; external URLs are excluded.
- All 459 API definitions and 68 public class members render; package/source
  hashes and all 17 downloadable notebook copies match the checkout.
- Maintained example audit passed: 44 pages, 44 Python blocks, 79 calls.
- Five regression tests for the new example auditor passed: valid alias/call,
  removed keyword, missing required argument, removed export, and unknown extra.
- A negative freshness test correctly rejected an altered expected guide hash;
  the original generated manifest was restored immediately afterward.
- Chromium checked the current-version label on all 53 API module pages, the
  four revised module source listings, generated installation requirements,
  citation/release dates, and all 11 revised tutorials.
- Chromium checked API/installation/home layouts at 390 px and API at desktop
  width, with no page-wide overflow or JavaScript errors. API screenshots:
  `/tmp/hyperproc-api-current-desktop.png` and
  `/tmp/hyperproc-api-current-phone.png`.

## Scope limits and future updates

The retained scientific test suite, notebook cells, provider login/downloads,
and atmospheric retrievals were not executed for this documentation update.
Saved tutorial output is the notebook's existing result, not a fresh run of
0.1.1. Python/platform expectations follow the current package README;
publication on PyPI and a remote release tag were not verified.

After changing code, docstrings, metadata, guides, or notebooks, run from the
repository root:

```bash
docs-site/.venv/bin/python docs-site/manage.py build
```

Then refresh the website. The existing server serves the built files;
it does not automatically watch or rebuild the checkout. For changed results,
rerun and save the affected notebook cells before building. Use
`docs-site/.venv/bin/python docs-site/manage.py check` to detect changes made
since the last generation.
