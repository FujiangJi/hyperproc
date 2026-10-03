"""The DLR-backed part of :mod:`hyperproc.archive`: EnMAP and DESIS, over STAC.

EnMAP and DESIS are not in NASA's CMR. DLR's Earth Observation Center runs its
own STAC catalogue at https://geoservice.dlr.de/, and it is fully open to
search - 238,494 EnMAP L2A scenes and 14,958 DESIS L2A scenes, each with a
footprint polygon, a cloud fraction and a per-file asset list::

    >>> hits = hp.search("ENMAP", "L2A", bbox=(10, 47, 11.5, 48.5),
    ...                  date=("2023-06-01", "2023-09-30"), cloud=(0, 10))
    >>> hp.download(hits[:1], "data/")

Downloading is not open: the file server redirects to DLR's CAS single sign-on,
and takes no HTTP Basic auth, so :func:`download` carries the login form
through once per mission and keeps the session cookie. Access is granted per
mission - EnMAP at https://www.enmap.org/data_access/, DESIS through EOWEB at
https://eoweb.dlr.de/egp/ - so the two accounts need not be the same; see
:func:`credentials`.

DLR publishes the rasters as cloud-optimised GeoTIFFs, whose names carry an
extra ``_COG`` before the extension. hyperproc's EnMAP reader accepts both
spellings, so a downloaded granule opens with no renaming.
"""
from __future__ import annotations

import fnmatch
import os
import re
import textwrap
import time
from html.parser import HTMLParser
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from hyperproc.archive.collections import resolve
from hyperproc.archive.results import Granule, Results, plural

#: DLR EOC Geoservice STAC. Overridable for testing against a mirror.
BASE = os.environ.get("DLR_STAC_URL", "https://geoservice.dlr.de/eoc/ogc/stac/v1")

#: A download gives up after this many broken connections **in a row that
#: added nothing** to the file. DLR's file server ends a connection after
#: roughly 75 MB, so a 650 MB EnMAP L1C image takes eight or nine of them;
#: counting every break would fail a download that was steadily getting
#: there. A connection that added bytes resets the count and is followed
#: after BACKOFF_S; one that added none waits twice as long as the last.
RETRIES = 5
BACKOFF_S = 5.0

#: Where an account comes from, per mission. Both missions' files sit on one
#: server behind one sign-on, but access is granted separately, through two
#: different front doors - so the two logins need not be the same one.
#: Quoted from each mission's own sign-on page, which states plainly which
#: accounts it accepts - they are not the same two.
SIGNUP = {
    "ENMAP": ("an EnMAP Access Service account (https://www.enmap.org/data_access/); "
              "an EO-Lab account also opens it"),
    "DESIS": ("an EOC Geoservice account - free self-registration at "
              "https://sso.eoc.dlr.de/geoservice/selfservice/register - "
              "or an EOWEB DESIS Science account (https://eoweb.dlr.de/egp/)"),
}
SSO = "https://sso.eoc.dlr.de/"


def needs_login(sensor: str | None = None) -> str:
    """What to do about a refused download, naming the right front door."""
    where = ("\n".join(f"    {k:6s} needs {v}" for k, v in SIGNUP.items())
             if sensor is None
             else f"    {sensor.upper():6s} needs {SIGNUP[sensor.upper()]}")
    env = ("DLR_EOC_USERNAME and DLR_EOC_PASSWORD" if sensor is None
           else f"{sensor.upper()}_USERNAME and {sensor.upper()}_PASSWORD, or "
                "DLR_EOC_USERNAME and DLR_EOC_PASSWORD")
    return (
        "DLR's file server requires an account; searching does not. Access is "
        "granted per mission, so register where the data lives:\n"
        f"{where}\n"
        f"Then set {env}, or add a line to ~/.netrc:\n"
        "    machine download.geoservice.dlr.de login YOU password YOURPASSWORD"
    )


#: Kept for callers that want the general message.
NEEDS_LOGIN = needs_login()

#: The server refuses a page larger than this.
PAGE = 500

_FRACTION = re.compile(r"\.(\d+)")

#: What the readers actually open, by file name rather than by asset key, so
#: one rule covers EnMAP's thirteen assets and DESIS's six.
READER_FILES = ("*-METADATA.*", "*-SPECTRAL_IMAGE*.TIF",
                "*-QL_QUALITY*.TIF", "*-QL_PIXELMASK*.TIF")


