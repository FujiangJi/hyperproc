# hyperproc.archive.dlr.read_policy

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def read_policy(sensor: str, user: str | None=None, password: str | None=None, width: int=88) -> str
```

The policy DLR is waiting on, as readable text.

:func:`sign_in` refuses to agree to an Acceptable Usage Policy on your
behalf, which is only reasonable if you can read the thing. This signs in,
stops at the policy page, and returns what it says - useful on a server
with no browser.

Args:
    sensor: ``"ENMAP"`` or ``"DESIS"`` - they have separate policies.
    user, password: as :func:`credentials`, so the environment works too.
    width: wrap column.

Returns:
    the policy text, or a line saying there is no policy pending.

[Module and aliases](../hyperproc-archive-dlr.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.dlr.read_policy --runtime`.
