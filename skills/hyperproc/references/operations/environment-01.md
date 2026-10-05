## Authority and version handling

Baseline: published PyPI hyperproc **0.1.2**, not an unreleased GitHub branch. The release manifest records wheel URL, SHA256, dependencies, and all module hashes. All reviewed checkout modules were identical to that wheel. The skill is a dated release snapshot, not a claim that future packages/sites cannot change.

Run the helper with the target interpreter:

```bash
python /path/to/hyperproc/scripts/env_report.py --capability core
python /path/to/hyperproc/scripts/env_report.py --capability atmos --output /path/to/environment.json
```

Replace the skill path and output path. The helper checks installed distribution metadata and import discovery without importing heavy libraries or authenticating. A dependency being installed does not prove ABI compatibility, engine readiness, account access, or scientific correctness. A mismatched package version is reported, not silently upgraded or rejected as unusable. Verify changed APIs in the installed environment using signatures/source.

The release declares Python >=3.11. Python 3.12 is the documented practical environment. For the reviewed ISOFIT 4.1.5, Python >=3.11,<3.13 applies; verify the actual installed ISOFIT metadata rather than generalizing this to every future ISOFIT 4.x. Do not assert a Python 3.12-only package restriction.
