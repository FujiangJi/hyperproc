## Decoding and geometry

The reader applies the product scale factor to reflectance, converts fill values, and reads wavelengths/band widths and usable-band information. Mapped UTM geometry is retained. Solar angles can be scene scalars while view/terrain information is spatially resolved. Several metadata layers have their own scaling conventions; they must not be treated as raw physical values indiscriminately.

`fix_geometry="auto"` uses the shared geometry checks. `classes=True` retains available classification/quality layers; `extras=True` retains ancillary information. The cast-shadow raw field is preserved rather than assigned an unsupported physical interpretation.