def _requests():
    try:
        import requests
    except ImportError as exc:                     # pragma: no cover - environment
        raise ImportError(
            "searching DLR needs requests:\n    pip install 'hyperproc[search]'"
        ) from exc
    return requests


def credentials(user: str | None = None, password: str | None = None,
                sensor: str | None = None):
    """``(user, password)`` from the arguments, the environment or ``~/.netrc``.

    EnMAP and DESIS are served from one host behind one sign-on, but access is
    granted per mission through two different portals, so the accounts can
    differ. ``ENMAP_USERNAME``/``ENMAP_PASSWORD`` and
    ``DESIS_USERNAME``/``DESIS_PASSWORD`` win over the shared
    ``DLR_EOC_*`` pair; ``~/.netrc`` is the last resort and holds only one,
    since both missions share a host.

    Returns ``None`` when there are none, so a caller can raise with an address
    rather than sending an empty login.
    """
    if sensor and not (user and password):
        key = sensor.upper()
        u, p = os.environ.get(f"{key}_USERNAME"), os.environ.get(f"{key}_PASSWORD")
        if u and p:
            return (u, p)
    user = user or os.environ.get("DLR_EOC_USERNAME")
    password = password or os.environ.get("DLR_EOC_PASSWORD")
    if user and password:
        return (user, password)
    try:
        import netrc
        for host in ("download.geoservice.dlr.de", "geoservice.dlr.de", "sso.eoc.dlr.de"):
            found = netrc.netrc().authenticators(host)
            if found and found[0] and found[2]:
                return (found[0], found[2])
    except Exception:                              # no netrc, unreadable, malformed
        pass
    return None


def _page_says(html: str) -> str:
    """The sign-on's own message, so a refusal states its actual reason.

    "Authentication attempt has failed" and "Your account is locked" arrive
    with the same HTTP status, and only one of them means the password was
    wrong.
    """
    text = _visible_text(html)
    # each phrase starts a readable sentence, so the quote does not begin
    # mid-clause; the search is ordered most specific first
    for phrase in ("Authentication attempt has failed", "Authentication Failure",
                   "account is locked", "account has been locked",
                   "has expired", "is expired",
                   "not authorized", "not authorised"):
        i = text.find(phrase)
        if i < 0:
            continue
        # one sentence: the rest of the page is the form's own field labels
        said = text[i:i + 160]
        stop = said.find(". ")
        return (said[:stop] if stop > 0 else said).strip()
    return ""


class _Forms(HTMLParser):
    """Every form on a sign-on page, kept **apart**.

    Keeping them apart is the whole point. DLR's EnMAP sign-on carries two: the
    EOC username/password form, and a hidden one whose only job is to hand you
    off to the EO-Lab identity provider. Merging their fields - as an earlier
    version did - meant posting the delegation form's ``_eventId`` along with
    the credentials, so the sign-on obligingly redirected to EO-Lab's Keycloak
    and the EOC password was never tried. DESIS's page has one form, which is
    why it worked there and not here.
    """

    def __init__(self):
        super().__init__()
        self.forms: list[dict] = []
        self.headings: list[str] = []
        self._cur: dict | None = None
        self._in_heading = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self._cur = {"action": a.get("action"), "fields": {}, "password": False}
            self.forms.append(self._cur)
        elif tag in ("input", "button") and a.get("name") and self._cur is not None:
            if a.get("type") == "submit":
                return                     # a button is clicked, not submitted blind
            self._cur["fields"][a["name"]] = a.get("value", "")
            if a.get("type") == "password" or a["name"] == "password":
                self._cur["password"] = True
        elif tag in ("h1", "h2", "h3"):
            self._in_heading = True

    def handle_endtag(self, tag):
        if tag == "form":
            self._cur = None
        elif tag in ("h1", "h2", "h3"):
            self._in_heading = False

    def handle_data(self, data):
        if self._in_heading and data.strip():
            self.headings.append(" ".join(data.split()))

    @property
    def login(self) -> dict | None:
        """The form that actually asks for a password."""
        return next((f for f in self.forms if f["password"]), None)

    @property
    def step(self) -> dict | None:
        """A form to carry through that is *not* a login - a consent, a hop."""
        return next((f for f in self.forms if not f["password"] and f["fields"]), None)

    @property
    def fields(self) -> dict:
        """Every field on the page, for messages only - never for posting."""
        out: dict[str, str] = {}
        for f in self.forms:
            out.update(f["fields"])
        return out


