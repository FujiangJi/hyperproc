# Maintaining this documentation

The site uses Material for MkDocs. It is local-only; no public hosting, analytics, credentials, or remote notebook execution is configured.

## Source layout

```text
docs-site/
├── docs/                   Human-written guides and generated reference/tutorials
├── hooks.py                Snapshot labels and concise tutorial tables of contents
├── navigation.yml          Maintained section order
├── mkdocs.yml              Theme, extensions, generated full navigation
├── overrides/              Shared header, breadcrumbs, homepage, and logo templates
├── scripts/generate.py     Static API inventory and notebook conversion
├── scripts/check_site.py   Built HTML/link/asset checks
├── manage.py               Generate, build, check, and local serve commands
├── requirements.txt        Documentation dependencies
└── site/                   Generated website; no scientific processing results
```

## Build from a clean docs environment

Use Python 3.11 or newer (matching the declared package minimum); a Python 3.12 processing environment also works. From `docs-site/`, install the documentation requirements in a dedicated environment, then run:

```bash
python -m pip install -r requirements.txt
python manage.py build
python manage.py check
python manage.py serve --port 8765
```

`serve` displays the already-built site at localhost. It does not execute notebooks or expose the repository's data directory. Stop it with Ctrl+C. The built site can also be served with Python's standard `http.server` without MkDocs installed.

## Edit the right source

- Edit conceptual/usage pages directly in `docs/`.
- Edit navigation in `navigation.yml`; its five primary sections match the shared header. The generator inserts API modules and the notebook library recursively into Documentation. Each section retains its sibling-guide sidebar on detail pages; header highlighting and breadcrumbs derive from the same navigation ancestry.
- API descriptions come from package docstrings and signatures. The docs build does not rewrite those source files.
- Notebook pages come from `tests/0_src_code/`; keep caveat annotations in the maintained companion guides. Edit a notebook only as a separate intentional development action.
- Logos live under `docs/assets/logos/`; `.theme-light` and `.theme-dark` variants respond to Material's current color scheme.
- The artwork under `docs/assets/logos` is what the site uses, and a clone needs nothing else to build; the vector masters it was exported from are not distributed. The homepage hero uses `overrides/main.html`; all pages share the header in `overrides/partials/home-header.html`. Data, Tools, and Documentation have landing pages with category highlighting in the header; its local image is `docs/assets/images/forest-mountain-hero.png`.

## What generation does

The generator uses Python AST to inventory modules/exports, writes reference directives for static mkdocstrings extraction, converts notebook markdown/code, copies original notebooks, and extracts stored PNG figures. Saved text outputs are expanded by default and can be collapsed. Long text outputs are shortened in the page but preserved in the download. Search-map cells receive browser-only Leaflet previews from saved widget geometry or, when geometry is missing, the saved center with an explicit caption. Vendored Leaflet assets supply pan/zoom controls; no kernel is started. It never imports hyperproc, executes notebook cells, or accesses remote data services.

The source-hash manifest and notebook inventories under `docs/assets/` make the documented snapshot explicit. Regenerate after source changes. Human-written scientific explanations still need review; automatic extraction cannot detect every stale docstring.

The build also checks public class methods/properties and uses
`scripts/audit_guides.py` to parse maintained Python examples, resolve package
aliases, bind calls against source signatures, and verify installation extras.
These checks never import hyperproc or execute example code. The dependency
table and citation date come directly from `pyproject.toml` and `CITATION.cff`;
the source-hash manifest includes the package README, maintained guides,
templates, styles, scripts, and source artwork so documentation checks detect
a changed input snapshot. Run `python manage.py build` after revisions;
`python manage.py check` reports stale build inputs instead of silently treating
old rendered pages as current.

## Before public release

Review data/image redistribution, institutional artwork approval, dependency support, and the release destination. License, maintainer, repository, and citation are recorded in the project metadata. Review local paths in archived output and whether downloaded notebooks are appropriate for public sharing. Public deployment is a separate action, not part of this local build.


## Updating tutorials after notebook edits

The source of each generated tutorial is its saved notebook in `tests/0_src_code/`. Save notebook edits, run `python manage.py build` from `docs-site/`, and refresh the browser. Code and Markdown update from saved cells; figures, maps, and logs update from saved outputs/widget state. Rerun and save cells when changing their results. The static preview does not watch source files.

Tutorial sidebar navigation is filtered by `hooks.py` at build time. Notebook tutorials show main sections and steps (generated H2/H3); function signatures and smaller H4 subsections stay in the body with their original anchors. The introductory section is labeled “Overview”, and notebooks with a single introductory parent display their steps without an extra nesting level. Maintained tutorial guides show their H2 sections. Other documentation sections keep their existing navigation. This rule also applies after notebook edits and regeneration.

Map extraction lives in `scripts/notebook_maps.py`. Its regression checks run with `python scripts/test_notebook_maps.py`. Leaflet 1.9.4 and its license are vendored under `docs/assets/vendor/leaflet/`; map tiles load from OpenStreetMap. Map snapshots are written under `docs/assets/notebook-maps/` and included in local-reference checks.

## Recording granule extents

The search/download tutorial's truncated widget outputs do not contain its granule extents. `scripts/record_granule_maps.py` explicitly retrieves provider metadata, matches saved granule identifier prefixes and acquisition minutes, and stores only matching granules under `map-recordings/search_download_tutorial/`. Ambiguous or missing matches fail rather than silently drawing other search results. This metadata action is separate from the static build and never downloads scene files or executes notebook cells.

Run it with a processing interpreter containing the search extra when a changed saved result table needs a new recording:

```bash
/path/to/processing/python scripts/record_granule_maps.py
python manage.py build
```

The record key includes the saved result rows and map-cell source, preventing old records from attaching to changed cells. The build manifest records recording hashes. Geometry is shown as granule bounding boxes, consistent with the package's notebook map; NEON site-month records have point locations, not flightline polygons. `python scripts/test_granule_recordings.py` checks record matching and invalidation.
