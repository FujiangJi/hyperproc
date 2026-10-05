# hyperproc.archive.results.Granule

Release baseline **0.1.2**. Fields and declared members below come from the release source. Dataclass/inherited methods may be generated at runtime; inspect the installed class signature when constructing it.

One granule, with the handful of fields a person actually chooses on.

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

## Declared fields

```text
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
```

## Declared members

- [size_gb](hyperproc.archive.results.Granule.size_gb.md)
- [__repr__](hyperproc.archive.results.Granule.__repr__.md)

[Module](../hyperproc-archive-results.md).
