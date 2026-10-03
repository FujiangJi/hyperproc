# Local website verification

This report covers the documentation update for the current hyperproc 0.1.2
checkout. Package source and original tutorial notebooks were not edited by the homepage redesign. The website uses the v3 Spectral Ribbon logo family and a generated forest-and-mountain hero. The static build does not execute notebooks.

## 0.1.2 revision verification — passed

Current package and citation metadata agree on 0.1.2 and 2026-10-03.
126 relevant offline package regressions passed (3 deselected); full test
collection found 748 tests, without executing the full suite. Chromium checked
all 54 API module version labels, the new internal netCDF helper, current
source/guide behavior, installation constraints, release/citation dates,
and desktop/mobile layouts. Five guide-auditor tests passed. The detailed
review is [REVISION_REVIEW_0.1.2.md](REVISION_REVIEW_0.1.2.md).

The remaining visual/interaction evidence below includes checks from earlier
website updates; it does not imply that every old interaction test was rerun.

## Automated checks — passed

- MkDocs 1.6.1 strict build using the pinned documentation requirements.
- 121 generated HTML pages, including the 404 page and the PACE migration notice.
- 51,328 local link, asset, and fragment references checked; external URLs excluded.
- All 465 indexed top-level functions/classes and 68 public class methods/properties rendered across 54 source modules.
- All 17 current downloadable notebooks match their originals byte-for-byte.
- Package module inventory and source hashes match the generation manifest. Maintained guides, README/metadata, templates, styles, scripts, artwork, and vendored assets are also checked against the generation snapshot.
- Package metadata hashes and copied LICENSE/CITATION.cff match their originals.
- 147 stored notebook PNG figures extracted; cells were not rerun.
- Version/count placeholders resolve in rendered pages.
- Optional search_map/Map exports link to their source-derived definitions.
- All 1,051 Saved output blocks across 17 tutorials render expanded by default.
- All 21 tutorial tables of contents show main sections only. All main notebook steps remain linked; detailed function headings retain their body anchors without cluttering the sidebar. Single-parent notebooks display steps without the redundant introduction nesting.
- All 14 archived search-map cells render matched saved granule extents: 109 granule entries in total. Provider metadata recordings are bound to saved result identifiers and acquisition minutes, and their hashes are verified by the build.
- Four map-extraction tests and two granule-recording tests pass. Map-extraction cases: saved center, matching widget view and polygon, cyclic widget references, and invalid/executable coordinate input.
- All package modules parse with Python 3.11 grammar, matching requires-python.
- All 44 Python example blocks across 47 maintained guides parse successfully; 79 resolvable calls bind to current source signatures and named installation extras exist.
- Five example-auditor regression tests pass. A negative freshness check rejects a stale guide hash and restores the original generation manifest.
- Rectangular/circular light/dark website SVGs match their v3 design masters. Compact header wordmarks omit the tagline layer; the favicon uses the spectral-ribbon h.

## Persistent section navigation and location — passed

The navigation tree now matches the five header categories. Data keeps archive,
reading, and sensor links together; Tools retains all workflow siblings; the
Documentation tree contains installation, tutorials, API, background, and
developer guides. API/notebook entries populate nested sections during builds.
Header highlighting and breadcrumbs derive from the same tree, so a tutorial
is consistently under Documentation even when a Data page links to it.

Guide pages show Home / section / current page, with ancestor index links.
The desktop sidebar highlights the current guide and allows direct sibling
navigation. Phones have a Browse this section control for the navigation
panel. Chromium verified direct atmospheric-to-satellite workflow switching
on desktop and phone, returning via the Tools breadcrumb, and category/path
accuracy for archive, sensor, installation, tutorial, API, developer, and
About pages. Dark mode passed; no page-wide overflow or JavaScript errors.
Screenshots: `/tmp/hyperproc-wayfinding-tools-desktop.png` and
`/tmp/hyperproc-wayfinding-tools-phone.png`.

## Entry-page hierarchy and link visibility — passed

