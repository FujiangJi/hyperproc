"""hyperproc.archive.dlr - EnMAP and DESIS through DLR's EOC STAC catalogue.

Two things about this archive shape the code and therefore these tests. DLR
publishes no file sizes, so a result must say "unpublished" rather than guess;
and it publishes EnMAP's rasters under a ``_COG`` name that the plain granule
does not use, so a downloaded scene has to open anyway.

Responses are replayed from ``tests/data/archive_fixtures/enmap_l2a.json`` and
``desis_l2a.json``, recorded by ``tests/tools/make_archive_fixtures.py``.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from hyperproc.archive import dlr

FIXTURES = Path(__file__).parent / "data" / "archive_fixtures"


class _Response:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.fixture
def fake_stac(monkeypatch):
    """Replay one recorded collection. Returns the request bodies that were sent."""
    sent: list[dict] = []

    def factory(name):
        payload = json.loads((FIXTURES / f"{name}.json").read_text())

        class _Requests:
            @staticmethod
            def post(url, json=None, **kw):
                sent.append(dict(json or {}))
                start = (json or {}).get("startIndex", 0)
                limit = (json or {}).get("limit", 10)
                page = payload["features"][start:start + limit]
                return _Response({"numberMatched": payload["numberMatched"],
                                  "features": page})

        monkeypatch.setattr(dlr, "_requests", lambda: _Requests)
        return sent

    return factory


# --------------------------------------------------------------------------- #
# the query we build                                                           #
# --------------------------------------------------------------------------- #

def test_the_query_carries_the_collection_the_box_and_the_window(fake_stac):
    sent = fake_stac("enmap_l2a")
    dlr.search("ENMAP", "L2A", bbox=(10, 47, 11.5, 48.5),
               date=("2023-06-01", "2023-09-30"), count=3, verbose=False)
    body = sent[0]
    assert body["collections"] == ["ENMAP_HSI_L2A"]
    assert body["bbox"] == [10.0, 47.0, 11.5, 48.5]
    assert body["datetime"] == "2023-06-01T00:00:00Z/2023-09-30T23:59:59Z"


def test_a_single_day_means_the_whole_day_not_midnight(fake_stac):
    sent = fake_stac("enmap_l2a")
    dlr.search("ENMAP", "L2A", bbox=(10, 47, 11.5, 48.5), date="2023-09-29",
               count=3, verbose=False)
    assert sent[0]["datetime"] == "2023-09-29T00:00:00Z/2023-09-29T23:59:59Z"


def test_a_cloud_filter_becomes_cql2_because_the_query_extension_is_ignored(fake_stac):
    sent = fake_stac("enmap_l2a")
    dlr.search("ENMAP", "L2A", bbox=(10, 47, 11.5, 48.5), cloud=(0, 10),
               count=3, verbose=False)
    body = sent[0]
    assert body["filter-lang"] == "cql2-json"
    props = json.dumps(body["filter"])
    assert "eo:cloud_cover" in props and '">="' in props and '"<="' in props


def test_a_cloud_filter_without_a_box_is_refused_rather_than_left_to_time_out(fake_stac):
    fake_stac("enmap_l2a")
    with pytest.raises(ValueError, match="scans the whole catalogue"):
        dlr.search("ENMAP", "L2A", cloud=(0, 10), verbose=False)


@pytest.mark.parametrize("bad,match", [
    ((-200, 0, 10, 10), "out of range"),
    ((10, 0, -10, 10), "inside out"),
])
def test_a_broken_bbox_is_refused_before_the_network(fake_stac, bad, match):
    sent = fake_stac("enmap_l2a")
    with pytest.raises(ValueError, match=match):
        dlr.search("ENMAP", "L2A", bbox=bad, verbose=False)
    assert sent == []


def test_count_is_paged_not_asked_for_in_one_go(fake_stac):
    sent = fake_stac("enmap_l2a")
    got = dlr.search("ENMAP", "L2A", bbox=(10, 47, 11.5, 48.5), count=2, verbose=False)
    assert len(got) == 2
    assert sent[0]["limit"] == 2 and sent[0]["startIndex"] == 0


def test_paging_stops_when_a_page_comes_back_short(fake_stac):
    sent = fake_stac("enmap_l2a")                 # the fixture holds 3 of 36
    got = dlr.search("ENMAP", "L2A", bbox=(10, 47, 11.5, 48.5), count=-1, verbose=False)
    assert len(got) == 3
    assert len(sent) == 1, "one page that came back short ends it"


# --------------------------------------------------------------------------- #
# what a result carries                                                        #
# --------------------------------------------------------------------------- #

def test_an_enmap_result_carries_what_a_person_chooses_on(fake_stac):
    fake_stac("enmap_l2a")
    g = dlr.search("ENMAP", "L2A", bbox=(10, 47, 11.5, 48.5), count=1, verbose=False)[0]
    assert g.sensor == "ENMAP" and g.level == "L2A"
    assert g.collection == "ENMAP_HSI_L2A"
    assert g.name.startswith("ENMAP01-____L2A-")
    assert isinstance(g.time, datetime) and g.time.year == 2023
    assert g.cloud is not None and 0 <= g.cloud <= 100
    assert len(g.bbox) == 4 and g.bbox[0] < g.bbox[2] and g.bbox[1] < g.bbox[3]


def test_dlr_publishes_no_size_and_the_total_says_so(fake_stac):
    fake_stac("enmap_l2a")
    got = dlr.search("ENMAP", "L2A", bbox=(10, 47, 11.5, 48.5), count=3, verbose=False)
    assert all(g.size_mb is None for g in got)
    assert "size not published" in repr(got)
    assert "size not published" in got.table()


def test_the_links_are_what_the_reader_opens(fake_stac):
    fake_stac("enmap_l2a")
    g = dlr.search("ENMAP", "L2A", bbox=(10, 47, 11.5, 48.5), count=1, verbose=False)[0]
    names = [u.rsplit("/", 1)[-1] for u in g.links]
    assert any(n.endswith("-METADATA.XML") for n in names)
    assert any("SPECTRAL_IMAGE" in n for n in names)
    assert any("QL_QUALITY_CLOUD" in n for n in names)
    assert not any("thumbnail" in n for n in names), "a browse png is not data"


def test_assets_image_drops_the_masks_and_all_keeps_everything(fake_stac):
    fake_stac("enmap_l2a")
    def links(assets):
        return dlr.search("ENMAP", "L2A", bbox=(10, 47, 11.5, 48.5), count=1,
                          assets=assets, verbose=False)[0].links
    assert len(links("image")) == 2                # metadata + the cube
    assert len(links("reader")) > 2
    assert len(links("all")) > len(links("reader"))


def test_an_unknown_assets_choice_is_refused(fake_stac):
    fake_stac("enmap_l2a")
    with pytest.raises(ValueError, match="assets must be"):
        dlr.search("ENMAP", "L2A", bbox=(10, 47, 11.5, 48.5), assets="some", verbose=False)


def test_desis_replays_too_and_its_files_are_plainly_named(fake_stac):
    fake_stac("desis_l2a")
    got = dlr.search("DESIS", "L2A", bbox=(-120, 34, -118, 36), count=3, verbose=False)
    assert len(got) == 3
    names = [u.rsplit("/", 1)[-1] for u in got[0].links]
    assert any(n.endswith("-SPECTRAL_IMAGE.tif") for n in names), \
        "DESIS is not published as COGs, so no _COG here"
    assert any(n.endswith("-METADATA.xml") for n in names)
    assert any(n.endswith("-QL_QUALITY.tif") for n in names)
    assert any(n.endswith("-QL_QUALITY-2.tif") for n in names)


@pytest.mark.parametrize("raw,expected", [
    ("2023-12-31T21:59:23.192921Z", datetime(2023, 12, 31, 21, 59, 23, 192921)),
    ("2024-01-02T03:04:05Z", datetime(2024, 1, 2, 3, 4, 5)),
    ("2024-01-02T03:04:05.12Z", datetime(2024, 1, 2, 3, 4, 5, 120000)),
    ("2024-01-02T03:04:05.1234567Z", datetime(2024, 1, 2, 3, 4, 5, 123456)),
    ("", None),
    ("not a time", None),
])
def test_times_survive_however_many_fractional_digits_stac_writes(raw, expected):
    assert dlr._time_of({"datetime": raw}) == expected


def test_start_datetime_is_used_when_datetime_is_absent():
    assert dlr._time_of({"start_datetime": "2024-05-06T07:08:09Z"}) \
        == datetime(2024, 5, 6, 7, 8, 9)


# --------------------------------------------------------------------------- #
# credentials, which searching never needs                                     #
# --------------------------------------------------------------------------- #

def test_credentials_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("DLR_EOC_USERNAME", "someone")
    monkeypatch.setenv("DLR_EOC_PASSWORD", "secret")
    assert dlr.credentials() == ("someone", "secret")


def test_credentials_come_from_netrc_when_the_environment_is_empty(monkeypatch, tmp_path):
    monkeypatch.delenv("DLR_EOC_USERNAME", raising=False)
    monkeypatch.delenv("DLR_EOC_PASSWORD", raising=False)
    rc = tmp_path / ".netrc"
    rc.write_text("machine download.geoservice.dlr.de login netrcuser password netrcpass\n")
    rc.chmod(0o600)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("NETRC", str(rc))
    assert dlr.credentials() == ("netrcuser", "netrcpass")


def test_with_no_credentials_the_download_says_where_to_register(monkeypatch, fake_stac):
    fake_stac("enmap_l2a")
    monkeypatch.setattr(dlr, "credentials", lambda *a, **k: None)
    got = dlr.search("ENMAP", "L2A", bbox=(10, 47, 11.5, 48.5), count=1, verbose=False)
    with pytest.raises(PermissionError) as exc:
        dlr.download(got, "/nowhere", verbose=False)
    assert "enmap.org/data_access" in str(exc.value), "the EnMAP door, not a generic one"
    assert ".netrc" in str(exc.value)


def test_the_two_missions_are_two_registrations_not_one(monkeypatch, fake_stac):
    """Both are served from download.geoservice.dlr.de behind one sign-on, but
    DLR grants access per mission, so an EnMAP account need not open DESIS.
    Naming the wrong portal sends people to the wrong form."""
    assert "enmap.org/data_access" in dlr.needs_login("ENMAP")
    assert "eoweb.dlr.de/egp" not in dlr.needs_login("ENMAP")
    assert "eoweb.dlr.de/egp" in dlr.needs_login("DESIS")
    assert "enmap.org/data_access" not in dlr.needs_login("DESIS")
    both = dlr.needs_login()
    assert "enmap.org/data_access" in both and "eoweb.dlr.de/egp" in both


@pytest.mark.parametrize("sensor,other", [("ENMAP", "DESIS"), ("DESIS", "ENMAP")])
def test_a_mission_specific_account_wins_over_the_shared_one(monkeypatch, sensor, other):
    monkeypatch.setenv("DLR_EOC_USERNAME", "shared")
    monkeypatch.setenv("DLR_EOC_PASSWORD", "sharedpw")
    monkeypatch.setenv(f"{sensor}_USERNAME", "mine")
    monkeypatch.setenv(f"{sensor}_PASSWORD", "minepw")
    monkeypatch.delenv(f"{other}_USERNAME", raising=False)
    monkeypatch.delenv(f"{other}_PASSWORD", raising=False)
    assert dlr.credentials(sensor=sensor) == ("mine", "minepw")
    assert dlr.credentials(sensor=other) == ("shared", "sharedpw"), \
        "the mission with no account of its own falls back to the shared pair"


# --------------------------------------------------------------------------- #
# the sign-on, which is a CAS form and not HTTP Basic                          #
# --------------------------------------------------------------------------- #

LOGIN_PAGE = """
<html><body><form action="login" method="post">
  <input name="username" value="">
  <input name="password" value="">
  <input name="execution" value="a-one-time-token">
  <input name="_eventId" value="submit">
