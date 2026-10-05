# hyperproc.archive.dlr._stream

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _stream(session, url: str, dest: Path, tmp: Path, key: str, seen: dict | None=None) -> int
```

Write ``url`` into ``tmp``, carrying on from whatever ``tmp`` already holds.

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

[Module and aliases](../hyperproc-archive-dlr.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.dlr._stream --runtime`.
