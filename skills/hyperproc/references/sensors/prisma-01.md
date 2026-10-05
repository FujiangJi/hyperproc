## Detector handling

The reader reorganizes HDF-EOS detector arrays, removes zero-wavelength entries, orders wavelengths, and handles VNIR/SWIR overlap. `cube="vnir"`, `"swir"`, or `"full"` selects detector coverage. `join_priority` controls which detector contributes in the overlap; the default is SWIR. Keep this decision in any comparison near the join.

Provider scaling differs by level. L1 radiance is represented in W m⁻² sr⁻¹ µm⁻¹; L2 reflectance is dimensionless after its level-specific conversion. Do not apply a single scaling formula to all levels.
