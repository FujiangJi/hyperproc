# Quality flags and masking

The QA layer translates available provider masks and selected derived conditions into a `uint16` bit field. A pixel can carry several flags simultaneously. Original provider layers remain useful for interpreting how a flag was obtained.

```python
q = hp.quality_flags(ds, derive=("fill", "terrain_shadow", "steep_terrain"))
print(hp.quality_table(q))
masked = hp.quality_apply(ds, q, drop=("fill", "cloud", "cloud_shadow", "cirrus"))
shadow = hp.quality_decode(q, "terrain_shadow", "cloud_shadow")
```

## Bit definitions

| Bit | Flag | Meaning |
|---:|---|---|
| 0 | `fill` | No observation / nodata |
| 1 | `saturated` | Saturation condition available from the product |
| 2 | `cloud` | Opaque cloud |
| 3 | `cloud_shadow` | Cloud-shadow flag |
| 4 | `cirrus` | Cirrus flag |
| 5 | `snow_ice` | Snow or ice |
| 6 | `water` | Water flag |
| 7 | `haze` | Haze/aerosol-related provider flag |
| 8 | `sun_glint` | Glint condition |
| 9 | `terrain_shadow` | Nonpositive local solar-incidence cosine |
| 10 | `steep_terrain` | Slope exceeds the selected threshold |
| 11 | `ac_failed` | Atmospheric retrieval failure indication |
| 12 | `brdf_filled` | BRDF handling used missing/substituted support |
| 13 | `negative_reflectance` | Selected fraction of usable bands below zero |

## Build is not mask

`quality_flags()` reports conditions. `quality_apply()` masks the selected main variable where specified flags occur. Building `steep_terrain` does not exclude those pixels unless that flag is in `drop`. Choose a policy appropriate to the analysis rather than assuming all bits are equally disqualifying.

Default derived flags are `fill` and `terrain_shadow`. Optional spectral cloud screening is not automatically run in every reader or workflow. A zero-valued cloud bit can mean that no cloud information was available; it is **not** a cloud-free certification.

## Export categorical values correctly

Use nearest-neighbor or another categorical-safe method for flags, never ordinary averaging. Include the bit definitions in output metadata. Review whether geometry-derived flags remain valid after resampling and whether source flags were present in the first place.

See [quality API](../api/hyperproc-quality.md) and [export](export.md).
