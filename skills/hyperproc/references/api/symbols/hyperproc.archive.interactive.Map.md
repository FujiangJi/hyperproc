# hyperproc.archive.interactive.Map

Release baseline **0.1.2**. Fields and declared members below come from the release source. Dataclass/inherited methods may be generated at runtime; inspect the installed class signature when constructing it.

A slippy map with a draw tool, a search panel and clickable footprints.

Args:
    center: ``(lat, lon)`` to open at.
    zoom: starting zoom.
    height: CSS height of the map.
    bbox: start with an area already chosen, instead of drawing one.
    results: footprints to draw straight away, from a search you have
        already run. Saves searching twice when you want to look at a
        result set you are holding.

Attributes:
    state: the :class:`SearchState` underneath.
    map: the raw ``ipyleaflet.Map``, for adding your own layers.
    widget: what is displayed - the map and the panel side by side. Show
        ``m.map`` instead for the map alone.

``bbox``, ``results`` and ``selected`` read through to the state, so
``hp.download(m.selected, "data/")`` works straight from the map.

## Declared members

- [__init__](hyperproc.archive.interactive.Map.__init__.md)
- [bbox](hyperproc.archive.interactive.Map.bbox.md)
- [results](hyperproc.archive.interactive.Map.results.md)
- [selected](hyperproc.archive.interactive.Map.selected.md)
- [_ipython_display_](hyperproc.archive.interactive.Map._ipython_display_.md)
- [__repr__](hyperproc.archive.interactive.Map.__repr__.md)
- [_build_panel](hyperproc.archive.interactive.Map._build_panel.md)
- [_sensor_changed](hyperproc.archive.interactive.Map._sensor_changed.md)
- [_status_html](hyperproc.archive.interactive.Map._status_html.md)
- [_say](hyperproc.archive.interactive.Map._say.md)
- [_drawn](hyperproc.archive.interactive.Map._drawn.md)
- [_show_bbox](hyperproc.archive.interactive.Map._show_bbox.md)
- [_list_changed](hyperproc.archive.interactive.Map._list_changed.md)
- [_select_all](hyperproc.archive.interactive.Map._select_all.md)
- [_hovered](hyperproc.archive.interactive.Map._hovered.md)
- [preview_html](hyperproc.archive.interactive.Map.preview_html.md)
- [_preview](hyperproc.archive.interactive.Map._preview.md)
- [_clicked](hyperproc.archive.interactive.Map._clicked.md)
- [search](hyperproc.archive.interactive.Map.search.md)
- [show](hyperproc.archive.interactive.Map.show.md)
- [fit](hyperproc.archive.interactive.Map.fit.md)
- [_apply](hyperproc.archive.interactive.Map._apply.md)
- [_redraw](hyperproc.archive.interactive.Map._redraw.md)
- [download](hyperproc.archive.interactive.Map.download.md)

[Module](../hyperproc-archive-interactive.md).
