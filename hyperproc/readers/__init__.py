"""One module per sensor. Each exposes ``open_<sensor>(path, **kw) -> xr.Dataset``.

Import them from here or let :func:`hyperproc.open` dispatch for you.
"""

from hyperproc.readers.aviris import (check_geometry, fix_slope_convention,
                                     open_aviris)
from hyperproc.readers.desis import open_desis
from hyperproc.readers.emit import open_emit
from hyperproc.readers.enmap import open_enmap
from hyperproc.readers.neon import open_neon
from hyperproc.readers.pace import open_pace
from hyperproc.readers.prisma import open_prisma
from hyperproc.readers.tanager import open_tanager

__all__ = ["check_geometry", "fix_slope_convention", "open_aviris", "open_desis", "open_emit", "open_enmap", "open_neon", "open_pace", "open_prisma",
           "open_tanager"]
