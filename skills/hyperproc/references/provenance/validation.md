# Validation scope for the merged skill

The reviewed baseline is the released PyPI **hyperproc 0.1.2** wheel, verified against its published SHA256 and all 54 Python modules. [Release identity](release-manifest.json) and [per-module source coverage](api-inventory.json) retain source hashes, exact symbol-reference locations and declared API counts.

The merged edition has no mirrored website article bodies. Earlier review retrieved 120 linked published pages; per-page URL/HTML hash evidence remains in small `website-review/` batches. Operational guidance is maintained once, API signatures/docstrings are stored per symbol, and installed-source/runtime helpers support later compatible versions.

Run the bundled validator using an existing scientific interpreter:

```bash
python /path/to/hyperproc/scripts/validate_bundle.py
python /path/to/hyperproc/scripts/validate_bundle.py --runtime
```

`--source-root` optionally verifies an already extracted reviewed wheel tree against the source hashes; it does not fetch it. `--output` writes a new evidence JSON when requested. Ordinary processing does not depend on a developer's temporary wheel directory or validation environment.

Checks cover reference reachability, a maximum of 900 words per Markdown instruction/reference, Python syntax, complete AST function/class/member signatures when the source tree is supplied, live installed signature/registry/alias behavior, metadata inspection without cube computation, bounded sampling, known-answer synthetic QA/NDVI, unknown download-size handling, distinct scene/window work identities, credential-like setting rejection, and raster QA/reflectance round trips.

OS installation commands are reviewed against package metadata and official Python/conda/Miniforge/Microsoft/upstream sources linked in the relevant chapter. Runtime checks use the available Linux scientific environment. They do not prove fresh installations or successful retrievals on macOS/native Windows/WSL2.

No scene transfer, provider authentication, asset setup, real atmospheric inversion, skill installation or environment mutation is required for these checks. Source coverage and synthetic output behavior are separate from independent scientific validation across sensors/conditions. Follow the [science-readiness criteria](../workflows/science-ready.md) for actual data.

The final [check results](validation-results.json) record the actual completed tests, static recipe audit and size/coverage summary. A result marked complete must refer to executed checks, not an intended test plan.
