# hyperproc.correct.pipeline.Sample

Release baseline **0.1.2**. Fields and declared members below come from the release source. Dataclass/inherited methods may be generated at runtime; inspect the installed class signature when constructing it.

What a fit needs from one image, at a spread of sampled pixels.

## Declared fields

```text
stem: str
sensor: str
level: str
path: str
wavelength: np.ndarray
good: np.ndarray
rho: np.ndarray
sza: np.ndarray
saa: np.ndarray
vza: np.ndarray
vaa: np.ndarray
slope: np.ndarray
aspect: np.ndarray
cos_i: np.ndarray
raa: np.ndarray
ndvi: np.ndarray
rows: np.ndarray
cols: np.ndarray
edge_ok: np.ndarray
edge_px: int
index: dict
blocks: list
all_ndvi: np.ndarray
cloud_stats: dict
fraction: float
seed: int
n_valid_total: int
elapsed: float = 0.0
strategy: str = 'chunks'
topo_sums: dict | None = None
cos_i_calc: np.ndarray | None = None
n_calc_topo: int = 0
_cloud_cache: dict = field(default_factory=dict, repr=False)
_cloud_precomputed: dict = field(default_factory=dict, repr=False)
```

## Declared members

- [n](hyperproc.correct.pipeline.Sample.n.md)
- [cloud_flags](hyperproc.correct.pipeline.Sample.cloud_flags.md)
- [topo_calc_mask](hyperproc.correct.pipeline.Sample.topo_calc_mask.md)
- [topo_apply_mask](hyperproc.correct.pipeline.Sample.topo_apply_mask.md)
- [brdf_calc_mask](hyperproc.correct.pipeline.Sample.brdf_calc_mask.md)
- [summary](hyperproc.correct.pipeline.Sample.summary.md)

[Module](../hyperproc-correct-pipeline.md).
