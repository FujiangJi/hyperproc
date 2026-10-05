# hyperproc.archive.collections.Collection

Release baseline **0.1.2**. Fields and declared members below come from the release source. Dataclass/inherited methods may be generated at runtime; inspect the installed class signature when constructing it.

One searchable archive entry.

Attributes:
    short_name: the collection id in its own archive - a CMR ``ShortName``,
        a NEON product code, a STAC collection id.
    what: the product, in the provider's words.
    granules: granules in the archive when this table was written, as a
        rough guide to what a broad search will return.
    backend: which of ``"cmr"``, ``"neon"``, ``"dlr"`` answers the query.
    cloud: whether the provider publishes a cloud fraction for this
        collection. Measured, not assumed, and not a property of the
        sensor: PACE reports one at L2 and none at L1B. A ``cloud=``
        filter on a collection that reports none can only ever match
        nothing, so :func:`hyperproc.search` refuses it.
    siblings: the extra files a granule carries. hyperproc's readers find
        these themselves once they are beside the main file, so the
        download brings what :func:`hyperproc.open` needs.

## Declared fields

```text
short_name: str
what: str
granules: int
backend: str = 'cmr'
cloud: bool = True
siblings: tuple[str, ...] = ()
note: str = ''
```

## Declared members


[Module](../hyperproc-archive-collections.md).