def _post_to(page_url: str, action: str | None) -> str:
    """Where a form submits to.

    An empty or self-referential ``action`` posts back to the page *including
    its query string*, which is where CAS keeps the ``service`` it is signing
    you in to. ``urljoin`` would drop it.
    """
    if not action:
        return page_url
    target = urljoin(page_url, action)
    return page_url if target == page_url.split("?")[0] else target


#: Headings that mean DLR is asking you to agree to something, not that the
#: login failed. Accepting is the account holder's to do, so it is never
#: submitted without ``accept_policy=True``.
POLICY_WORDS = ("usage policy", "terms of use", "licence", "license", "agreement")


def sign_in(session, url: str, auth: tuple[str, str], sensor: str = "",
            accept_policy: bool = False) -> None:
    """Sign ``session`` in to DLR, so it can fetch ``url`` and its neighbours.

    **The file server does not take HTTP Basic auth.** It answers ``403`` to an
    ``Authorization`` header - with no ``WWW-Authenticate`` challenge, which is
    how you can tell - and redirects everything else to DLR's CAS single
    sign-on. So signing in is the form: fetch it, post the credentials with its
    one-time ``execution`` token, and come back holding a service ticket. The
    session keeps the cookie afterwards, so this happens once however many
    files follow.

    Args:
        accept_policy: DLR shows an Acceptable Usage Policy once per account
            and will not issue a ticket until it is agreed to. That agreement
            is yours to give, so by default this **stops and says so** rather
            than clicking it for you. Accept it once in a browser, or pass
            ``True`` here to send the acceptance from this session.

    Raises:
        PermissionError: if the sign-on refuses, quoting the mission's own
            registration address, or if it is waiting on a policy you have not
            agreed to.
    """
    r = session.get(url, timeout=60, stream=True)
    try:
        if "sso." not in r.url:
            return                                  # already signed in
        page, where = r.text, r.url
    finally:
        r.close()

    found = _Forms()
    found.feed(page)
    form = found.login
    if form is None:                                # pragma: no cover - upstream change
        raise PermissionError(
            f"DLR's sign-on page at {where.split('?')[0]} has no password form this "
            f"version recognises. {needs_login(sensor or None)}")

    xsrf = session.cookies.get("XSRF-TOKEN")
    headers = {"X-XSRF-TOKEN": xsrf} if xsrf else {}
    r = session.post(_post_to(where, form["action"]), timeout=60, headers=headers,
                     data=dict(form["fields"], username=auth[0], password=auth[1]))

    # CAS can put a step between the password and the service ticket - a consent
    # page, a "which account" page, a form a browser would submit with script.
    # None of those ask for a password again, so they are safe to carry through.
    found = _Forms()
    for _ in range(3):
        if "sso." not in r.url:
            return                                  # holding the ticket
        found = _Forms()
        found.feed(r.text)
        if found.login or r.status_code in (401, 403):
            break                                   # back at a login: refused
        nxt = found.step
        if nxt is None:
            break                                   # nothing left to submit

        heading = " ".join(found.headings).lower()
        if any(word in heading for word in POLICY_WORDS) and not accept_policy:
            raise PermissionError(
                f"Your {sensor or 'DLR'} login worked. DLR is now waiting for you "
                f"to agree to its policy - the page is headed "
                f"{', '.join(found.headings[:3])!r}.\n"
                f"That agreement is yours to give, so hyperproc does not click it "
                f"for you. Either:\n"
                f"  - open {url} in a browser, sign in, accept it once, and retry "
                f"here; the account keeps the acceptance, or\n"
                f"  - read it here first:  "
                f"print(hp.archive.dlr.read_policy({(sensor or 'DESIS')!r}))  "
                f"and then pass accept_policy=True, e.g. "
                f"hp.download(hits, out, accept_policy=True)")

        r = session.post(_post_to(r.url, nxt["action"]), data=nxt["fields"],
                         timeout=60, headers=headers)

    said = _page_says(r.text)
    page_is = ", ".join(found.headings[:3])
    raise PermissionError(
        f"DLR's sign-on did not hand back a service ticket for "
        f"{sensor or 'EOC'} (HTTP {r.status_code})"
        + (f"; it said: {said}" if said else "")
        + (f"; the page is headed {page_is!r}" if page_is else "")
        + (f"; it offers the fields {sorted(found.fields)}" if found.fields and not said else "")
        + ".\nThe two missions take different accounts, so an account that opens "
        f"one need not open the other.\n{needs_login(sensor or None)}")


