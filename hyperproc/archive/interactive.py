"""Draw a box on a map, search it, click the footprints you want.

    >>> import hyperproc as hp
    >>> m = hp.search_map()      # displays; draw a rectangle with the toolbar
    >>> m                        # in Jupyter the map is the cell output
    >>> m.search("EMIT", "L2A", date=("2023-04-01", "2023-04-30"))
    >>> m.selected               # what you clicked
    >>> hp.download(m.selected, "data/")

Everything the panel does is a method you can call instead, and everything a
method does the panel can do, so a notebook can start by pointing and end by
scripting. The map needs ``ipyleaflet``::

    pip install 'hyperproc[search-map]'

The logic underneath - which box, which granules, which of them are selected -
is :class:`SearchState`, which needs no widgets at all.
"""
from __future__ import annotations

import math

from hyperproc.archive.api import search as _search
from hyperproc.archive.collections import COLLECTIONS, resolve
from hyperproc.archive.results import Granule, Results

def has_cloud(sensor: str, level: str | None = None) -> bool:
    """Does this collection publish a cloud fraction?

    Read from the collection table rather than kept as a second list, because
    it is not a property of the sensor: PACE reports one at L2 and none at
    L1B. Offering the slider where there is none would silently drop every
    granule, which is how a working search looks broken.
    """
    if level is not None:
        return resolve(sensor, level)[2].cloud
    return any(c.cloud for (s, _), c in COLLECTIONS.items() if s == sensor.upper())

#: Footprint colours: what a search returned, and what you picked out of it.
FOUND = "#3388ff"
PICKED = "#ff7800"


def sensors() -> dict[str, list[str]]:
    """``{sensor: [levels]}`` for everything searchable, for a dropdown."""
    out: dict[str, list[str]] = {}
    for sensor, level in sorted(COLLECTIONS):
        out.setdefault(sensor, []).append(level)
    return out


class SearchState:
    """The part of the map that is not a map: a box, a result set, a selection.

    Attributes:
        bbox: ``(west, south, east, north)`` of the drawn rectangle, or ``None``.
        results: the last :class:`~hyperproc.archive.results.Results`.
        selected: the granules picked out of it, in the order they were picked.
    """

    def __init__(self, bbox=None):
        self.bbox = tuple(bbox) if bbox else None
        self.results = Results([])
        self.selected: list[Granule] = []

    # -- the box ----------------------------------------------------------
    def set_bbox_from_geojson(self, geometry: dict) -> tuple:
        """Take the bounds of a drawn shape, whatever shape it is.

        The draw toolbar can produce a rectangle, a polygon or a circle marker;
        a search takes a box, so the bounds of whatever was drawn is the honest
        reading of the gesture.
        """
        coords = _flatten(geometry.get("coordinates", []))
        if not coords:
            raise ValueError("nothing was drawn")
        lon = [c[0] for c in coords]
        lat = [c[1] for c in coords]
        self.bbox = (min(lon), min(lat), max(lon), max(lat))
        return self.bbox

    # -- the search -------------------------------------------------------
    def search(self, sensor: str, level: str | None = None, **kwargs) -> Results:
        """Search the drawn box. Selection is cleared, since it named old granules."""
        if "bbox" not in kwargs:
            if self.bbox is None:
                raise ValueError(
                    "no area chosen - draw a rectangle on the map, or pass "
                    "bbox=(west, south, east, north)")
            kwargs["bbox"] = self.bbox
        # the backend raises for this too; catching it here keeps the panel's
        # disabled slider and the method in step with one another
        self.results = _search(sensor, level, **kwargs)
        self.selected = []
        return self.results

    # -- the selection ----------------------------------------------------
    def toggle(self, name: str) -> bool:
        """Pick a granule by name, or unpick it. Returns whether it is now picked."""
        for i, g in enumerate(self.selected):
            if g.name == name:
                del self.selected[i]
                return False
        for g in self.results:
            if g.name == name:
                self.selected.append(g)
                return True
        raise KeyError(f"{name} is not in the last search")

    def select_all(self) -> list[Granule]:
        self.selected = list(self.results)
        return self.selected

    def clear(self) -> None:
        self.selected = []

    # -- what a map draws -------------------------------------------------
    def geojson(self) -> dict:
        """The footprints as a FeatureCollection, ready for a map layer.

        A footprint with no area - NEON publishes a site's coordinates, not its
        flight box - comes out as a Point rather than a zero-width polygon, so
        it is visible instead of invisible.
        """
        picked = {g.name for g in self.selected}
        feats = []
        for g in self.results:
            if g.bbox is None:
                continue
            w, s, e, n = g.bbox
            geom = ({"type": "Point", "coordinates": [w, s]} if (w == e and s == n)
                    else {"type": "Polygon", "coordinates": [[
                        [w, s], [e, s], [e, n], [w, n], [w, s]]]})
            feats.append({
                "type": "Feature", "id": g.name, "geometry": geom,
                "properties": {
                    "name": g.name, "sensor": g.sensor, "level": g.level,
                    "time": g.time.isoformat(sep=" ", timespec="minutes") if g.time else None,
                    "cloud": g.cloud, "size_mb": g.size_mb,
                    "browse": g.browse,
                    "selected": g.name in picked,
                    "color": PICKED if g.name in picked else FOUND,
                },
            })
        return {"type": "FeatureCollection", "features": feats}

    def bounds(self) -> tuple[float, float, float, float] | None:
        """``(west, south, east, north)`` covering every footprint, for a zoom."""
        boxes = [g.bbox for g in self.results if g.bbox is not None]
        if not boxes:
            return self.bbox
        return (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))

    def summary(self) -> str:
        """One line for a status bar."""
        if self.bbox is not None:
            where = "bbox " + ", ".join(f"{v:.3f}" for v in self.bbox)
        elif len(self.results):
            # handed a result set rather than given a box; say what is on screen
            where = "extent " + ", ".join(f"{v:.2f}" for v in self.bounds())
        else:
            where = "no area chosen"
        return f"{where} | {self.results!r} | {len(self.selected)} selected"

    def __repr__(self) -> str:
        return f"<SearchState {self.summary()}>"


