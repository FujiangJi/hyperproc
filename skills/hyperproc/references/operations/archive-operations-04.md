## Map environments

`hp.search_map(results=hits)` is an ipyleaflet/ipywidgets UI in a compatible Jupyter kernel with `search-map` extra. Footprints/quicklooks depend on saved geometries/provider availability. `m.selected` selects records; downloading remains a separate action. Do not promise the widget works in plain terminal Python or the static docs.

The website can show saved Leaflet footprints and pan/zoom without running archive Python. It cannot edit/run a whole notebook merely because a map is interactive. An AI without notebook rendering can use API search/selection instead of forcing a browser.

Exact references: [archive API](../api/hyperproc-archive-api.md), [CMR](../api/hyperproc-archive-cmr.md), [NEON](../api/hyperproc-archive-neon.md), [DLR](../api/hyperproc-archive-dlr.md), [interactive maps](../api/hyperproc-archive-interactive.md), [published data access](https://fujiangji.github.io/hyperproc/getting-started/data-access/), [search workflow](https://fujiangji.github.io/hyperproc/workflows/search/).
