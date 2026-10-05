# hyperproc.atmos.correct.resolve_surface

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def resolve_surface(inputs: Inputs, surface=None, cache: bool=True) -> tuple[Path, Path | None]
```

``(surface_path_to_pass, cached_mat_to_fill)``.

Building the five-library prior takes a couple of minutes and depends only
on the wavelength grid, so the built ``.mat`` is cached per sensor and
grid under ``~/.cache/hyperproc/surface`` (``HYPERPROC_CACHE_DIR`` to move
it). When the cache has it, the ``.mat`` is passed and nothing is rebuilt.

[Module and aliases](../hyperproc-atmos-correct.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.correct.resolve_surface --runtime`.
