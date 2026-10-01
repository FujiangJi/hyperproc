"""What a search returns, whichever archive answered it.

Three archives back :mod:`hyperproc.archive` - NASA's CMR, NEON's own API and
DLR's STAC catalogue - and they describe a granule in three different
vocabularies. :class:`Granule` is the small common part: what it is called,
where and when it was taken, how big it is and where to fetch it. Everything
the backend knows and this does not stays in ``raw``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Sequence


def plural(n: int, word: str) -> str:
    """``"1 granule"``, ``"2 granules"`` - a download line reads badly otherwise."""
    return f"{n} {word}" + ("" if n == 1 else "s")


@dataclass
class Granule:
    """One granule, with the handful of fields a person actually chooses on.

    Attributes:
        name: the granule identifier the archive uses.
        sensor, level: the ``(sensor, level)`` pair :func:`hyperproc.open` uses,
            so a result can be handed straight to the reader once downloaded.
        collection: the archive's own collection id - a CMR ``ShortName``, a
            NEON product code, a STAC collection.
        version: collection version where the archive states one.
        time: acquisition start, naive UTC.
        bbox: ``(west, south, east, north)`` in degrees, or ``None``.
        size_mb: ``None`` where the archive does not publish a size. NEON
            deliveries and DLR items do not; CMR does.
        cloud: percent cloud where the provider reports it, else ``None``.
        links: every file to fetch. For EMIT L2A that is the reflectance, the
            mask and the uncertainty - the siblings :func:`hyperproc.open`
            looks for once they sit in one directory. Empty where the archive
            needs a second, authenticated call to list them.
        browse: a public quicklook image, where the archive publishes one that
            can be fetched without a login. EMIT and the AVIRIS collections do;
            PACE's browse URLs 404; DLR's thumbnails sit behind its sign-on and
            NEON publishes none per delivery, so those are ``None``.
        raw: the backend's own record, kept whole.
    """
    name: str
    sensor: str
    level: str
    collection: str
    version: str | None
    time: datetime | None
    bbox: tuple[float, float, float, float] | None
    size_mb: float | None
    cloud: float | None
    links: list[str] = field(default_factory=list)
    browse: str | None = None
    raw: Any = field(default=None, repr=False)

    @property
    def size_gb(self) -> float | None:
        return None if self.size_mb is None else self.size_mb / 1024.0

    def __repr__(self) -> str:
        when = self.time.strftime("%Y-%m-%d %H:%M") if self.time else "unknown time"
        size = f"{self.size_mb:,.0f} MB" if self.size_mb is not None else "size unpublished"
        cloud = f", {self.cloud:.0f}% cloud" if self.cloud is not None else ""
        return f"<{self.name}  {when}, {size}{cloud}>"


class Results(Sequence):
    """What a search found: a sequence of :class:`Granule`, with a readable total.

    Slices and indexes like a list, so ``hits[:3]`` is the first three and
    ``hits[0]`` is one granule.
    """

    def __init__(self, granules: Iterable[Granule], query: dict | None = None,
                 note: str = ""):
        self._g = list(granules)
        self.query = dict(query or {})
        #: printed under an empty or surprising result, where the reason is a
        #: property of the archive rather than of the query
        self.note = note

    def __len__(self) -> int:
        return len(self._g)

    def __getitem__(self, i):
        return (Results(self._g[i], self.query, self.note)
                if isinstance(i, slice) else self._g[i])

    def __iter__(self):
        return iter(self._g)

    @property
    def size_gb(self) -> float:
        """Total of the sizes that are known. See :attr:`unsized`."""
        return sum(g.size_mb for g in self._g if g.size_mb is not None) / 1024.0

    @property
    def unsized(self) -> int:
        """How many granules the archive gave no size for."""
        return sum(1 for g in self._g if g.size_mb is None)

    def _total(self) -> str:
        n = plural(len(self._g), "granule")
        if self.unsized == len(self._g) and self._g:
            return f"{n}, size not published"
        if self.unsized:
            return f"{n}, {self.size_gb:,.1f} GB + {self.unsized} unsized"
        return f"{n}, {self.size_gb:,.1f} GB"

    def __repr__(self) -> str:
        if not self._g:
            return "no granules"
        return self._total()

    def table(self) -> str:
        """One line per granule: the listing you read before downloading."""
        if not self._g:
            q = ", ".join(f"{k}={v}" for k, v in self.query.items() if v is not None)
            return f"no granules matched ({q})"
        rows = [f"{'granule':52s} {'when':16s} {'size':>9s}  cloud", "-" * 92]
        for g in self._g:
            when = g.time.strftime("%Y-%m-%d %H:%M") if g.time else "-"
            cloud = f"{g.cloud:.0f}%" if g.cloud is not None else "-"
            size = f"{g.size_mb:8,.0f}M" if g.size_mb is not None else "       -"
            rows.append(f"{g.name[:52]:52s} {when:16s} {size}  {cloud:>5s}")
        rows.append("-" * 92)
        rows.append(f"{self._total()} total")
        return "\n".join(rows)

    def to_geodataframe(self):
        """The footprints as a GeoDataFrame, for plotting. Needs geopandas."""
        try:
            import geopandas as gpd
            from shapely.geometry import box
        except ImportError as exc:                 # pragma: no cover - environment
            raise ImportError(
                "to_geodataframe needs geopandas:\n    pip install 'hyperproc[search-map]'"
            ) from exc
        rows, geoms = [], []
        for g in self._g:
            if g.bbox is None:
                continue
            rows.append({"name": g.name, "sensor": g.sensor, "level": g.level,
                         "time": g.time, "size_mb": g.size_mb, "cloud": g.cloud,
                         "version": g.version, "browse": g.browse,
                         "url": g.links[0] if g.links else None})
            geoms.append(box(*g.bbox))
        return gpd.GeoDataFrame(rows, geometry=geoms, crs="EPSG:4326")
