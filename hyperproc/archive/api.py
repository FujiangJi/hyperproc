"""One ``search`` and one ``download`` over three archives.

The backend is decided by what you asked for, not by which function you called:
:func:`hyperproc.search` looks the ``(sensor, level)`` pair up in
:data:`hyperproc.archive.COLLECTIONS` and hands the query to CMR, NEON or DLR.
The three return the same :class:`~hyperproc.archive.results.Granule`, so the
rest of a workflow does not care which answered.
"""
from __future__ import annotations

import os
from pathlib import Path

from hyperproc.archive import cmr, dlr, neon
from hyperproc.archive.collections import BACKENDS, resolve
from hyperproc.archive.results import Granule, Results

_BACKEND = {"cmr": cmr, "neon": neon, "dlr": dlr}

#: Arguments each backend's ``download`` takes beyond ``(results, out_dir,
#: workers, verbose)``. Passing one to a backend that has no use for it is a
#: mistake worth naming rather than ignoring.
_DOWNLOAD_ARGS = {
    "cmr": (),
    "neon": ("token", "pattern"),
    "dlr": ("user", "password", "accept_policy"),
}


def search(sensor: str, level: str | None = None, **kwargs) -> Results:
    """Find granules in whichever archive publishes them.

    Args:
        sensor: ``"EMIT"``, ``"PACE"``, ``"AVIRIS-3"``, ``"AVIRIS-5"``,
            ``"NEON"``, ``"ENMAP"``, ``"DESIS"``. The reader spellings work too
            (``"aviris3"``, ``"oci"``).
        level: ``"L1B"``/``"L1"`` for radiance, ``"L2A"``/``"L2"`` for
            reflectance. Required where a sensor has more than one searchable
            level. :func:`describe` prints the table.
        bbox: ``(west, south, east, north)`` in degrees.
        date: ``("YYYY-MM-DD", "YYYY-MM-DD")``, or a single date. NEON
            deliveries are monthly, so dates there are truncated to the month.
        cloud: ``(min, max)`` percent, where the provider reports it - EMIT,
            PACE, EnMAP and DESIS do; the AVIRIS collections and NEON do not.
        count: cap on results, default 100. ``-1`` for every match.
        verbose: print the query and the total.

    Backend-specific arguments are accepted too and documented on the backend:
    ``version=`` (CMR), ``site=`` and ``site_radius_km=`` (NEON), ``assets=``
    (DLR).

    Returns:
        :class:`~hyperproc.archive.results.Results`.

    Raises:
        ValueError: for a sensor no archive here carries, with the address of
            the archive that does.
    """
    _, _, coll = resolve(sensor, level)
    return _BACKEND[coll.backend].search(sensor, level, **kwargs)


def download(results, out_dir: str | Path = "data", workers: int = 8, *,
             token: str | None = None, user: str | None = None,
             password: str | None = None, pattern: str | None = None,
             accept_policy: bool = False, verbose: bool = True) -> list[Path]:
    """Fetch what a search found, from whichever archives it came from.

    Args:
        results: a :class:`~hyperproc.archive.results.Results`, a list of
            granules, or one granule. A mixture of archives is fine; each group
            goes to its own backend.
        out_dir: created if missing. Everything lands flat, which is what the
            readers expect - they find a granule's siblings by name.
        workers: parallel connections.
        token: NEON API token, else ``NEON_TOKEN``.
        user, password: DLR EOC account, else ``DLR_EOC_USERNAME`` /
            ``DLR_EOC_PASSWORD``, else ``~/.netrc``.
        pattern: NEON only - which files inside a site-month delivery to take.
        accept_policy: DLR only - agree to its Acceptable Usage Policy from
            here. Left ``False``, a pending policy stops the download and says
            where to read it, because agreeing to it is yours to do.

    Returns:
        the downloaded paths.

    Credentials differ by archive and none of them are needed to search:
    Earthdata for EMIT, PACE and AVIRIS; a NEON API token since June 2026; a
    DLR EOC account for EnMAP and DESIS. Each backend raises with its own
    registration address when it has none.
    """
    if isinstance(results, Granule):
        results = [results]
    items = list(results)
    if not items:
        if verbose:
            print("nothing to download")
        return []

    groups: dict[str, list] = {}
    for g in items:
        _, _, coll = resolve(g.sensor, g.level)
        groups.setdefault(coll.backend, []).append(g)

    extra = {"token": token, "user": user, "password": password, "pattern": pattern,
             "accept_policy": accept_policy or None}
    given = {k for k, v in extra.items() if v is not None}
    for backend in groups:
        stray = given - set(_DOWNLOAD_ARGS[backend])
        if stray and len(groups) == 1:
            who = BACKENDS[backend][0]
            raise TypeError(f"{sorted(stray)} means nothing to {who}; it takes "
                            f"{list(_DOWNLOAD_ARGS[backend]) or 'no extra credentials'}")

    paths: list[Path] = []
    for backend, part in groups.items():
        if verbose and len(groups) > 1:
            print(f"[{BACKENDS[backend][0]}]")
        kw = {k: extra[k] for k in _DOWNLOAD_ARGS[backend] if extra[k] is not None}
        paths += _BACKEND[backend].download(part, out_dir, workers=workers,
                                            verbose=verbose, **kw)
    return paths


def credentials() -> dict[str, bool]:
    """Which archives this process could download from. Never returns a secret.

    The DLR entries are **per mission**, because DLR grants EnMAP and DESIS
    separately and an account for one need not open the other. A single
    "have I got DLR credentials" flag reads True when you hold only one of
    them, and then waves the other through to a refusal.

        >>> hp.archive.credentials()
        {'cmr': True, 'neon': False, 'ENMAP': False, 'DESIS': True}
    """
    import netrc as _netrc

    def in_netrc(host: str) -> bool:
        try:
            return _netrc.netrc().authenticators(host) is not None
        except Exception:          # absent, unreadable, malformed
            return False

    return {
        "cmr": bool(os.environ.get("EARTHDATA_USERNAME")
                    or os.environ.get("EARTHDATA_TOKEN")
                    or in_netrc("urs.earthdata.nasa.gov")),
        "neon": neon.token_from() is not None,
        "ENMAP": dlr.credentials(sensor="ENMAP") is not None,
        "DESIS": dlr.credentials(sensor="DESIS") is not None,
    }


def can_download(sensor: str, level: str | None = None) -> bool:
    """Could this process fetch bytes for this collection, as things stand?

    Answers the question :func:`download` would otherwise answer by failing.
    Says nothing about whether the account is *cleared* for the data - only
    DLR can say that, and only when asked.
    """
    sensor, level, coll = resolve(sensor, level)
    have = credentials()
    return have[sensor] if coll.backend == "dlr" else have[coll.backend]


def files(results, **kwargs) -> Results:
    """Open a NEON site-month delivery up into the flightlines inside it.

    For CMR and DLR a granule already *is* its files - the links are on it - so
    this returns what it was given, unchanged. That way one script works
    against every archive.

    See :func:`hyperproc.archive.neon.files` for ``token=`` and ``pattern=``.
    """
    items = [results] if isinstance(results, Granule) else list(results)
    if not items:
        return Results([])
    backends = {resolve(g.sensor, g.level)[2].backend for g in items}
    if backends == {"neon"}:
        return neon.files(items, **kwargs)
    if "neon" in backends:
        raise ValueError("files() takes NEON deliveries on their own; "
                         f"this mixes {sorted(backends)}")
    return results if isinstance(results, Results) else Results(items)
