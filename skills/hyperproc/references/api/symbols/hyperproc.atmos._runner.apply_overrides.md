# hyperproc.atmos._runner.apply_overrides

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def apply_overrides(cfg: dict, overrides: dict)
```

Set values in a config by slash-separated path.

Returns ``(changed, missing)``. A path that this config does not have is
reported rather than raised: ``apply_oe`` writes two configs and the
water-vapour presolve has no aerosol term, so an aerosol override applies
to one of them only. The caller checks that every override reached at
least one config.

[Module and aliases](../hyperproc-atmos-_runner.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos._runner.apply_overrides --runtime`.
