# hyperproc.correct.pipeline.per_block_effects

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def per_block_effects(sample: Sample, wavelengths=(549, 659, 849, 1651, 2202), spec: dict=TOPO_CALC, min_pixels: int=500, split: int=1) -> list
```

The illumination effect fitted separately in each sampled block.

A single C per image assumes one relation between reflectance and cos i
over the whole image. This shows whether that holds: blocks that agree in
sign and size support a per-image C; blocks that disagree mean the pooled
slope is driven by *which* regions were pooled, not by illumination, and
the verdict should be read with that in mind. ``split`` divides every
sampled block into ``split x split`` sub-blocks (no extra reading), which
gives the consistency statistic more, smaller regions to compare.

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.per_block_effects --runtime`.
