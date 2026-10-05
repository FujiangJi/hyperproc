# hyperproc.readers.aviris.read_hdr

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def read_hdr(path: str | Path) -> dict[str, str]
```

Parse an ENVI ``.hdr`` into a dict of raw strings.

Handles the quirks in the AVIRIS family: brace-delimited values spanning
many lines, leading whitespace on keys (Classic indents ``wavelength`` and
``fwhm``), and ``map info ={`` with no space before the brace.

[Module and aliases](../hyperproc-readers-aviris.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.aviris.read_hdr --runtime`.