def zoom_for(bounds, width_px: int = 900, height_px: int = 500) -> int:
    """The web-Mercator zoom at which ``bounds`` fills a map that size.

    ``ipyleaflet.Map.fit_bounds`` sends a message to the browser, so it does
    nothing when there is no browser - which is every notebook executed by
    nbconvert. The map is then saved at whatever it was constructed with, and
    opens on the wrong continent. Computing the zoom here instead puts it in
    the widget's own state, where it survives saving.
    """
    w, s_, e, n = bounds
    span_lon = max(abs(e - w), 1e-6)
    # latitude spans less screen per degree away from the equator
    mid = math.radians(max(-85.0, min(85.0, (s_ + n) / 2)))
    span_lat = max(abs(n - s_), 1e-6) / max(0.02, math.cos(mid))
    by_lon = math.log2(360.0 * width_px / (256.0 * span_lon))
    by_lat = math.log2(360.0 * height_px / (256.0 * span_lat))
    return int(max(1, min(18, math.floor(min(by_lon, by_lat)))))


def _flatten(coords) -> list:
    """Every ``[lon, lat]`` pair in an arbitrarily nested coordinate array."""
    if (isinstance(coords, (list, tuple)) and len(coords) >= 2
            and all(isinstance(v, (int, float)) for v in coords[:2])):
        return [coords]
    out = []
    for c in coords if isinstance(coords, (list, tuple)) else []:
        out += _flatten(c)
    return out


# --------------------------------------------------------------------------- #
# the map itself                                                              #
# --------------------------------------------------------------------------- #

def _px(css: str, default: int) -> int:
    """``"420px"`` -> ``420``. Anything else keeps the default."""
    try:
        return int(str(css).strip().lower().removesuffix("px"))
    except ValueError:
        return default


def _widgets():
    try:
        import ipyleaflet
        import ipywidgets
    except ImportError as exc:                     # pragma: no cover - environment
        raise ImportError(
            "the search map needs ipyleaflet and ipywidgets:\n"
            "    pip install 'hyperproc[search-map]'\n"
            "Everything it does is also a plain function - hyperproc.search, "
            "hyperproc.download - which need neither."
        ) from exc
    return ipyleaflet, ipywidgets


