"""netCDF rc files whose last line has no newline, and why that matters here.

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
without a newline (``auth.py``: ``f"HTTP.COOKIEJAR={...}\\nHTTP.NETRC={...}"``),
so a machine that has ever signed in to Earthdata through it has the file in
exactly the state that triggers this. The bug is netCDF-C's and the file is
earthaccess's; hyperproc only drives both, and says so rather than letting a
retrieval die at random.
"""
from __future__ import annotations

from pathlib import Path

#: Read by netCDF-C at import, in this order, from the home and working dirs.
NC_RC_NAMES = (".ncrc", ".daprc", ".dodsrc")


def unterminated_rc_files(*dirs) -> list[Path]:
    """Those of :data:`NC_RC_NAMES` in ``dirs`` whose last byte is not a newline.

    ``dirs`` defaults to the home directory. An empty file is fine - there is
    no last line to run off the end of. Unreadable paths are skipped: this is
    a diagnostic, and it must never be the thing that fails.
    """
    found = []
    for d in dirs or (Path.home(),):
        for name in NC_RC_NAMES:
            p = Path(d) / name
            try:
                data = p.read_bytes()
            except OSError:
                continue
            if data and not data.endswith(b"\n"):
                found.append(p)
    return found


def rc_warning(paths) -> str:
    """What to tell someone about ``paths``, including the one-line fix."""
    listed = ", ".join(str(p) for p in paths)
    fix = "  ".join(f"printf '\\n' >> {p}" for p in paths)
    return (f"{listed} has no newline after its last line. netCDF-C reads past "
            f"the end of such a file when netCDF4 is imported, which crashes "
            f"ISOFIT's Ray workers at random on macOS (SIGSEGV or SIGBUS, in a "
            f"different place each run) and corrupts memory silently elsewhere. "
            f"Fix it with:\n    {fix}\n"
            f"Nothing else about the file changes. Setting NCRCENV_RC to a "
            f"newline-terminated copy also works and leaves the original alone.")


def terminate_rc_file(path) -> bool:
    """Append the missing newline to ``path``. True when it wrote one."""
    p = Path(path)
    data = p.read_bytes()
    if not data or data.endswith(b"\n"):
        return False
    with open(p, "ab") as fh:
        fh.write(b"\n")
    return True
