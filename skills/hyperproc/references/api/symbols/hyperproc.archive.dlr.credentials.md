# hyperproc.archive.dlr.credentials

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def credentials(user: str | None=None, password: str | None=None, sensor: str | None=None)
```

``(user, password)`` from the arguments, the environment or ``~/.netrc``.

EnMAP and DESIS are served from one host behind one sign-on, but access is
granted per mission through two different portals, so the accounts can
differ. ``ENMAP_USERNAME``/``ENMAP_PASSWORD`` and
``DESIS_USERNAME``/``DESIS_PASSWORD`` win over the shared
``DLR_EOC_*`` pair; ``~/.netrc`` is the last resort and holds only one,
since both missions share a host.

Returns ``None`` when there are none, so a caller can raise with an address
rather than sending an empty login.

[Module and aliases](../hyperproc-archive-dlr.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.dlr.credentials --runtime`.