def read_policy(sensor: str, user: str | None = None, password: str | None = None,
                width: int = 88) -> str:
    """The policy DLR is waiting on, as readable text.

    :func:`sign_in` refuses to agree to an Acceptable Usage Policy on your
    behalf, which is only reasonable if you can read the thing. This signs in,
    stops at the policy page, and returns what it says - useful on a server
    with no browser.

    Args:
        sensor: ``"ENMAP"`` or ``"DESIS"`` - they have separate policies.
        user, password: as :func:`credentials`, so the environment works too.
        width: wrap column.

    Returns:
        the policy text, or a line saying there is no policy pending.
    """
    requests = _requests()
    key = sensor.upper()
    auth = credentials(user, password, sensor=key)
    if auth is None:
        raise PermissionError(needs_login(key))

    session = requests.Session()
    session.headers["User-Agent"] = "hyperproc"
    url = f"https://download.geoservice.dlr.de/{key}/files/"
    r = session.get(url, timeout=60, stream=True)
    try:
        if "sso." not in r.url:
            return f"nothing pending: this account already has access to {key}"
        page, where = r.text, r.url
    finally:
        r.close()

    found = _Forms()
    found.feed(page)
    form = found.login
    if form is None:                                # pragma: no cover
        raise PermissionError(f"DLR's sign-on page has no password form. {needs_login(key)}")
    xsrf = session.cookies.get("XSRF-TOKEN")
    r = session.post(_post_to(where, form["action"]), timeout=60,
                     headers={"X-XSRF-TOKEN": xsrf} if xsrf else {},
                     data=dict(form["fields"], username=auth[0], password=auth[1]))
    if r.status_code in (401, 403):
        raise PermissionError(f"DLR's sign-on rejected the {key} login "
                              f"(HTTP {r.status_code}). {needs_login(key)}")
    if "sso." not in r.url:
        return f"nothing pending: this account already has access to {key}"

    found = _Forms()
    found.feed(r.text)
    body = _visible_text(r.text)
    head = ", ".join(found.headings[:3])
    wrapped = "\n".join(textwrap.wrap(body, width=width,
                                      break_long_words=False, break_on_hyphens=False))
    return (f"{head}\n{'-' * len(head)}\n{wrapped}\n\n"
            f"To agree from here, having read it:\n"
            f"    hp.download(hits, out_dir, accept_policy=True)")


def _visible_text(html: str) -> str:
    """The words of a page, with script, style and markup taken out."""
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    return " ".join(re.sub(r"<[^>]+>", " ", text).split())


def _rfc3339(date) -> str | None:
    """``date=`` as a STAC ``datetime`` interval.

    A bare day means the whole day, not midnight, which is the difference
    between finding a scene and not.
    """
    if date is None:
        return None
    if isinstance(date, str):
        date = (date, date)
    a, b = (str(d) for d in date)
    if len(a) == 10:
        a += "T00:00:00Z"
    if len(b) == 10:
        b += "T23:59:59Z"
    return f"{a}/{b}"


def _time_of(props: dict) -> datetime | None:
    """The acquisition time as naive UTC.

    STAC writes fractional seconds with however many digits it has;
    ``fromisoformat`` wants three or six, so they are padded or trimmed first.
    """
    raw = str(props.get("datetime") or props.get("start_datetime") or "")
    if not raw:
        return None
    raw = _FRACTION.sub(lambda m: "." + m.group(1)[:6].ljust(6, "0"), raw)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:                             # pragma: no cover - defensive
        return None


def _links(item: dict, assets: str) -> list[str]:
    """The asset URLs to fetch, in the order the readers want them."""
    hrefs = [a["href"] for a in item.get("assets", {}).values() if a.get("href")]
    if assets == "all":
        return hrefs
    if assets == "image":
        keep = ("*-METADATA.*", "*-SPECTRAL_IMAGE*.TIF")
    elif assets == "reader":
        keep = READER_FILES
    else:
        raise ValueError(f"assets must be 'reader', 'image' or 'all', not {assets!r}")
    out = [h for h in hrefs
           if any(fnmatch.fnmatch(h.rsplit("/", 1)[-1].upper(), p) for p in keep)]
    return out


