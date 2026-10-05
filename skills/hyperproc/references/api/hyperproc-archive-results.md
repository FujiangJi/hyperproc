# hyperproc.archive.results

Release baseline **0.1.2**; source `hyperproc/archive/results.py`. Choose a callable below rather than loading every declaration.

What a search returns, whichever archive answered it.

Three archives back :mod:`hyperproc.archive` - NASA's CMR, NEON's own API and
DLR's STAC catalogue - and they describe a granule in three different
vocabularies. :class:`Granule` is the small common part: what it is called,
where and when it was taken, how big it is and where to fetch it. Everything
the backend knows and this does not stays in ``raw``.

## Declared callables and classes

- [plural](symbols/hyperproc.archive.results.plural.md)
- [Granule](symbols/hyperproc.archive.results.Granule.md)
- [Results](symbols/hyperproc.archive.results.Results.md)