</form></body></html>
"""


class _Resp:
    def __init__(self, url, status=200, text=""):
        self.url, self.status_code, self.text = url, status, text

    def raise_for_status(self): return None
    def iter_content(self, n): return [b"x"]
    def close(self): return None
    def __enter__(self): return self
    def __exit__(self, *a): return False


class _Session:
    """A requests.Session that lands on the sign-on until it is posted to."""

    def __init__(self, signed_in=False, accept=("u", "p")):
        self.headers, self.cookies = {}, {"XSRF-TOKEN": "xyz"}
        self.signed_in, self.accept, self.posted = signed_in, accept, []

    def get(self, url, **kw):
        if self.signed_in:
            return _Resp(url)
        return _Resp("https://sso.eoc.dlr.de/eoc/auth/login?service=" + url,
                     text=LOGIN_PAGE)

    def post(self, url, data=None, **kw):
        self.posted.append(data)
        if (data["username"], data["password"]) == self.accept:
            self.signed_in = True
            return _Resp("https://download.geoservice.dlr.de/x?ticket=ST-1")
        return _Resp(url, status=401, text="Authentication Failure")


@pytest.mark.parametrize("page,expected", [
    ("<h2>Authentication Failure</h2><p>Authentication attempt has failed. "
     "Username: is a required field</p>", "Authentication attempt has failed"),
    ("<p>Your account is locked. Contact the helpdesk</p>", "account is locked"),
    ("<p>Your password has expired. Reset it</p>", "has expired"),
    ("<html><body>nothing useful here</body></html>", ""),
])
def test_the_servers_own_reason_is_quoted_back_one_sentence_only(page, expected):
    """A wrong password and a locked account arrive with the same 401; only the
    page says which. The rest of it is form labels, so one sentence is enough."""
    assert dlr._page_says(page) == expected


def test_the_login_form_is_parsed_including_its_one_time_token():
    found = dlr._Forms()
    found.feed(LOGIN_PAGE)
    form = found.login
    assert form["fields"]["execution"] == "a-one-time-token"
    assert form["fields"]["_eventId"] == "submit"
    assert set(form["fields"]) >= {"username", "password"}


#: DLR's EnMAP sign-on, which carries a second, hidden form whose only job is
#: to hand you off to the EO-Lab identity provider.
ENMAP_LOGIN_PAGE = """
<html><body><h2>EnMAP Access Service</h2>
<form action="login" method="post">
  <input name="username" value=""><input type="password" name="password" value="">
  <input type="hidden" name="execution" value="the-real-token">
  <input type="hidden" name="_eventId" value="submit">