def search(sensor: str, level: str | None = None, *, bbox=None, date=None,
           cloud: tuple[float, float] | None = None, count: int = 100,
           assets: str = "reader", verbose: bool = True, **kwargs) -> Results:
    """Find EnMAP or DESIS scenes in DLR's STAC catalogue.

    Args:
        sensor: ``"ENMAP"`` or ``"DESIS"``.
        level: EnMAP ``"L1B"`` (unmerged detectors), ``"L1C"`` (orthorectified
            radiance) or ``"L2A"`` (surface reflectance); DESIS ``"L2A"``.
        bbox: ``(west, south, east, north)`` in degrees. **Give one.** The
            catalogue is large and a cloud filter without a box scans it all,
            which times out rather than answering.
        date: ``("YYYY-MM-DD", "YYYY-MM-DD")``, or a single day, which means
            that whole day.
        cloud: ``(min, max)`` percent, from the provider's ``eo:cloud_cover``.
        count: cap on scenes returned. ``-1`` for every match, paged.
        assets: which files each result links to. ``"reader"`` (default) is
            what :func:`hyperproc.open` uses - metadata, the spectral image and
            the quality masks. ``"image"`` drops the masks, ``"all"`` adds the
            browse images and thumbnails.
        verbose: print the query and the total.

    Returns:
        :class:`Results`, newest first. DLR publishes no file sizes, so the
        totals read "size not published" rather than guessing.
    """
    requests = _requests()
    sensor, level, coll = resolve(sensor, level)
    if coll.backend != "dlr":
        raise ValueError(f"{sensor} {level} is not a DLR product")
    if kwargs:
        raise TypeError(f"unexpected argument(s) {sorted(kwargs)} for a DLR search")

    body: dict[str, Any] = {"collections": [coll.short_name]}
    if bbox is not None:
        w, s, e, n = (float(v) for v in bbox)
        if not (-180 <= w <= 180 and -180 <= e <= 180 and -90 <= s <= 90 and -90 <= n <= 90):
            raise ValueError(f"bbox out of range: {bbox}; expected (west, south, east, north) in degrees")
        if w > e or s > n:
            raise ValueError(f"bbox is inside out: {bbox}; expected (west, south, east, north)")
        body["bbox"] = [w, s, e, n]
    when = _rfc3339(date)
    if when:
        body["datetime"] = when
    if cloud is not None:
        lo, hi = (float(c) for c in cloud)
        body["filter-lang"] = "cql2-json"
        body["filter"] = {"op": "and", "args": [
            {"op": ">=", "args": [{"property": "eo:cloud_cover"}, lo]},
            {"op": "<=", "args": [{"property": "eo:cloud_cover"}, hi]}]}
        if bbox is None:
            raise ValueError(
                "a cloud filter without bbox= scans the whole catalogue and times "
                "out on DLR's side; give a bounding box as well")

    if verbose:
        shown = {"bbox": bbox, "date": when, "cloud": cloud}
        shown = {k: v for k, v in shown.items() if v is not None}
        print(f"searching {coll.short_name} ({sensor} {level}){':' if shown else ''}"
              + "".join(f"\n    {k} = {v}" for k, v in shown.items()))

    want = float("inf") if count is None or count < 0 else int(count)
    items: list[dict] = []
    matched = None
    start = 0
    while len(items) < want:
        page = dict(body, limit=min(PAGE, want - len(items)), startIndex=start)
        r = requests.post(f"{BASE}/search", json=page, timeout=180,
                          headers={"accept": "application/geo+json"})
        r.raise_for_status()
        got = r.json()
        matched = got.get("numberMatched", matched)
        batch = got.get("features", [])
        items += batch
        start += len(batch)
        if len(batch) < page["limit"]:
            break

    out = Results((_granule(it, sensor, level, coll.short_name, assets) for it in items),
                  {"collection": coll.short_name, "bbox": bbox, "datetime": when,
                   "cloud": cloud}, note=coll.note)
    if verbose:
        extra = (f" of {matched:,d} matching" if matched and matched > len(out) else "")
        print(f"  {out!r}{extra}")
        if not out and coll.note:
            print("  note:", coll.note)
    return out


