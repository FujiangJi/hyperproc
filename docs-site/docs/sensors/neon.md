# NEON Airborne Observation Platform

The current reader supports **DP1.30006.001 reflectance flightlines**, not DP3 mosaics. NEON's `L1` label in this registry does not indicate at-sensor radiance.

```python
import hyperproc as hp
ds = hp.open("/path/to/NEON_DP1_reflectance.h5", sensor="NEON", level="L1")
hp.describe(ds)
```

The filename is a placeholder; provide a genuine DP1 HDF5 product with its provider hierarchy.

## Decoding and geometry

The reader applies the product scale factor to reflectance, converts fill values, and reads wavelengths/band widths and usable-band information. Mapped UTM geometry is retained. Solar angles can be scene scalars while view/terrain information is spatially resolved. Several metadata layers have their own scaling conventions; they must not be treated as raw physical values indiscriminately.

`fix_geometry="auto"` uses the shared geometry checks. `classes=True` retains available classification/quality layers; `extras=True` retains ancillary information. The cast-shadow raw field is preserved rather than assigned an unsupported physical interpretation.

## Workflow

Use QA and the airborne grouped correction route where justified. The current DP1 reflectance product does not need to be passed through ISOFIT as if it were radiance. A NEON sensor specification in atmospheric configuration is not evidence of a usable radiance input here.

**Planned — not implemented:** DP3 mosaic reader. Do not follow a general NEON DP3 tutorial and assume its input is supported by this code.

[Reader API](../api/hyperproc-readers-neon.md) · [NEON tutorial](../tutorials/neon-tutorial.md)
