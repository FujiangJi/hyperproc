# hyperproc.archive.interactive.Map.preview_html

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def preview_html(self, props: dict) -> str
```

The quicklook for one footprint, as a scrap of HTML.

The ``onerror`` fallback matters: CMR lists a browse image for every
PACE granule and none of them were ever written, so the URL is there
and 404s. A broken-image icon says less than a sentence does.

[Module and aliases](../hyperproc-archive-interactive.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.interactive.Map.preview_html --runtime`.