def _granule(item: dict, sensor: str, level: str, collection: str,
             assets: str = "reader") -> Granule:
    props = item.get("properties", {})
    cloud = props.get("eo:cloud_cover")
    bbox = item.get("bbox")
    return Granule(
        name=item.get("id", "?"),
        sensor=sensor, level=level, collection=collection,
        version=props.get("version") or props.get("processing:version"),
        time=_time_of(props),
        bbox=tuple(bbox[:2] + bbox[-2:]) if bbox and len(bbox) >= 4 else None,
        size_mb=None,
        cloud=float(cloud) if cloud is not None else None,
        links=_links(item, assets), raw=item,
    )


def _content_range(r) -> tuple[int | None, int | None]:
    """``(first byte, total size)`` from a 206 or 416 answer, None where absent."""
    m = re.match(r"bytes\s+(?:(\d+)-\d+|\*)/(\d+)", r.headers.get("Content-Range", ""))
    if not m:
        return None, None
    return (int(m.group(1)) if m.group(1) else None), int(m.group(2))


def _retryable(exc: BaseException) -> bool:
    """A dropped or stalled connection, or the server failing on its own side."""
    from requests import exceptions as rex
    if isinstance(exc, (rex.ChunkedEncodingError, rex.ConnectionError, rex.Timeout)):
        return True
    resp = getattr(exc, "response", None)
    return isinstance(exc, rex.HTTPError) and resp is not None and resp.status_code >= 500


