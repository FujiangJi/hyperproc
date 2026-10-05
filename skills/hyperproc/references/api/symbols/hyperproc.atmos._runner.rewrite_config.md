# hyperproc.atmos._runner.rewrite_config

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def rewrite_config(cfg_path: str | Path, engine: str | None, settings: dict, overrides: dict | None=None) -> None
```

Adjust one ISOFIT config: swap the engine block and apply ``--set`` overrides.

[Module and aliases](../hyperproc-atmos-_runner.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos._runner.rewrite_config --runtime`.