</form>
<form action="/eoc/auth/login" method="post">
  <input type="hidden" name="_csrf" value="c">
  <input type="hidden" name="client_name" value="eolab2_enmap-dl">
  <input type="hidden" name="_eventId" value="delegatedAuthenticationRedirect">
</form></body></html>
"""


def test_two_forms_on_one_page_are_kept_apart():
    """EnMAP's page has a login form and a 'sign in with EO-Lab' form. Merging
    their fields posts the delegation _eventId with the credentials, so the
    sign-on redirects to Keycloak and the password is never tried."""
    found = dlr._Forms()
    found.feed(ENMAP_LOGIN_PAGE)
    assert len(found.forms) == 2
    login = found.login
    assert login["fields"]["_eventId"] == "submit", "not the delegation event"
    assert "client_name" not in login["fields"], "the other form's field leaked in"
    assert found.step["fields"]["client_name"] == "eolab2_enmap-dl"


def test_the_credentials_go_to_the_login_form_not_the_delegation_one():
    class _TwoForm(_Session):
        def get(self, url, **kw):
            if self.signed_in:
                return _Resp(url)
            return _Resp("https://sso.eoc.dlr.de/eoc/auth/login?service=" + url,
                         text=ENMAP_LOGIN_PAGE)

    s = _TwoForm(accept=("u", "p"))
    dlr.sign_in(s, "https://download.geoservice.dlr.de/ENMAP/files/x.xml",
                ("u", "p"), sensor="ENMAP")
    sent = s.posted[0]
    assert sent["_eventId"] == "submit"
    assert sent["execution"] == "the-real-token"
    assert "client_name" not in sent


@pytest.mark.parametrize("page_url,action,expected", [
    ("https://sso/x/login?service=Y", "login", "https://sso/x/login?service=Y"),
    ("https://sso/x/login?service=Y", None, "https://sso/x/login?service=Y"),
    ("https://sso/x/login?service=Y", "", "https://sso/x/login?service=Y"),
    ("https://sso/x/login?service=Y", "/other/place", "https://sso/other/place"),
])
def test_a_self_referential_action_keeps_the_query_string(page_url, action, expected):
    """CAS keeps the service it is signing you in to in the query string;
    urljoin would drop it."""
    assert dlr._post_to(page_url, action) == expected


def test_signing_in_posts_the_credentials_with_the_token():
    """DLR's file server answers 403 to an Authorization header and has no
    WWW-Authenticate challenge, so Basic auth is not the mechanism - the CAS
    form is. Posting without the one-time token is rejected."""
    s = _Session()
    dlr.sign_in(s, "https://download.geoservice.dlr.de/DESIS/files/x.xml",
                ("u", "p"), sensor="DESIS")
    sent = s.posted[0]
    assert sent["username"] == "u" and sent["password"] == "p"
    assert sent["execution"] == "a-one-time-token", "the form's own token is carried back"
    assert sent["_eventId"] == "submit"


def test_an_already_signed_in_session_is_left_alone():
    s = _Session(signed_in=True)
    dlr.sign_in(s, "https://download.geoservice.dlr.de/DESIS/files/x.xml", ("u", "p"))
    assert s.posted == [], "no second login for the files after the first"


def test_a_refused_sign_on_names_the_mission_and_its_portal():
    s = _Session(accept=("someone-else", "something-else"))
    with pytest.raises(PermissionError) as exc:
        dlr.sign_in(s, "https://download.geoservice.dlr.de/DESIS/files/x.xml",
                    ("u", "wrong"), sensor="DESIS")
    said = str(exc.value)
    assert "401" in said
    assert "eoweb.dlr.de/egp" in said, "the DESIS door, not EnMAP's"
    assert "take different accounts" in said
    assert "Authentication Failure" in said, "the server's own words are quoted back"


def test_a_sign_on_page_we_cannot_fill_in_says_so_rather_than_guessing():
    class _Odd(_Session):
        def get(self, url, **kw):
            return _Resp("https://sso.eoc.dlr.de/eoc/auth/login",
                         text="<html><body>we redesigned this</body></html>")
    with pytest.raises(PermissionError, match="no password form"):
        dlr.sign_in(_Odd(), "https://download.geoservice.dlr.de/x", ("u", "p"))


def test_a_mixed_result_set_signs_in_to_each_mission_separately(monkeypatch, tmp_path):
    """The two accounts can differ, so one session cannot serve both."""
    from hyperproc.archive.results import Granule
    made = {}

    def _new_session():
        s = _Session(accept=("e", "ep"))
        made[len(made)] = s
        return s

    monkeypatch.setattr(dlr, "_requests",
                        lambda: type("R", (), {"Session": staticmethod(_new_session)}))
    monkeypatch.setenv("ENMAP_USERNAME", "e"); monkeypatch.setenv("ENMAP_PASSWORD", "ep")
    monkeypatch.setenv("DESIS_USERNAME", "d"); monkeypatch.setenv("DESIS_PASSWORD", "dp")

    def g(sensor):
        return Granule(name=sensor, sensor=sensor, level="L2A", collection="c",
                       version=None, time=None, bbox=None, size_mb=None, cloud=None,
                       links=[f"https://download.geoservice.dlr.de/{sensor}/{sensor}.TIF"])

    # DESIS's credentials are not the ones this stub accepts, so it must fail
    # on DESIS and not silently reuse EnMAP's session
    with pytest.raises(PermissionError, match="DESIS"):
        dlr.download([g("ENMAP"), g("DESIS")], tmp_path, workers=1, verbose=False)
    posted = [d for s in made.values() for d in s.posted]
    assert {(d["username"], d["password"]) for d in posted} == {("e", "ep"), ("d", "dp")}


def test_downloading_nothing_does_nothing(monkeypatch, tmp_path):
    from hyperproc.archive.results import Results
    monkeypatch.setattr(dlr, "_requests", lambda: None)
    assert dlr.download(Results([]), tmp_path, verbose=False) == []


# --------------------------------------------------------------------------- #
# the levels DLR does not publish                                              #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("level", ["L1B", "L1C"])
def test_asking_for_a_desis_level_dlr_does_not_publish_says_where_it_is(level):
    from hyperproc.archive import resolve
    with pytest.raises(ValueError, match="Teledyne"):
        resolve("DESIS", level)


@pytest.mark.network
def test_the_dlr_catalogue_still_answers_the_way_the_fixtures_say():
    import requests
    for name, body in [("enmap_l2a", {"collections": ["ENMAP_HSI_L2A"],
                                      "bbox": [10.0, 47.0, 11.5, 48.5],
                                      "datetime": "2023-06-01T00:00:00Z/2023-09-30T23:59:59Z"}),
                       ("desis_l2a", {"collections": ["DESIS_HSI_L2A"],
                                      "bbox": [-120.0, 34.0, -118.0, 36.0]})]:
        recorded = json.loads((FIXTURES / f"{name}.json").read_text())
        r = requests.post(f"{dlr.BASE}/search", json=dict(body, limit=3), timeout=180)
        r.raise_for_status()
        live = r.json()
        assert live["numberMatched"] >= recorded["numberMatched"], "the archive only grows"
        for f in live["features"]:
            assert {"id", "bbox", "geometry", "properties", "assets"} <= set(f)
            assert "datetime" in f["properties"]
            assert all("href" in a for a in f["assets"].values())


@pytest.mark.network
def test_dlrs_sign_on_is_still_the_form_this_version_fills_in():
    """If DLR changes its login page, downloads break with a confusing 403.
    This asks the live sign-on whether the fields are still there."""
    import requests
    url = ("https://download.geoservice.dlr.de/DESIS/files/L2A/2021/12/18/DT0667868308/19/"
           "DESIS-HSI-L2A-DT0667868308_019-20211218T214555-V0220/"
           "DESIS-HSI-L2A-DT0667868308_019-20211218T214555-V0220-METADATA.xml")
    s = requests.Session()
    s.headers["User-Agent"] = "hyperproc"
    r = s.get(url, timeout=60)
    assert "sso." in r.url, "the file server no longer redirects to the sign-on"
    found = dlr._Forms()
    found.feed(r.text)
    form = found.login
    assert form is not None, "no password form on DLR's sign-on"
    assert {"username", "password", "execution", "_eventId"} <= set(form["fields"])
    assert form["fields"]["execution"], "the one-time token is empty"


@pytest.mark.network
def test_the_file_server_still_refuses_basic_auth():
    """The premise of sign_in(). A 401 with a WWW-Authenticate challenge would
    mean Basic auth had become available and the CAS dance was unnecessary."""
    import requests
    url = "https://download.geoservice.dlr.de/DESIS/files/"
    r = requests.get(url, auth=("nobody", "nobody"), timeout=60, allow_redirects=False)
    assert r.status_code == 403
    assert "WWW-Authenticate" not in r.headers


# --------------------------------------------------------------------------- #
# the usage policy, which is the account holder's to accept                    #
# --------------------------------------------------------------------------- #

POLICY_PAGE = """
<html><body><h2>EOC UMS: Geoservice Login</h2><h2>Acceptable Usage Policy</h2>
<form method="post">
  <input name="execution" value="a-second-token">
  <input name="_eventId" value="submit">