def _stream(session, url: str, dest: Path, tmp: Path, key: str,
            seen: dict | None = None) -> int:
    """Write ``url`` into ``tmp``, carrying on from whatever ``tmp`` already holds.

    The rest is asked for with a Range header. A server that honours it
    answers 206 and the bytes are appended; one that ignores it answers 200
    with the whole file, which then overwrites the partial one - appending a
    second full copy would make a file that looks finished and is not.

    Compression is refused (``Accept-Encoding: identity``) because byte ranges
    and the announced size count the bytes on the wire, and a decoded stream
    would match neither.

    ``seen["appending"]`` is set before the first byte is written, so a caller
    whose transfer then breaks can tell bytes added from a file rewritten.

    Returns the byte the transfer resumed at, 0 when the file came whole.

    Raises:
        requests.exceptions.ChunkedEncodingError: fewer bytes arrived than the
            server announced, so a short file is retried rather than renamed
            into place looking finished.
    """
    from requests import exceptions as rex

    have = tmp.stat().st_size if tmp.exists() else 0
    headers = {"Accept-Encoding": "identity"}
    if have:
        headers["Range"] = f"bytes={have}-"
    with session.get(url, stream=True, timeout=300, headers=headers) as r:
        if r.status_code in (401, 403) or "sso." in r.url:
            raise PermissionError(
                f"DLR refused {dest.name} after signing in - the account is "
                f"probably not cleared for {key}. {needs_login(key)}")
        if r.status_code == 416:                   # nothing past `have` to send
            _, total = _content_range(r)
            if total == have:
                return have                        # the partial file was whole
            tmp.unlink()
            raise rex.ChunkedEncodingError(
                f"{tmp.name} holds {have:,d} bytes of a {total or '?'}-byte file; "
                f"starting it again")
        r.raise_for_status()
        start, total = 0, None
        if r.status_code == 206:
            start, total = _content_range(r)
            if start != have:
                tmp.unlink()
                raise rex.ChunkedEncodingError(
                    f"asked for byte {have:,d} and was sent byte {start}; "
                    f"starting {dest.name} again")
        elif "Content-Length" in r.headers and not r.headers.get("Content-Encoding"):
            total = int(r.headers["Content-Length"])
        if seen is not None:
            seen["appending"] = bool(start)
        with open(tmp, "ab" if start else "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
    got = tmp.stat().st_size
    if total is not None and got != total:
        raise rex.ChunkedEncodingError(
            f"{got:,d} of {total:,d} bytes of {dest.name} arrived")
    return start


def download(results, out_dir: str | Path = "data", workers: int = 4,
             user: str | None = None, password: str | None = None,
             accept_policy: bool = False, verbose: bool = True) -> list[Path]:
    """Fetch EnMAP or DESIS files into ``out_dir``. Needs an EOC account.

    Every file of a granule lands in the one directory, which is what the
    readers expect: an EnMAP GeoTIFF carries no wavelengths of its own and
    finds them in the ``METADATA.XML`` beside it.

    A result set mixing EnMAP and DESIS is fine: each mission is fetched with
    its own account if you have set one, since DLR grants access to the two
    separately. See :func:`credentials`.

    ``accept_policy=True`` agrees to DLR's Acceptable Usage Policy from here;
    without it, a pending policy stops the download and says where to read it.

    A file whose connection breaks is resumed from the bytes already written,
    where the server allows it, for as long as each connection adds some; it
    gives up after :data:`RETRIES` breaks in a row that add nothing. Until it
    is whole it sits beside its final name as ``*.part``, so a later call
    carries on from it too, and a file shorter than the server announced is
    never renamed into place.
    """
    requests = _requests()
    if isinstance(results, Granule):
        results = [results]
    items = list(results)
    jobs = [(g, url) for g in items for url in g.links]
    if not jobs:
        if verbose:
            print("nothing to download")
        return []

    # a mixed EnMAP/DESIS result set uses each mission's own account
    auth_for: dict[str, tuple[str, str]] = {}
    for g in items:
        key = g.sensor.upper()
        if key not in auth_for:
            got = credentials(user, password, sensor=key)
            if got is None:
                raise PermissionError(needs_login(key))
            auth_for[key] = got

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if verbose:
        print(f"downloading {plural(len(items), 'granule')}, "
              f"{plural(len(jobs), 'file')} -> {out}")

    # one session per mission, each signed in once before any file is fetched,
    # because the two accounts can differ and a session holds only one
    sessions: dict[str, Any] = {}
    for key, auth in auth_for.items():
        first = next(url for g, url in jobs if g.sensor.upper() == key)
        sessions[key] = requests.Session()
        sessions[key].headers["User-Agent"] = "hyperproc"
        sign_in(sessions[key], first, auth, sensor=key,
                accept_policy=accept_policy)
        if verbose:
            print(f"  signed in to DLR for {key}")

    def fetch(job) -> Path:
        granule, url = job
        key = granule.sensor.upper()
        dest = out / url.rsplit("/", 1)[-1]
        if dest.exists() and dest.stat().st_size > 0:
            return dest
        tmp = dest.with_suffix(dest.suffix + ".part")
        stalls = 0                          # breaks in a row that added nothing
        while True:
            had = tmp.stat().st_size if tmp.exists() else 0
            seen: dict = {}
            try:
                start = _stream(sessions[key], url, dest, tmp, key, seen)
                break
            except Exception as exc:
                if not _retryable(exc):
                    raise
                held = tmp.stat().st_size if tmp.exists() else 0
                # Progress is bytes added. A server that ignores Range rewrites
                # the file from 0, which is not progress however far it gets -
                # counting it would let such a server loop for ever.
                added = held > had and (seen.get("appending") or had == 0)
                stalls = 0 if added else stalls + 1
                if stalls > RETRIES:
                    raise ConnectionError(
                        f"{dest.name}: {stalls} connections in a row broke without "
                        f"adding a byte ({type(exc).__name__}: {exc}). The "
                        f"{held / 1e6:,.0f} MB that arrived are kept in "
                        f"{tmp.name}, and a later download carries on from "
                        f"there.") from exc
                wait = BACKOFF_S * 2 ** stalls
                if verbose:
                    count = "" if added else f", {stalls} of {RETRIES} with no progress"
                    print(f"  {dest.name}: connection broke at {held / 1e6:,.0f} MB "
                          f"({type(exc).__name__}); resuming in {wait:.0f} s{count}")
                time.sleep(wait)
        tmp.replace(dest)
        if verbose:
            note = (f"  (resumed at {start / 1e6:,.0f} MB)" if start else
                    "  (the server would not resume, so it came whole)" if had else "")
            print(f"  {dest.name}  {dest.stat().st_size / 1e6:,.0f} MB{note}")
        return dest

    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
        paths = list(pool.map(fetch, jobs))

    if verbose:
        print(f"  {plural(len(paths), 'file')} in {out}")
    return paths
