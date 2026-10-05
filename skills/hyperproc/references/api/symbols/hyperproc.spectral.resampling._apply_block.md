# hyperproc.spectral.resampling._apply_block

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _apply_block(a: np.ndarray, M: np.ndarray, min_coverage: float=0.5) -> np.ndarray
```

Apply the resampling matrix, keeping a dead source band local.

A dense product spreads a single NaN across the whole output, because
``0.0 * nan`` is ``nan``: one dead band at the end of the shortwave takes
the visible with it. On the PRISMA test granule four unflagged bands near
2490 nm carry NaN in some pixels, and that silently emptied the resampled
spectrum of 31 % of them.

So the gaps are zeroed and each target band is divided by the weight that
actually landed on finite source bands. That is the renormalisation the
static coverage test already performs, applied per pixel, and it is held
to the same threshold: a target band that kept less than ``min_coverage``
of its weight comes back NaN rather than as a confident-looking number
built from a fraction of its response.

[Module and aliases](../hyperproc-spectral-resampling.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral.resampling._apply_block --runtime`.
