# hyperproc.atmos.setup.setup

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def setup(base: str | None=None, engines=('sRTMnet',), examples: bool=False, overwrite: bool=False, verbose: bool=True) -> dict
```

Fetch and build what ``engines`` need, then :func:`check`.

Args:
    base: directory to hold every ISOFIT asset. Recorded in
        ``~/.isofit/isofit.ini`` so ISOFIT and every later call find it;
        None keeps the current ini setting (default ``~/.isofit``).
    engines: which engines to provision. ``"sRTMnet"`` (default) is the
        emulator JPL uses operationally and needs 6S compiled underneath.
    examples: also download ISOFIT's tutorial data (~340 MB), useful for
        an end-to-end smoke test of a fresh install.
    overwrite: re-download assets that validate fine.

Raises:
    ImportError: ISOFIT is not installed.
    RuntimeError: a compiler an engine needs is missing.

[Module and aliases](../hyperproc-atmos-setup.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.setup.setup --runtime`.
