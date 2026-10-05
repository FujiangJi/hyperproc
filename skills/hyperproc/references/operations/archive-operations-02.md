## Search versus authenticated operations

Anonymous bounded search is different from listing/download/authentication. NEON site-month results expand through `hp.files` to reflectance flightlines using `NEON_TOKEN`; filtering is month-granular. CMR/DLR `files` preserves existing records. Review requested scene IDs, primary/ancillary files, size and disk before a large transfer.

`hp.archive.credentials()` reports availability without secrets; `can_download(sensor,level)` is a local preflight, not actual provider authentication verification. CMR login can prompt and some authentication paths can persist credentials. DLR uses CAS, not Basic Auth. Mission approvals and EnMAP/DESIS accounts may differ. A provider policy must actually be reviewed/accepted by the user; do not silently set `accept_policy=True` merely to clear an error. Existing explicit authorization persists; avoid redundant approval loops.

Keep tokens/passwords in appropriate existing environment/configuration, never generated scripts, output manifests, notebook cells, logs or copied `raw` payloads. Inspect credential-like data before serializing provider metadata. The inspection helper intentionally rejects credential-like reader-option keys.
