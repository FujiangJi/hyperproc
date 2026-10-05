## Failure reporting and retries

Retain the failing callable, sanitized exception, installed versions, exact region/parameters, and last successful stage. Diagnose one cause before retrying. Do not silently change sensor, physical units, masks, priors or correction gates to make execution succeed. If partial downloads/work products are resumable, identify retained state and stopping condition. Explain blocked stages separately from successfully completed inspection or code preparation.

The bundle's `validate_bundle.py` verifies AST coverage, source hashes when the release wheel is supplied, metadata, local reference links and syntax of bundled scripts. Its `--runtime` option tests helpers and a tiny known-answer QA/index/export workflow against the active environment. Passing these checks establishes bundle integrity and selected synthetic behavior, not every released API or sensor engine independently validated.
