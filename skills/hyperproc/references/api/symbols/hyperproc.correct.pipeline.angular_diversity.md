# hyperproc.correct.pipeline.angular_diversity

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def angular_diversity(sza, vza, raa, mask=None, volume='ross_thick', geometric='li_dense_r', b_r=1.0, h_b=2.0, span_min_deg=8.0, cond_max=2000.0) -> dict
```

Can a kernel fit tell f_vol and f_geo apart on this geometry?

Reports the p05-p95 span of view zenith, the circular spread of relative
azimuth, and the condition number of the ``[k_vol, k_geo, 1]`` design
matrix. Verdict ``ok`` needs a view-zenith span of at least
``span_min_deg`` and a condition number below ``cond_max``; narrow-swath
narrow-swath scenes (2-3 degrees of view zenith) fail this, airborne swaths
(15-20 degrees) pass.

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.angular_diversity --runtime`.
