# hyperproc.readers.neon._H5Array

Release baseline **0.1.2**. Fields and declared members below come from the release source. Dataclass/inherited methods may be generated at runtime; inspect the installed class signature when constructing it.

Array-like view of one HDF5 dataset that reopens the file for every
read. The dask graph then holds only a path and a dataset name: it can be
pickled (distributed / process schedulers), and no file handle is left
open after ``hyperproc.open`` returns.

## Declared members

- [__init__](hyperproc.readers.neon._H5Array.__init__.md)
- [__getitem__](hyperproc.readers.neon._H5Array.__getitem__.md)

[Module](../hyperproc-readers-neon.md).
