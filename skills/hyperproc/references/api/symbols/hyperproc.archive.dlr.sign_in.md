# hyperproc.archive.dlr.sign_in

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def sign_in(session, url: str, auth: tuple[str, str], sensor: str='', accept_policy: bool=False) -> None
```

Sign ``session`` in to DLR, so it can fetch ``url`` and its neighbours.

**The file server does not take HTTP Basic auth.** It answers ``403`` to an
``Authorization`` header - with no ``WWW-Authenticate`` challenge, which is
how you can tell - and redirects everything else to DLR's CAS single
sign-on. So signing in is the form: fetch it, post the credentials with its
one-time ``execution`` token, and come back holding a service ticket. The
session keeps the cookie afterwards, so this happens once however many
files follow.

Args:
    accept_policy: DLR shows an Acceptable Usage Policy once per account
        and will not issue a ticket until it is agreed to. That agreement
        is yours to give, so by default this **stops and says so** rather
        than clicking it for you. Accept it once in a browser, or pass
        ``True`` here to send the acceptance from this session.

Raises:
    PermissionError: if the sign-on refuses, quoting the mission's own
        registration address, or if it is waiting on a policy you have not
        agreed to.

[Module and aliases](../hyperproc-archive-dlr.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.dlr.sign_in --runtime`.
