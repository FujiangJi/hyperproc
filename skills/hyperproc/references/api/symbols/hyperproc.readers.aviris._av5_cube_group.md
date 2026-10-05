# hyperproc.readers.aviris._av5_cube_group

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _av5_cube_group(path: Path) -> str
```

Name of the group holding the 3-D cube.

AVIRIS-5 does not use one name for it: reflectance sits under
``reflectance/reflectance`` but its uncertainty sits under
``uncertainty/uncertainty``, so the group is looked up rather than guessed.

[Module and aliases](../hyperproc-readers-aviris.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.aviris._av5_cube_group --runtime`.