Light-mode content links use blue (#0866b3) and persistent underlines, including
homepage quick links. Keyboard focus is visible. Dark-mode links retain the
mint theme color. Data uses a numbered archive-to-dataset sequence; Tools uses
four processing-stage groups; Documentation highlights the three-step starting
path above a compact reference directory. These entry pages no longer use
identical per-feature cards.

Chromium checked the link styles, step/group counts, all entry-page destination
links, current-category indication, 1440 px desktop and 390 px phone layouts,
and the dark theme. No page-wide overflow or JavaScript errors were reported.
Screenshots are saved as `/tmp/hyperproc-home-clear-links.png` and
`/tmp/hyperproc-entry-{data,tools,documentation}-{desktop,phone}.png`.

## Shared navigation and logo alignment — passed

All pages use the same five-link header: Home, Data, Tools, Documentation, and
About. Data/Tools/Documentation open dedicated landing pages. Current
categories have an underline and an `aria-current` location; the old tab bar
and duplicate header site-name label are absent. The homepage brand image is
larger, with a 20 px gap; the text is offset 12 px below the geometric center on desktop for visual alignment.

Chromium checked all five header destinations, landing-page guide links,
category highlighting in sensor/workflow/API/developer pages, desktop and
390 px phone layouts, light/dark logos, desktop search results, phone search,
and the documentation drawer. No page-wide overflow or JavaScript errors.
Screenshots: `/tmp/hyperproc-navigation-home-desktop.png`,
`/tmp/hyperproc-navigation-architecture-desktop.png`,
`/tmp/hyperproc-navigation-home-phone.png`, and
`/tmp/hyperproc-navigation-tutorial-phone.png`.

## Previous 0.1.1 revision browser checks — passed

Chromium verified the version 0.1.1 label on all 53 API module pages, current source text for the four changed modules, the generated dependency table, citation/release dates, and the BRDF installation instruction in all 11 edited tutorials. API, installation, and home pages have no horizontal page overflow at 390 px; API was also checked at desktop width. No JavaScript errors were reported. The detailed findings are in [REVISION_REVIEW.md](REVISION_REVIEW.md).

The following map, TOC, and homepage interaction evidence comes from the preceding website updates; these interaction suites were not rerun for this package documentation review.

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

The homepage uses a compact wordmark header, five navigation links, a full-width
forest-and-mountain hero, and an Explore tools CTA to the processing decision
guide. Its horizontal brand strip uses the compact wordmark and live HTML
taglines. The About page and logo downloads use the new full rectangular and
circular artwork. All four master copies match the v3 SVGs byte-for-byte.

Chromium checks passed at 1440 px and 390 px widths: light/dark logos switch,
homepage links resolve, search returns results on desktop and opens on phone,
the CTA opens its destination, the documentation drawer works, installation
copy controls remain present, and there is no page-wide overflow or JavaScript
error. Screenshots record desktop light/dark and phone light layouts. The hero
image is a generated illustration of a forested mountain landscape, not a
satellite scene or processing output.

The prior site's report recorded desktop/mobile layout, theme switching, search,
API, and figure checks. Those original layout checks were not repeated exhaustively for every documentation page. The homepage CSS, template, and logo family were updated. Current
link/asset checks validate the rebuilt output, including the archive workflow,
archive API section, and search/download notebook.

## Evidence limits

Static-site checks do not execute notebook cells, processing algorithms, atmospheric retrievals, archive searches, or scene downloads. A separate metadata-recording action queried the anonymous archives to match saved result identifiers; subsequent website builds use those local records offline. They do not establish
PyPI publication, a remote release tag, independent scientific validation, or
institutional approval of the artwork.

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

## Restored GitHub repository header — passed

The shared header restores Material's repository widget, linking to
https://github.com/FujiangJi/hyperproc and displaying FujiangJi/hyperproc.
Desktop star/fork facts use Material's GitHub API integration; no counts are
hardcoded. Phones retain a compact GitHub icon link. Chromium verified header
links on home, Tools, and API pages, light/dark modes, and 1440/1024/768/390/360
px widths without page overflow. Fact rendering was tested using browser-only
API fixtures, not claims about current repository counts.
