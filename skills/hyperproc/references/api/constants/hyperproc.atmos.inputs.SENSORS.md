# hyperproc.atmos.inputs.SENSORS

Release **0.1.2** source expression; not an evaluated runtime value. For a later release inspect the installed source.

```text
{'EMIT': SensorSpec('emit', 1.0, 'emit%Y%m%dt%H%M%S', altitude_km=420.0, tested=True), 'AVIRIS-3': SensorSpec('av3', 1.0, 'AV3%Y%m%dt%H%M%S', id_pattern='^AV3\\d{8}t\\d{6}', tested=True), 'AVIRIS-5': SensorSpec('av5', 1.0, 'AV5%Y%m%dt%H%M%S', id_pattern='^AV5\\d{8}t\\d{6}', tested=True), 'AVIRIS-NG': SensorSpec('ang', 1.0, 'ang%Y%m%dt%H%M%S', id_pattern='^ang\\d{8}t\\d{6}', tested=True), 'AVIRIS-CLASSIC': SensorSpec('avcl', 1.0, 'f%y%m%dt01p00r01', id_pattern='^f\\d{6}t\\d{2}p\\d{2}r\\d{2}', tested=True), 'NEON': SensorSpec('neon', 1.0, 'NIS01_%Y%m%d_%H%M%S'), 'ENMAP': SensorSpec('enmap', 100.0, '%Y%m%dt%H%M%S', rdn='ENMAP_L1B_hyperproc_0_0_{fid}_rdn', altitude_km=653.0, tested=True), 'PRISMA': SensorSpec('prisma', 0.1, '%Y%m%d%H%M%S', rdn='PRS_{fid}_rdn', altitude_km=615.0, tested=True, inversion_windows=((400.0, 1340.0), (1450.0, 1800.0), (1970.0, 2470.0))), 'TANAGER': SensorSpec('tanager', 0.1, '%Y%m%d_%H%M%S_tanager', altitude_km=500.0, tested=True), 'PACE': SensorSpec('oci', 1.0, 'PACE_OCI.%Y%m%dT%H%M%S', altitude_km=676.5, converter='pace_rhot', band_grid='oci_rsr', tested=True), 'DESIS': SensorSpec('NA', 1.0, 'desis%Y%m%dt%H%M%S', rdn='{fid}', altitude_km=400.0, tested=True)}
```

[Module](../hyperproc-atmos-inputs.md).
