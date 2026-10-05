# hyperproc.atmos.inputs.hdr_path

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def hdr_path(binary: Path | str) -> Path
```

The ENVI header beside a binary: ``<file>.hdr``.

Not ``Path.with_suffix(".hdr")``: a PACE file id carries a dot
(``PACE_OCI.20260422T195047_rdn``), so that would write ``PACE_OCI.hdr``
and ISOFIT would not find a header at all.

[Module and aliases](../hyperproc-atmos-inputs.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.inputs.hdr_path --runtime`.
