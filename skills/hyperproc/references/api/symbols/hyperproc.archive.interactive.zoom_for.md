# hyperproc.archive.interactive.zoom_for

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def zoom_for(bounds, width_px: int=900, height_px: int=500) -> int
```

The web-Mercator zoom at which ``bounds`` fills a map that size.

``ipyleaflet.Map.fit_bounds`` sends a message to the browser, so it does
nothing when there is no browser - which is every notebook executed by
nbconvert. The map is then saved at whatever it was constructed with, and
opens on the wrong continent. Computing the zoom here instead puts it in
the widget's own state, where it survives saving.

[Module and aliases](../hyperproc-archive-interactive.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.interactive.zoom_for --runtime`.