</form></body></html>
"""


class _PolicySession(_Session):
    """Accepts the password, then shows the usage policy once."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.stage = "login"

    def post(self, url, data=None, **kw):
        self.posted.append(data)
        if self.stage == "login":
            if (data["username"], data["password"]) != self.accept:
                return _Resp(url, status=401, text="Authentication Failure")
            self.stage = "policy"
            return _Resp("https://sso.eoc.dlr.de/eoc/auth/login", text=POLICY_PAGE)
        self.stage = "done"
        return _Resp("https://download.geoservice.dlr.de/x?ticket=ST-1")


def test_a_pending_usage_policy_is_not_clicked_for_you():
    """The login worked; DLR is asking the account holder to agree to something.
    Submitting that silently would be agreeing on their behalf."""
    s = _PolicySession(accept=("u", "p"))
    with pytest.raises(PermissionError) as exc:
        dlr.sign_in(s, "https://download.geoservice.dlr.de/DESIS/files/x.xml",
                    ("u", "p"), sensor="DESIS")
    said = str(exc.value)
    assert "login worked" in said, "it must not read as a failed password"
    assert "Acceptable Usage Policy" in said
    assert "accept_policy=True" in said
    assert len(s.posted) == 1, "only the login was posted, never the policy"


def test_the_policy_is_accepted_only_when_asked_for():
    s = _PolicySession(accept=("u", "p"))
    dlr.sign_in(s, "https://download.geoservice.dlr.de/DESIS/files/x.xml",
                ("u", "p"), sensor="DESIS", accept_policy=True)
    assert len(s.posted) == 2
    assert s.posted[1] == {"execution": "a-second-token", "_eventId": "submit"}, \
        "the policy form's own token is carried back, not invented"


