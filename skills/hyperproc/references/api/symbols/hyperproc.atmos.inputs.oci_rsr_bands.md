# hyperproc.atmos.inputs.oci_rsr_bands

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def oci_rsr_bands() -> np.ndarray
```

Band centres (nm) of the OCI response functions ISOFIT resamples with.

For the ``oci`` sensor ISOFIT replaces its Gaussian resampling with the
measured response functions in ``data/oci/pace_oci_rsr.nc``, whose 270
bands are its own idea of the instrument. Handing it a different band
count makes the look-up table and the instrument model disagree
("conflicting sizes for dimension 'wl'"), so the inputs are written on
this grid.

[Module and aliases](../hyperproc-atmos-inputs.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.inputs.oci_rsr_bands --runtime`.
