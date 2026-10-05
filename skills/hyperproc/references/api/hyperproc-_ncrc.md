# hyperproc._ncrc

Release baseline **0.1.2**; source `hyperproc/_ncrc.py`. Choose a callable below rather than loading every declaration.

netCDF rc files whose last line has no newline, and why that matters here.

netCDF-C reads ``.ncrc``, ``.daprc`` and ``.dodsrc`` from the home directory
and the working directory when ``netCDF4`` is imported - not when a remote
file is opened, but at import. A last line with no trailing newline makes its
parser read and write past the end of its buffer.

Whether that shows depends on the allocator. On glibc the stray bytes usually
land in slack and nothing happens, so the fault sits there unseen. macOS packs
small allocations tightly and checks them, so the same file corrupts the heap:
measured at roughly one import in fifteen. ISOFIT starts a Ray worker per core
and every one of them imports netCDF4, which turns a one-in-fifteen chance into
a near-certain crash somewhere in a long retrieval, at a different place each
time.

``earthaccess`` writes ``~/.dodsrc`` on ``login(persist=True)`` and ends it
without a newline (``auth.py``: ``f"HTTP.COOKIEJAR={...}\nHTTP.NETRC={...}"``),
so a machine that has ever signed in to Earthdata through it has the file in
exactly the state that triggers this. The bug is netCDF-C's and the file is
earthaccess's; hyperproc only drives both, and says so rather than letting a
retrieval die at random.

## Declared callables and classes

- [unterminated_rc_files](symbols/hyperproc._ncrc.unterminated_rc_files.md) — internal
- [rc_warning](symbols/hyperproc._ncrc.rc_warning.md) — internal
- [terminate_rc_file](symbols/hyperproc._ncrc.terminate_rc_file.md) — internal

## Constant expressions

- [NC_RC_NAMES](constants/hyperproc._ncrc.NC_RC_NAMES.md)