def test_a_form_with_no_action_posts_back_to_the_page_it_came_from():
    """CAS's policy form has no action attribute; a browser posts to the current
    URL. Treating that as 'nothing to submit' is what stalled this before."""
    seen = []

    class _NoAction(_PolicySession):
        def post(self, url, data=None, **kw):
            seen.append(url)
            return super().post(url, data=data, **kw)

    s = _NoAction(accept=("u", "p"))
    dlr.sign_in(s, "https://download.geoservice.dlr.de/DESIS/files/x.xml",
                ("u", "p"), sensor="DESIS", accept_policy=True)
    assert seen[1] == "https://sso.eoc.dlr.de/eoc/auth/login"


def test_a_benign_second_step_is_still_carried_through_without_asking():
    """Only pages that read as an agreement stop; a plain redirect form does not."""
    class _Interstitial(_PolicySession):
        def post(self, url, data=None, **kw):
            self.posted.append(data)
            if self.stage == "login":
                self.stage = "hop"
                return _Resp("https://sso.eoc.dlr.de/eoc/auth/login",
                             text='<html><h2>Redirecting</h2><form method="post">'
                                  '<input name="execution" value="t"></form></html>')
            return _Resp("https://download.geoservice.dlr.de/x?ticket=ST-1")

    s = _Interstitial(accept=("u", "p"))
    dlr.sign_in(s, "https://download.geoservice.dlr.de/x", ("u", "p"), sensor="DESIS")
    assert len(s.posted) == 2, "no agreement in it, so no reason to stop"
