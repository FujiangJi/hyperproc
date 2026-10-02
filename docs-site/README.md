# hyperproc local documentation

Material for MkDocs documentation generated from the adjacent `hyperproc/` source
and `tests/0_src_code/` notebooks. No package import, atmospheric retrieval,
notebook execution, scene download, or public deployment occurs during a build.

## Open the already-built site

From this directory, using Python 3.11 or newer:

```sh
python manage.py serve
```

Open <http://127.0.0.1:8765/>. Stop with Ctrl-C. The `site/` directory contains the
static build; use HTTP rather than double-clicking HTML so search and routes work.

## Rebuild after source changes

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py build
python manage.py serve
```

The build regenerates API/notebook pages, runs MkDocs in strict mode, then checks
local links, fragments, assets, source hashes, original notebook copies, and
rendered coverage for all top-level functions/classes. It does not test scientific
algorithms. The tested documentation dependencies are pinned separately from the
research environment. Use Python 3.11 or newer, matching the package requirement.

## Where to edit

- `docs/background`, `getting-started`, `sensors`, `workflows`, `project`, and
  `development`: maintained explanatory pages.
- `docs/tutorials/aviris3-walkthrough.md` and `caveats.md`: maintained interpretation.
- `scripts/generate.py`: source-derived reference and notebook renderer. Do not
  hand-edit generated API pages or notebook snapshots; the next build replaces them.
- `hooks.py`: resolves version and inventory placeholders from the generated manifest.
- `navigation.yml`: navigation structure; API/notebook items are inserted by generation.
- `mkdocs.yml`: theme/build settings; navigation and API plugin settings are generated.
- `docs/stylesheets/extra.css` and `overrides/partials/logo.html`: design/theme switching.
- `docs/assets/logos`: the website's own copies of the artwork, and the only
  ones it needs. The vector masters they were exported from are not
  distributed with the repository.

The compact rectangular wordmark switches in the header and homepage brand strip.
The full rectangular artwork appears on the About page, and both circular variants
are available in its downloads. All use Material's `data-md-color-scheme` state.
Outlined wordmark lettering needs no external font download; the full rectangular
taglines are editable SVG text with a system-font fallback.

The homepage layout lives in `overrides/main.html`; every page shares the
header in `overrides/partials/home-header.html`. Data, Tools, and Documentation
open dedicated landing pages, with the current category highlighted throughout
the site. The header displays the logo without a duplicate site-name label. The generated forest-and-mountain hero is
stored in `docs/assets/images/forest-mountain-hero.png`; it is an illustrative
landscape, not a processing output. The SVGs under `docs/assets/logos` are
exports; the masters they came from are kept outside the repository, so
changing the artwork means regenerating them rather than editing these in
place. Compact wordmark copies omit the taglines and use a tighter SVG
viewBox; the favicon uses the spectral-ribbon h alone.

## Evidence and pending details

Current version, API coverage, notebook counts, and figure counts are recorded in
`docs/assets/build-manifest.json` at build time. Saved output is historical evidence, not a fresh successful
run. Original docstrings are preserved, including grouped parameter descriptions;
Google-style parsing warnings for grouped names and missing types are disabled,
without suppressing build/link errors. The description layout avoids falsely
labeling grouped optional parameters as required; signatures remain authoritative
for individual defaults. No package source was edited to fix prose.

Package version, Python requirement, maintainer, repository, MIT license, and
citation now follow the adjacent package metadata. Remote publication, a release
DOI, institutional artwork approval, and independent scientific benchmarks are
not established by a documentation build. Original notebook downloads retain
local paths and saved output. This build is local only.


## Notebook changes and map previews

Save edits to the original notebooks in `../tests/0_src_code/`, rebuild with
`python manage.py build`, and refresh the tutorial page. For updated figures or
logs, rerun the relevant cells and save their output before rebuilding. The
static preview does not watch files or execute cells.

Map cells have browser-only zoomable previews. Saved widget state preserves supported geometry. The archive tutorial additionally
uses recorded metadata matched to its saved granule IDs to show result extents
and click details. Without either source, a saved center shows a labeled base-map
preview. These maps do not require a Jupyter service. Leaflet assets are local;
OpenStreetMap tiles require network access.

The entry pages use a numbered Data path, grouped processing stages for Tools,
and an introductory path plus reference directory for Documentation. Their
styles live in `docs/stylesheets/extra.css`; content links are blue and
underlined in light mode, with theme-aware colors in dark mode.

Navigation is grouped under Home, Data, Tools, Documentation, and About. Detail
pages retain the section's sibling links; header categories and breadcrumbs
come from the same navigation tree. Breadcrumbs use
`overrides/partials/page-location.html`, with a phone section-browser control.
API and notebook navigation is inserted recursively by `scripts/generate.py`.
