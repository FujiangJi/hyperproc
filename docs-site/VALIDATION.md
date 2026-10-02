# Local website verification

This report covers the documentation update for the current hyperproc 0.1.0
checkout. Package source and original tutorial notebooks were not edited by this update. The current rectangular and circular logo masters and website copies omit the affiliation footer. The static build does not execute notebooks.

## Automated checks — passed

- MkDocs 1.6.1 strict build using the pinned documentation requirements.
- 117 generated HTML pages, including the 404 page and the PACE migration notice.
- 50,051 local link, asset, and fragment references checked; external URLs excluded.
- All 459 indexed top-level functions/classes rendered across 53 source modules.
- All 17 current downloadable notebooks match their originals byte-for-byte.
- Package module inventory and source hashes match the generation manifest.
- Package metadata hashes and copied LICENSE/CITATION.cff match their originals.
- 147 stored notebook PNG figures extracted; cells were not rerun.
- Version/count placeholders resolve in rendered pages.
- Optional search_map/Map exports link to their source-derived definitions.
- All 1,051 Saved output blocks across 17 tutorials render expanded by default.
- All 21 tutorial tables of contents show main sections only. All main notebook steps remain linked; detailed function headings retain their body anchors without cluttering the sidebar. Single-parent notebooks display steps without the redundant introduction nesting.
- All 14 archived search-map cells render matched saved granule extents: 109 granule entries in total. Provider metadata recordings are bound to saved result identifiers and acquisition minutes, and their hashes are verified by the build.
- Four map-extraction tests and two granule-recording tests pass. Map-extraction cases: saved center, matching widget view and polygon, cyclic widget references, and invalid/executable coordinate input.
- All package modules parse with Python 3.11 grammar, matching requires-python.
- All 43 Python examples in the maintained guide sections parse successfully.
- Rectangular/circular light/dark website SVGs match their v2 design masters.

## Map preview browser checks — passed

- All 14 map-cell previews appear in the static tutorial.
- Zoom-in changes the displayed tile level; drag pans; reset restores the initial view.
- Controls remain usable at a 390 px phone width without page-wide overflow.
- OpenStreetMap tiles render; no notebook iframe or Jupyter service is needed.
- The search/download maps draw cached bounding boxes for the granules listed in the saved output. The first map shows five selectable EMIT extents and matching popup details; overlapping scenes are individually selectable on phone widths. NEON site/month entries render as points with their delivery details.

## Browser evidence

The homepage installation box appears immediately below the introduction and
before the Python usage example. It lists five pip install commands and three
atmospheric-asset setup commands, with the theme's copy-to-clipboard control.
Desktop and 390 px phone layouts were checked without horizontal page overflow.

The tutorial TOC update was checked in Chromium across all 21 tutorial pages.
All main steps in the 17 notebook tutorials remain linked, function-detail
anchors still resolve, and the search/download sidebar has 20 entries.
At 390 px width, the mobile drawer opens the simplified TOC without horizontal
page overflow. Its 14 map previews and expanded saved outputs remain present.

The homepage and About page serve the updated light and dark rectangular logo
SVGs without the GCRL/University of Wisconsin–Madison footer or its divider.
The package name and purpose caption remain present. Both 1440 × 480 PNG exports
were refreshed from the revised vector masters.
The rectangular text block sits 12 SVG pixels below the emblem's vertical center
in both themes, matching the requested downward refinement (verified within 0.05 px). Circular
masters and header copies omit the bottom affiliation arc; their light and
dark PNG exports were refreshed at their original dimensions.

The prior site's report recorded desktop/mobile layout, theme switching, search,
API, and figure checks. Those original layout checks were not repeated exhaustively for the static documentation update. The existing CSS, logo template, and SVG masters were retained. Current
link/asset checks validate the rebuilt output, including the archive workflow,
archive API section, and search/download notebook.

## Evidence limits and package finding

Static-site checks do not execute notebook cells, processing algorithms, atmospheric retrievals, archive searches, or scene downloads. A separate metadata-recording action queried the anonymous archives to match saved result identifiers; subsequent website builds use those local records offline. They do not establish
PyPI publication, a remote release tag, independent scientific validation, or
institutional approval of the artwork.

The current pyproject.toml explicitly lists packages but omits hyperproc.archive.
A built wheel needs that package included to provide the new archive API. This
website update leaves the package source and packaging metadata untouched.

Original notebook downloads retain saved output and local paths. Public hosting
requires review of those artifacts and provider-data usage terms.

## Reproduce

From the repository root:

```bash
docs-site/.venv/bin/python docs-site/manage.py build
```

To preview the built site:

```bash
docs-site/.venv/bin/python docs-site/manage.py serve
```

Open http://127.0.0.1:8765/. The server exposes the built site directory only.
