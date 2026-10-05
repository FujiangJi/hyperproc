# hyperproc.atmos.inputs

Release baseline **0.1.2**; source `hyperproc/atmos/inputs.py`. Choose a callable below rather than loading every declaration.

Turn a hyperproc L1B dataset into the three ENVI files ISOFIT reads.

``isofit apply_oe`` wants, for one scene:

``<fid>_rdn``
    at-sensor radiance in µW cm⁻² nm⁻¹ sr⁻¹, band-interleaved-by-line float32,
    with ``wavelength`` and ``fwhm`` (nm) in the header;
``<fid>_loc``
    three float64 bands: longitude, latitude (WGS-84 degrees), elevation (m);
``<fid>_obs``
    eleven float64 bands in JPL's order: path length (m), to-sensor azimuth
    and zenith, to-sun azimuth and zenith (degrees), solar phase, slope,
    aspect, cos(i), UTC time (decimal hours), Earth-sun distance (AU).

The file id ``fid`` is not free: ``apply_oe`` slices it from the radiance
file name and parses the acquisition time out of it with a per-sensor
pattern, so :data:`SENSORS` carries that pattern for every hyperproc sensor
together with the radiance unit factor and the ``apply_oe`` sensor code.

Every hyperproc reader already exposes the ingredients as dataset layers
(``sza, saa, vza, vaa, slope, aspect, cos_i, elev, lat, lon`` and, for the
JPL products, ``path_length, utc_time, solar_phase``), so the writer here is
mostly bookkeeping: unit scaling, NaN to -9999, and streaming the cube out in
row blocks so a full granule never sits in memory.

## Imported aliases

- `main_var` → `hyperproc.io.main_var`

## Declared callables and classes

- [sensor_spec](symbols/hyperproc.atmos.inputs.sensor_spec.md)
- [acquisition_time](symbols/hyperproc.atmos.inputs.acquisition_time.md)
- [names_for](symbols/hyperproc.atmos.inputs.names_for.md)
- [hdr_path](symbols/hyperproc.atmos.inputs.hdr_path.md)
- [write_envi_header](symbols/hyperproc.atmos.inputs.write_envi_header.md)
- [_row_blocks](symbols/hyperproc.atmos.inputs._row_blocks.md) — internal
- [_write_cube](symbols/hyperproc.atmos.inputs._write_cube.md) — internal
- [_write_layers](symbols/hyperproc.atmos.inputs._write_layers.md) — internal
- [_layer](symbols/hyperproc.atmos.inputs._layer.md) — internal
- [_latlon](symbols/hyperproc.atmos.inputs._latlon.md) — internal
- [_phase](symbols/hyperproc.atmos.inputs._phase.md) — internal
- [_earth_sun_au](symbols/hyperproc.atmos.inputs._earth_sun_au.md) — internal
- [assemble_obs](symbols/hyperproc.atmos.inputs.assemble_obs.md)
- [assemble_loc](symbols/hyperproc.atmos.inputs.assemble_loc.md)
- [_apply_window](symbols/hyperproc.atmos.inputs._apply_window.md) — internal
- [_stats](symbols/hyperproc.atmos.inputs._stats.md) — internal
- [oci_rsr_bands](symbols/hyperproc.atmos.inputs.oci_rsr_bands.md)
- [match_bands](symbols/hyperproc.atmos.inputs.match_bands.md)
- [pace_rhot_scales](symbols/hyperproc.atmos.inputs.pace_rhot_scales.md)
- [prepare_inputs](symbols/hyperproc.atmos.inputs.prepare_inputs.md)
- [SensorSpec](symbols/hyperproc.atmos.inputs.SensorSpec.md)
- [Inputs](symbols/hyperproc.atmos.inputs.Inputs.md)

## Constant expressions

- [FILL](constants/hyperproc.atmos.inputs.FILL.md)
- [RT_RANGE](constants/hyperproc.atmos.inputs.RT_RANGE.md)
- [OBS_BANDS](constants/hyperproc.atmos.inputs.OBS_BANDS.md)
- [LOC_BANDS](constants/hyperproc.atmos.inputs.LOC_BANDS.md)
- [_ENVI_DTYPE](constants/hyperproc.atmos.inputs._ENVI_DTYPE.md)
- [SENSORS](constants/hyperproc.atmos.inputs.SENSORS.md)
- [_ALIASES](constants/hyperproc.atmos.inputs._ALIASES.md)
- [BAND_GRIDS](constants/hyperproc.atmos.inputs.BAND_GRIDS.md)
- [CONVERTERS](constants/hyperproc.atmos.inputs.CONVERTERS.md)
