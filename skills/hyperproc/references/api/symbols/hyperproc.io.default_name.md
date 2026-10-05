# hyperproc.io.default_name

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def default_name(ds: xr.Dataset, suffix: str='', ext: str='.tif') -> str
```

``<stem><suffix><ext>`` - the source filename with .nc swapped out.

Most sensors carry the level in the granule id already
(``EMIT_L2A_RFL_...``), so ``granule`` is enough to name a file uniquely.
AVIRIS ids do not - ``AV320231005t181518`` is the flight line, shared by
L1B and L2A - and the two levels do not always agree: AVIRIS-3 ships a
``bbl`` on L2A and none on L1B, so their band tables genuinely differ.
Readers in that position set ``attrs["stem"]`` to disambiguate rather than
let the second write silently replace the first.

[Module and aliases](../hyperproc-io.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.io.default_name --runtime`.
