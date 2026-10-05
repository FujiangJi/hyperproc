# hyperproc.archive.collections

Release baseline **0.1.2**; source `hyperproc/archive/collections.py`. Choose a callable below rather than loading every declaration.

Which archives hyperproc can search, and which it cannot.

The table below is the whole of the module's knowledge: it maps the
``(sensor, level)`` names the readers already use onto a collection in one of
three archives, so a search result can be handed straight to
:func:`hyperproc.open`.

=========  ==============================  =====================  ==============
backend    archive                         searching              downloading
=========  ==============================  =====================  ==============
``cmr``    NASA Common Metadata Repository anonymous              Earthdata login
``neon``   NEON Data API v0                anonymous              NEON API token
``dlr``    DLR EOC Geoservice STAC         anonymous              EOC account
=========  ==============================  =====================  ==============

Every count in the comments was measured against the archive, not assumed.

**Versions are deliberately not pinned.** EMIT carries two live versions -
249,428 granules at v001 and 23,267 at v002 for the L1B radiance - so pinning
the newest would silently hide nine tenths of the archive. Pass ``version=``
to :func:`hyperproc.search` when you want one.

## Declared callables and classes

- [resolve](symbols/hyperproc.archive.collections.resolve.md)
- [describe](symbols/hyperproc.archive.collections.describe.md)
- [Collection](symbols/hyperproc.archive.collections.Collection.md)

## Constant expressions

- [COLLECTIONS](constants/hyperproc.archive.collections.COLLECTIONS.md)
- [ALIASES](constants/hyperproc.archive.collections.ALIASES.md)
- [LEVEL_NOTES](constants/hyperproc.archive.collections.LEVEL_NOTES.md)
- [ELSEWHERE](constants/hyperproc.archive.collections.ELSEWHERE.md)
- [BACKENDS](constants/hyperproc.archive.collections.BACKENDS.md)