class Map:
    """A slippy map with a draw tool, a search panel and clickable footprints.

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
    """

    def __init__(self, center=(20.0, 0.0), zoom: int = 2, height: str = "600px",
                 bbox=None, results=None):
        leaflet, widgets = _widgets()
        self._leaflet, self._w = leaflet, widgets
        self.state = SearchState(bbox)
        self._layer = None
        self._height_px = _px(height, 600)
        self._width_px = 900          # the widget is responsive; this is a fair guess

        self.map = leaflet.Map(center=center, zoom=zoom, scroll_wheel_zoom=True,
                               layout=widgets.Layout(height=height, flex="1 1 auto"))
        self.map.add(leaflet.LayersControl(position="topleft"))
        self.map.add(leaflet.FullScreenControl())

        self.draw = leaflet.DrawControl(
            rectangle={"shapeOptions": {"color": "#00a0a0", "fillOpacity": 0.05}},
            polygon={}, circle={}, circlemarker={}, polyline={}, marker={},
            edit=False, remove=True)
        self.draw.on_draw(self._drawn)
        self.map.add(self.draw)

        self._panel = self._build_panel()
        # Beside the map, not inside it. A leaflet WidgetControl is a floating
        # overlay sized by its own CSS, and a front end that clips it rather
        # than scrolling it simply loses whatever does not fit - which is how
        # the download button disappeared under VS Code. An HBox is ordinary
        # widget layout that every front end handles the same way.
        self.map.layout.width = "100%"
        self.widget = widgets.HBox(
            [self.map, self._panel],
            layout=widgets.Layout(width="100%", align_items="flex-start"))
        if bbox:
            self._show_bbox()
        if results is not None:
            self.show(results)

    # -- read-through ------------------------------------------------------
    @property
    def bbox(self):
        return self.state.bbox

    @property
    def results(self) -> Results:
        return self.state.results

    @property
    def selected(self) -> list[Granule]:
        return self.state.selected

    def _ipython_display_(self):                   # pragma: no cover - notebook
        from IPython.display import display
        display(self.widget)

    def __repr__(self) -> str:
        return f"<hyperproc search map: {self.state.summary()}>"

    # -- the panel ---------------------------------------------------------
    def _build_panel(self):
        w = self._w
        table = sensors()
        self.w_sensor = w.Dropdown(options=list(table), value="EMIT",
                                   description="sensor", layout=w.Layout(width="260px"))
        self.w_level = w.Dropdown(options=table["EMIT"], value="L2A",
                                  description="level", layout=w.Layout(width="260px"))
        self.w_start = w.Text(value="", placeholder="YYYY-MM-DD", description="from",
                              layout=w.Layout(width="260px"))
        self.w_end = w.Text(value="", placeholder="YYYY-MM-DD", description="to",
                            layout=w.Layout(width="260px"))
        self.w_cloud = w.IntRangeSlider(value=(0, 100), min=0, max=100, step=5,
                                        description="cloud %", continuous_update=False,
                                        layout=w.Layout(width="260px"))
        self.w_count = w.BoundedIntText(value=50, min=1, max=2000, step=10,
                                        description="max", layout=w.Layout(width="260px"))
        self.w_go = w.Button(description="Search", button_style="primary",
                             icon="search", layout=w.Layout(width="120px"))
        self.w_all = w.Button(description="Select all", layout=w.Layout(width="135px"))
        self.w_list = w.SelectMultiple(options=[], rows=8,
                                       layout=w.Layout(width="260px"))
        self.w_out = w.Text(value="data", description="into",
                            layout=w.Layout(width="260px"))
        self.w_get = w.Button(description="Download selected", icon="download",
                              button_style="success",
                              layout=w.Layout(width="260px", height="32px"))
        self.w_status = w.HTML(value=self._status_html())
        self.w_preview = w.HTML(value="")

        self.w_sensor.observe(self._sensor_changed, names="value")
        self.w_level.observe(self._sensor_changed, names="value")
        self.w_go.on_click(lambda _b: self.search())
        self.w_all.on_click(lambda _b: self._select_all())
        self.w_list.observe(self._list_changed, names="value")
        self.w_get.on_click(lambda _b: self.download())
        self._sensor_changed()

        # Every control that does something sits above everything whose height
        # varies. The panel scrolls, and the granule list and the quicklook both
        # grow with what you searched and clicked, so a button placed after them
        # slides out of view exactly when you want it.
        return w.VBox([self.w_sensor, self.w_level, self.w_start, self.w_end,
                       self.w_cloud, self.w_count,
                       w.HBox([self.w_go, self.w_all]),
                       self.w_out, self.w_get,
                       self.w_status, self.w_list, self.w_preview],
                      layout=w.Layout(padding="6px 8px", width="300px",
                                      flex="0 0 300px", overflow="auto",
                                      border_left="1px solid #ddd",
                                      max_height=f"{self._height_px}px"))

    def _sensor_changed(self, _change=None):
        table = sensors()
        levels = table[self.w_sensor.value]
        self.w_level.options = levels
        if self.w_level.value not in levels:
            self.w_level.value = levels[-1]
        ok = has_cloud(self.w_sensor.value, self.w_level.value)
        self.w_cloud.disabled = not ok
        self.w_cloud.description = "cloud %" if ok else "no cloud"

    def _status_html(self, extra: str = "") -> str:
        return f"<small>{self.state.summary()}{'<br>' + extra if extra else ''}</small>"

    def _say(self, extra: str = "") -> None:
        self.w_status.value = self._status_html(extra)

    # -- events ------------------------------------------------------------
    def _drawn(self, _control, action, geo_json):
        if action != "created":
            return
        self.state.set_bbox_from_geojson(geo_json["geometry"])
        self._say()

    def _show_bbox(self):
        w, s, e, n = self.state.bbox
        self.map.add(self._leaflet.Rectangle(
            bounds=((s, w), (n, e)), color="#00a0a0", fill_opacity=0.05, weight=2))

    def _list_changed(self, _change=None):
        chosen = set(self.w_list.value)
        self.state.selected = [g for g in self.state.results if g.name in chosen]
        if self.state.selected:
            g = self.state.selected[-1]
            self._preview({"browse": g.browse, "sensor": g.sensor})
        self._redraw()

    def _select_all(self):
        self.state.select_all()
        self.w_list.value = tuple(g.name for g in self.state.selected)
        self._redraw()

    def _hovered(self, feature=None, **_kw):
        """Name the footprint under the pointer, the way a listing would."""
        if not feature:
            return
        p = feature["properties"]
        bits = [p["name"], p["time"] or "unknown time"]
        if p["cloud"] is not None:
            bits.append(f"{p['cloud']:.0f}% cloud")
        if p["size_mb"] is not None:
            bits.append(f"{p['size_mb']:,.0f} MB")
        self._say("<b>" + bits[0] + "</b><br>" + "  |  ".join(bits[1:]))

    def preview_html(self, props: dict) -> str:
        """The quicklook for one footprint, as a scrap of HTML.

        The ``onerror`` fallback matters: CMR lists a browse image for every
        PACE granule and none of them were ever written, so the URL is there
        and 404s. A broken-image icon says less than a sentence does.
        """
        url = props.get("browse")
        if not url:
            return (f"<small><i>no public quicklook for {props.get('sensor', 'this')}"
                    f"</i></small>")
        fallback = ("&lt;small&gt;&lt;i&gt;the archive lists a quicklook here, "
                    "but it is missing&lt;/i&gt;&lt;/small&gt;")
        onerror = "this.parentNode.innerHTML = '" + fallback + "'"
        return (f'<a href="{url}" target="_blank" title="open the full-size image">'
                f'<img src="{url}" alt="quicklook" '
                f'style="max-width:100%;max-height:150px;display:block;'
                f'margin-top:4px;border:1px solid #ccc" '
                f'onerror="{onerror}"></a>'
                f'<small><i>click to open full size</i></small>')

    def _preview(self, props: dict) -> None:
        self.w_preview.value = self.preview_html(props)

    def _clicked(self, feature=None, **_kw):
        if not feature:
            return
        self._preview(feature["properties"])
        name = feature.get("id") or feature["properties"]["name"]
        self.state.toggle(name)
        self.w_list.unobserve(self._list_changed, names="value")
        self.w_list.value = tuple(g.name for g in self.state.selected)
        self.w_list.observe(self._list_changed, names="value")
        self._redraw()

    # -- actions -----------------------------------------------------------
    def search(self, sensor: str | None = None, level: str | None = None, **kwargs):
        """Search the drawn box. With no arguments, uses the panel's settings.

        Returns the :class:`~hyperproc.archive.results.Results`, and draws the
        footprints on the map.
        """
        if sensor is None:
            sensor, level = self.w_sensor.value, self.w_level.value
            kwargs.setdefault("count", int(self.w_count.value))
            a, b = self.w_start.value.strip(), self.w_end.value.strip()
            if a and b:
                kwargs.setdefault("date", (a, b))
            elif a or b:
                kwargs.setdefault("date", a or b)
            lo, hi = self.w_cloud.value
            if not self.w_cloud.disabled and (lo, hi) != (0, 100):
                kwargs.setdefault("cloud", (lo, hi))
        kwargs.setdefault("verbose", False)
        self._say("searching...")
        try:
            res = self.state.search(sensor, level, **kwargs)
        except Exception as exc:
            self.w_list.options = []
            self._say(f"<span style='color:#c00'>{type(exc).__name__}: {exc}</span>")
            raise
        self._apply(res)
        return res

    def show(self, results, fit: bool = True):
        """Draw a result set you already have, without searching again.

        Args:
            results: a :class:`~hyperproc.archive.results.Results`, or a list
                of granules.
            fit: zoom to the footprints. ``False`` leaves the view alone.

        Returns the results, so it chains.
        """
        if not isinstance(results, Results):
            results = Results(list(results))
        self.state.results = results
        self.state.selected = []
        self._apply(results)
        if fit:
            self.fit()
        return results

    def fit(self) -> None:
        """Centre and zoom on the footprints, or on the drawn box if there are none.

        Sets ``center`` and ``zoom`` rather than only calling ``fit_bounds``:
        those are traits, so they are saved with the notebook and the map opens
        on the data when the file is reopened without a kernel. ``fit_bounds``
        is still called, because a live browser refines the fit.
        """
        box = self.state.bounds()
        if box is None:
            return
        w, s_, e, n = box
        pad = max(0.02, 0.05 * max(e - w, n - s_))
        w, s_, e, n = w - pad, s_ - pad, e + pad, n + pad
        self.map.center = ((s_ + n) / 2, (w + e) / 2)
        self.map.zoom = zoom_for((w, s_, e, n), self._width_px, self._height_px)
        try:
            self.map.fit_bounds([[s_, w], [n, e]])
        except Exception:      # no front end attached; center/zoom already did it
            pass

    def _apply(self, res) -> None:
        """Put a result set into the list, the map and the status line."""
        self.w_list.unobserve(self._list_changed, names="value")
        self.w_list.options = [g.name for g in res]
        self.w_list.value = ()
        self.w_list.observe(self._list_changed, names="value")
        self.w_preview.value = ""
        self._redraw()
        self._say(res.note if not res
                  else "click a footprint to select it and see its quicklook")

    def _redraw(self):
        leaflet = self._leaflet
        if self._layer is not None:
            self.map.remove(self._layer)
            self._layer = None
        data = self.state.geojson()
        if not data["features"]:
            self._say()
            return
        self._layer = leaflet.GeoJSON(
            data=data, name="footprints",
            style={"weight": 1, "fillOpacity": 0.15},
            hover_style={"weight": 3, "fillOpacity": 0.35},
            point_style={"radius": 6, "fillOpacity": 0.7},
            style_callback=lambda f: {"color": f["properties"]["color"],
                                      "fillColor": f["properties"]["color"]})
        self._layer.on_click(self._clicked)
        self._layer.on_hover(self._hovered)
        self.map.add(self._layer)
        # the summary already ends with "n selected"; saying it twice just
        # pushed the panel's own controls further down
        self._say()

    def download(self, out_dir: str | None = None, **kwargs):
        """Download the selected granules. Same as ``hp.download(m.selected, ...)``.

        Credentials come from the environment exactly as they do there; nothing
        is typed into the map.
        """
        from hyperproc.archive.api import download as _download
        if not self.state.selected:
            self._say("nothing selected")
            return []
        out = out_dir or self.w_out.value or "data"
        self._say(f"downloading {len(self.state.selected)} to {out} ...")
        try:
            paths = _download(self.state.selected, out, **kwargs)
        except Exception as exc:
            self._say(f"<span style='color:#c00'>{type(exc).__name__}: {exc}</span>")
            raise
        self._say(f"{len(paths)} files in {out}")
        return paths


def search_map(**kwargs) -> Map:
    """A :class:`Map`, ready to draw on. See :class:`Map` for the arguments."""
    return Map(**kwargs)
