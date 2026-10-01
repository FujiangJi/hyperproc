"""hyperproc.archive.interactive - the draw-a-box search map.

The map is two things stacked: :class:`SearchState`, which is a box, a result
set and a selection and needs nothing installed, and :class:`Map`, which is
that plus ipyleaflet widgets. Most of what can go wrong lives in the first, so
most of the tests do too and run everywhere; the widget tests skip when
ipyleaflet is absent.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from hyperproc.archive.interactive import (FOUND, PICKED, SearchState, _flatten,
                                           has_cloud, sensors)
from hyperproc.archive.results import Granule, Results


def _granule(name, bbox, sensor="EMIT", level="L2A", cloud=10.0, size=100.0):
    return Granule(name=name, sensor=sensor, level=level, collection="X",
                   version="001", time=datetime(2023, 4, 1, 12), bbox=bbox,
                   size_mb=size, cloud=cloud, links=[f"https://x/{name}"])


@pytest.fixture
def state():
    s = SearchState(bbox=(-121.0, 34.0, -119.0, 35.0))
    s.results = Results([
        _granule("a", (-121.0, 34.0, -120.5, 34.5)),
        _granule("b", (-120.4, 34.1, -119.9, 34.6)),
        _granule("c", (-71.287, 44.064, -71.287, 44.064),        # a NEON point
                 sensor="NEON", level="L1", cloud=None, size=None),
    ])
    return s


# --------------------------------------------------------------------------- #
# the box                                                                      #
# --------------------------------------------------------------------------- #

def test_a_drawn_rectangle_becomes_a_bbox():
    s = SearchState()
    assert s.set_bbox_from_geojson({"type": "Polygon", "coordinates": [[
        [-121.0, 34.0], [-119.0, 34.0], [-119.0, 35.0], [-121.0, 35.0], [-121.0, 34.0]]]}) \
        == (-121.0, 34.0, -119.0, 35.0)


def test_any_drawn_shape_becomes_its_bounds():
    """The toolbar can make a polygon; a search takes a box, so the bounds of
    what was drawn is the honest reading of the gesture."""
    s = SearchState()
    assert s.set_bbox_from_geojson({"type": "Polygon", "coordinates": [[
        [0.0, 0.0], [3.0, 1.0], [1.0, 4.0], [0.0, 0.0]]]}) == (0.0, 0.0, 3.0, 4.0)


def test_a_drawn_point_is_a_box_with_no_area():
    s = SearchState()
    assert s.set_bbox_from_geojson({"type": "Point", "coordinates": [5.0, 6.0]}) \
        == (5.0, 6.0, 5.0, 6.0)


def test_drawing_nothing_is_refused():
    with pytest.raises(ValueError, match="nothing was drawn"):
        SearchState().set_bbox_from_geojson({"type": "Polygon", "coordinates": []})


@pytest.mark.parametrize("coords,n", [
    ([1.0, 2.0], 1),
    ([[1.0, 2.0], [3.0, 4.0]], 2),
    ([[[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]], 3),
    ([[[[1.0, 2.0]]], [[[3.0, 4.0]]]], 2),
])
def test_coordinates_are_flattened_however_deep_they_nest(coords, n):
    assert len(_flatten(coords)) == n


# --------------------------------------------------------------------------- #
# searching                                                                    #
# --------------------------------------------------------------------------- #

def test_searching_with_no_box_says_to_draw_one():
    with pytest.raises(ValueError, match="draw a rectangle"):
        SearchState().search("EMIT", "L2A")


def test_the_drawn_box_is_the_one_searched(monkeypatch):
    seen = {}
    monkeypatch.setattr("hyperproc.archive.interactive._search",
                        lambda s, lv, **kw: seen.update(kw) or Results([]))
    SearchState(bbox=(1.0, 2.0, 3.0, 4.0)).search("EMIT", "L2A")
    assert seen["bbox"] == (1.0, 2.0, 3.0, 4.0)


def test_an_explicit_bbox_wins_over_the_drawn_one(monkeypatch):
    seen = {}
    monkeypatch.setattr("hyperproc.archive.interactive._search",
                        lambda s, lv, **kw: seen.update(kw) or Results([]))
    SearchState(bbox=(1.0, 2.0, 3.0, 4.0)).search("EMIT", "L2A", bbox=(9.0, 9.0, 10.0, 10.0))
    assert seen["bbox"] == (9.0, 9.0, 10.0, 10.0)


def test_a_cloud_filter_on_a_sensor_with_no_cloud_is_refused_not_sent():
    """The AVIRIS collections report no cloud, so the filter would exclude
    everything - a working search that looks broken."""
    with pytest.raises(ValueError, match="does not report cloud"):
        SearchState(bbox=(1.0, 2.0, 3.0, 4.0)).search("AVIRIS-3", "L1B", cloud=(0, 10))


@pytest.mark.parametrize("sensor,level,expected", [
    ("EMIT", "L2A", True), ("PACE", "L2", True), ("PACE", "L1B", False),
    ("AVIRIS-3", "L1B", False), ("ENMAP", "L2A", True), ("NEON", "L1", False),
])
def test_the_slider_follows_the_collection_table(sensor, level, expected):
    assert has_cloud(sensor, level) is expected


def test_a_new_search_clears_the_old_selection(state, monkeypatch):
    state.toggle("a")
    monkeypatch.setattr("hyperproc.archive.interactive._search",
                        lambda s, lv, **kw: Results([]))
    state.search("EMIT", "L2A")
    assert state.selected == [], "the old selection named granules that are gone"


# --------------------------------------------------------------------------- #
# the selection                                                                #
# --------------------------------------------------------------------------- #

def test_clicking_selects_and_clicking_again_deselects(state):
    assert state.toggle("a") is True
    assert [g.name for g in state.selected] == ["a"]
    assert state.toggle("a") is False
    assert state.selected == []


def test_the_selection_keeps_the_order_things_were_picked_in(state):
    state.toggle("b")
    state.toggle("a")
    assert [g.name for g in state.selected] == ["b", "a"]


def test_selecting_something_that_was_not_found_is_an_error(state):
    with pytest.raises(KeyError, match="not in the last search"):
        state.toggle("nothing-like-this")


def test_select_all_and_clear(state):
    assert len(state.select_all()) == 3
    state.clear()
    assert state.selected == []


def test_what_is_selected_is_what_download_would_take(state):
    state.toggle("a")
    assert all(isinstance(g, Granule) for g in state.selected)
    assert state.selected[0].links == ["https://x/a"]


# --------------------------------------------------------------------------- #
# what the map draws                                                           #
# --------------------------------------------------------------------------- #

def test_a_footprint_with_area_is_a_polygon(state):
    feats = state.geojson()["features"]
    assert feats[0]["geometry"]["type"] == "Polygon"
    assert len(feats[0]["geometry"]["coordinates"][0]) == 5, "closed ring"


def test_a_footprint_with_no_area_is_a_point_so_it_can_be_seen(state):
    """NEON publishes a site's coordinates, not its flight box. A zero-width
    polygon would draw as nothing at all."""
    point = [f for f in state.geojson()["features"] if f["id"] == "c"][0]
    assert point["geometry"] == {"type": "Point", "coordinates": [-71.287, 44.064]}


def test_a_granule_without_a_footprint_is_left_off_the_map():
    s = SearchState()
    s.results = Results([_granule("a", None)])
    assert s.geojson()["features"] == []


def test_selected_footprints_are_drawn_in_the_other_colour(state):
    state.toggle("b")
    by_id = {f["id"]: f["properties"] for f in state.geojson()["features"]}
    assert by_id["b"]["selected"] is True and by_id["b"]["color"] == PICKED
    assert by_id["a"]["selected"] is False and by_id["a"]["color"] == FOUND


def test_a_footprint_carries_what_a_tooltip_would_show(state):
    props = state.geojson()["features"][0]["properties"]
    assert props["name"] == "a" and props["sensor"] == "EMIT" and props["level"] == "L2A"
    assert props["time"] == "2023-04-01 12:00"
    assert props["cloud"] == 10.0 and props["size_mb"] == 100.0


def test_the_summary_says_where_what_and_how_many(state):
    state.toggle("a")
    said = state.summary()
    assert "bbox" in said and "3 granules" in said and "1 selected" in said
    assert "no area chosen" in SearchState().summary()


def test_the_sensor_table_is_the_searchable_one():
    from hyperproc.archive import COLLECTIONS
    assert sensors() == {s: sorted({lv for ss, lv in COLLECTIONS if ss == s})
                         for s, _ in COLLECTIONS}


# --------------------------------------------------------------------------- #
# the widgets                                                                  #
# --------------------------------------------------------------------------- #

@pytest.fixture
def m(monkeypatch):
    pytest.importorskip("ipyleaflet")
    from hyperproc.archive.interactive import Map
    monkeypatch.setattr(
        "hyperproc.archive.interactive._search",
        lambda s, lv, **kw: Results([_granule("a", (-121.0, 34.0, -120.5, 34.5)),
                                     _granule("b", (-120.4, 34.1, -119.9, 34.6))]))
    return Map(bbox=(-121.0, 34.0, -119.0, 35.0))


def test_the_map_is_built_with_a_draw_tool_and_a_panel(m):
    kinds = {type(c).__name__ for c in m.map.controls}
    assert {"DrawControl", "LayersControl"} <= kinds
    assert m._panel is not None


def test_the_panel_sits_beside_the_map_not_inside_it():
    """A leaflet WidgetControl is a floating overlay sized by its own CSS, and a
    front end that clips it rather than scrolling it loses whatever does not
    fit. That is how the download button vanished under VS Code. An HBox is
    ordinary widget layout, handled the same way everywhere."""
    pytest.importorskip("ipyleaflet")
    from hyperproc.archive.interactive import Map
    built = Map(height="600px")
    assert type(built.widget).__name__ == "HBox"
    assert list(built.widget.children) == [built.map, built._panel]
    assert not any(type(c).__name__ == "WidgetControl" for c in built.map.controls), \
        "nothing of the panel may live inside the map any more"


def test_the_panel_is_a_fixed_sidebar_and_the_map_takes_the_rest():
    pytest.importorskip("ipyleaflet")
    from hyperproc.archive.interactive import Map
    built = Map(height="420px")
    assert built._panel.layout.flex == "0 0 300px"
    assert built.map.layout.flex == "1 1 auto"
    assert built._panel.layout.max_height == "420px"


def test_a_draw_event_sets_the_box(m):
    m._drawn(None, "created", {"geometry": {"type": "Polygon", "coordinates": [[
        [0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]}})
    assert m.bbox == (0.0, 0.0, 1.0, 1.0)
    assert "0.000" in m.w_status.value


def test_a_draw_event_that_is_not_a_creation_is_ignored(m):
    before = m.bbox
    m._drawn(None, "deleted", {"geometry": {"type": "Point", "coordinates": [9.0, 9.0]}})
    assert m.bbox == before


def test_the_panel_search_draws_the_footprints(m):
    m.search()
    assert len(m.results) == 2
    assert list(m.w_list.options) == ["a", "b"]
    assert m._layer is not None and len(m._layer.data["features"]) == 2


def test_clicking_a_footprint_selects_it_and_updates_the_list(m):
    m.search()
    m._clicked(feature=m._layer.data["features"][0])
    assert [g.name for g in m.selected] == ["a"]
    assert m.w_list.value == ("a",)
    assert m._layer.data["features"][0]["properties"]["color"] == PICKED


def test_choosing_in_the_list_selects_on_the_map_too(m):
    m.search()
    m.w_list.value = ("b",)
    assert [g.name for g in m.selected] == ["b"]


def test_select_all_ticks_everything(m):
    m.search()
    m._select_all()
    assert len(m.selected) == 2 and set(m.w_list.value) == {"a", "b"}


def test_changing_sensor_changes_the_levels_offered(m):
    m.w_sensor.value = "NEON"
    assert list(m.w_level.options) == ["L1"]
    assert m.w_cloud.disabled is True, "NEON reports no cloud"
    m.w_sensor.value = "EMIT"
    assert set(m.w_level.options) == {"L1B", "L2A"}
    assert m.w_cloud.disabled is False


def test_the_level_alone_can_switch_the_slider_off(m):
    """PACE publishes a cloud fraction at L2 and none at L1B, so the sensor is
    not enough to decide - the level has to be watched too."""
    m.w_sensor.value = "PACE"
    m.w_level.value = "L2"
    assert m.w_cloud.disabled is False
    m.w_level.value = "L1B"
    assert m.w_cloud.disabled is True


def test_the_panel_passes_its_own_settings_to_the_search(m, monkeypatch):
    seen = {}
    monkeypatch.setattr("hyperproc.archive.interactive._search",
                        lambda s, lv, **kw: seen.update(dict(kw, sensor=s, level=lv))
                        or Results([]))
    m.w_sensor.value = "ENMAP"
    m.w_level.value = "L2A"
    m.w_start.value = "2023-06-01"
    m.w_end.value = "2023-09-30"
    m.w_cloud.value = (0, 20)
    m.w_count.value = 7
    m.search()
    assert seen["sensor"] == "ENMAP" and seen["level"] == "L2A"
    assert seen["date"] == ("2023-06-01", "2023-09-30")
    assert seen["cloud"] == (0, 20) and seen["count"] == 7
    assert seen["bbox"] == (-121.0, 34.0, -119.0, 35.0)


def test_an_untouched_cloud_slider_is_not_sent_as_a_filter(m, monkeypatch):
    seen = {}
    monkeypatch.setattr("hyperproc.archive.interactive._search",
                        lambda s, lv, **kw: seen.update(kw) or Results([]))
    m.search()
    assert "cloud" not in seen, "0-100 percent is no filter at all"


def test_a_failed_search_shows_the_reason_and_still_raises(m, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("the archive is down")
    monkeypatch.setattr("hyperproc.archive.interactive._search", boom)
    with pytest.raises(RuntimeError):
        m.search()
    assert "the archive is down" in m.w_status.value


def test_downloading_nothing_says_so_and_asks_no_archive(m):
    m.search()
    assert m.download() == []
    assert "nothing selected" in m.w_status.value


def test_the_download_button_is_the_download_function(m, monkeypatch):
    seen = {}
    monkeypatch.setattr("hyperproc.archive.api.download",
                        lambda r, out, **kw: seen.update(out=out, n=len(r)) or [])
    m.search()
    m._select_all()
    m.w_out.value = "somewhere"
    m.download()
    assert seen == {"out": "somewhere", "n": 2}


# --------------------------------------------------------------------------- #
# showing a result set the map did not search for                              #
# --------------------------------------------------------------------------- #

def test_the_extent_of_a_result_set_is_its_footprints(state):
    assert state.bounds() == (-121.0, 34.0, -71.287, 44.064)


def test_the_extent_falls_back_to_the_drawn_box_when_nothing_has_a_footprint():
    s = SearchState(bbox=(1.0, 2.0, 3.0, 4.0))
    assert s.bounds() == (1.0, 2.0, 3.0, 4.0)
    s.results = Results([_granule("a", None)])
    assert s.bounds() == (1.0, 2.0, 3.0, 4.0)


def test_a_map_can_be_handed_a_search_it_did_not_run(m):
    """The tour notebook searches thirteen collections and wants to look at each
    in turn; searching twice to see the same thing would be absurd."""
    other = Results([_granule("x", (0.0, 0.0, 1.0, 1.0)),
                     _granule("y", (1.0, 1.0, 2.0, 2.0))])
    got = m.show(other)
    assert got is other
    assert list(m.w_list.options) == ["x", "y"]
    assert len(m._layer.data["features"]) == 2
    assert m.results is other


def test_a_shown_result_set_can_be_clicked_like_a_searched_one(m):
    m.show(Results([_granule("x", (0.0, 0.0, 1.0, 1.0))]))
    m._clicked(feature=m._layer.data["features"][0])
    assert [g.name for g in m.selected] == ["x"]
    assert m.w_list.value == ("x",)


def test_showing_clears_what_was_selected_from_the_previous_set(m):
    m.search()
    m._select_all()
    assert len(m.selected) == 2
    m.show(Results([_granule("x", (0.0, 0.0, 1.0, 1.0))]))
    assert m.selected == [], "the old selection named granules that are no longer shown"


def test_a_plain_list_of_granules_is_accepted_too(m):
    m.show([_granule("x", (0.0, 0.0, 1.0, 1.0))])
    assert isinstance(m.results, Results) and len(m.results) == 1


def test_results_can_be_passed_at_construction(monkeypatch):
    pytest.importorskip("ipyleaflet")
    from hyperproc.archive.interactive import Map
    got = Results([_granule("x", (0.0, 0.0, 1.0, 1.0))])
    built = Map(results=got)
    assert built.results is got
    assert list(built.w_list.options) == ["x"]


def test_fit_zooms_to_the_extent_of_everything_shown(m):
    # ipyleaflet reports map.bounds only from a live front end, so the checkable
    # part is the extent fit() is given
    m.show(Results([_granule("x", (0.0, 0.0, 1.0, 1.0)),
                    _granule("y", (2.0, 2.0, 3.0, 3.0))]))
    assert m.state.bounds() == (0.0, 0.0, 3.0, 3.0)


def test_fitting_with_nothing_to_fit_does_nothing(m):
    m.state.results = Results([])
    m.state.bbox = None
    m.fit()          # must not raise


# --------------------------------------------------------------------------- #
# opening on the data                                                          #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("bounds,expected", [
    ((-180, -85, 180, 85), 1),          # the whole world
    ((-130, -5, -60, 45), 3),           # a set of PACE swaths
    ((-121, 33.5, -115, 37.5), 7),      # a state
    ((-117.44, 34.46, -117.40, 34.49), 14),   # one AVIRIS flight line
])
def test_a_zoom_is_computed_from_the_extent(bounds, expected):
    from hyperproc.archive.interactive import zoom_for
    assert zoom_for(bounds) == expected


def test_zoom_is_clamped_to_what_a_tile_server_has():
    from hyperproc.archive.interactive import zoom_for
    assert zoom_for((0.0, 0.0, 1e-9, 1e-9)) <= 18
    assert zoom_for((-180.0, -85.0, 180.0, 85.0)) >= 1


def test_the_map_opens_on_the_data_not_where_it_was_constructed(m):
    """fit_bounds only messages a live browser, so a notebook executed headless
    would save a map centred on nothing. center and zoom are traits, so they
    are saved - this is what makes a reopened notebook show the granules."""
    before = tuple(m.map.center)
    m.show(Results([_granule("x", (-121.0, 33.5, -120.0, 34.5)),
                    _granule("y", (-118.0, 35.0, -117.0, 36.0))]))
    lat, lon = m.map.center
    assert (lat, lon) != before
    assert -122 < lon < -116 and 33 < lat < 37, "centred between the footprints"
    assert m.map.zoom >= 5, "zoomed in on a two-degree extent"


def test_showing_without_fitting_leaves_the_view_alone(m):
    before, zoom = tuple(m.map.center), m.map.zoom
    m.show(Results([_granule("x", (-121.0, 33.5, -120.0, 34.5))]), fit=False)
    assert tuple(m.map.center) == before and m.map.zoom == zoom


def test_hovering_a_footprint_names_the_granule(m):
    m.search()
    m._hovered(feature=m._layer.data["features"][0])
    said = m.w_status.value
    assert "a" in said and "2023-04-01" in said
    assert "10% cloud" in said and "100 MB" in said


def test_the_status_line_says_what_is_on_screen_when_no_box_was_drawn():
    s = SearchState()
    assert "no area chosen" in s.summary()
    s.results = Results([_granule("x", (-121.0, 33.5, -120.0, 34.5))])
    assert "extent" in s.summary() and "-121.00" in s.summary()


@pytest.mark.parametrize("css,expected", [("600px", 600), ("420px", 420), ("auto", 600)])
def test_the_map_height_is_read_from_its_css(css, expected):
    from hyperproc.archive.interactive import _px
    assert _px(css, 600) == expected


# --------------------------------------------------------------------------- #
# quicklooks                                                                   #
# --------------------------------------------------------------------------- #

def test_a_footprint_carries_its_quicklook_url(state):
    state.results = Results([_granule("a", (-121.0, 34.0, -120.5, 34.5))])
    state.results[0].browse = "https://example/a.png"
    assert state.geojson()["features"][0]["properties"]["browse"] == "https://example/a.png"


def test_the_preview_is_an_image_that_opens_full_size(m):
    html = m.preview_html({"browse": "https://example/a.png", "sensor": "EMIT"})
    assert '<img src="https://example/a.png"' in html
    assert 'href="https://example/a.png"' in html and 'target="_blank"' in html


def test_a_quicklook_the_archive_never_wrote_falls_back_to_a_sentence(m):
    """CMR lists a browse image for every PACE granule and none exist, so the
    URL is present and 404s. A broken-image icon explains nothing."""
    html = m.preview_html({"browse": "https://example/missing.png", "sensor": "PACE"})
    assert "onerror=" in html
    assert "missing" in html


@pytest.mark.parametrize("sensor", ["NEON", "ENMAP", "DESIS"])
def test_an_archive_with_no_public_quicklook_says_so(m, sensor):
    """NEON publishes none per delivery and DLR's thumbnails sit behind its
    sign-on, so there is nothing a map can load."""
    html = m.preview_html({"browse": None, "sensor": sensor})
    assert "no public quicklook" in html and sensor in html
    assert "<img" not in html


def test_clicking_a_footprint_shows_its_quicklook(m, monkeypatch):
    monkeypatch.setattr("hyperproc.archive.interactive._search",
                        lambda s, lv, **kw: Results([_granule("a", (0.0, 0.0, 1.0, 1.0))]))
    m.search()
    m.results[0].browse = "https://example/a.png"
    m._redraw()
    m._clicked(feature=m._layer.data["features"][0])
    assert "https://example/a.png" in m.w_preview.value


def test_a_new_search_clears_the_previous_quicklook(m):
    m.search()
    m._clicked(feature=m._layer.data["features"][0])
    m.search()
    assert m.w_preview.value == "", "it belonged to a granule that is no longer shown"


# --------------------------------------------------------------------------- #
# the panel's layout                                                           #
# --------------------------------------------------------------------------- #

def test_every_action_sits_above_everything_that_grows(m):
    """The panel scrolls. The granule list and the quicklook both grow with what
    you searched and clicked, so a button placed after them slides out of view
    exactly when you want it - which is how Download selected disappeared."""
    flat = []
    for c in m._panel.children:
        flat.extend(getattr(c, "children", [c]))
    actions = [m.w_go, m.w_all, m.w_get]
    grows = [m.w_list, m.w_preview]
    assert max(flat.index(a) for a in actions) < min(flat.index(g) for g in grows)


def test_the_quicklook_is_the_very_last_thing(m):
    assert list(m._panel.children)[-1] is m.w_preview


def test_a_quicklook_is_capped_so_it_cannot_fill_the_panel(m):
    html = m.preview_html({"browse": "https://example/a.png", "sensor": "EMIT"})
    assert "max-height:150px" in html
    assert "full size" in html, "the whole image is still one click away"


@pytest.mark.parametrize("height", ["600px", "380px", "240px"])
def test_the_panel_is_sized_to_the_map_not_to_a_fixed_guess(height):
    pytest.importorskip("ipyleaflet")
    from hyperproc.archive.interactive import Map
    assert Map(height=height)._panel.layout.max_height == height


def test_the_selection_count_is_not_printed_twice(m):
    m.search()
    m._clicked(feature=m._layer.data["features"][0])
    assert m.w_status.value.count("selected") == 1
