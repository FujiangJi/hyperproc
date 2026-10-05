# hyperproc.atmos.correct.build_command

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def build_command(inputs: Inputs, engine: str='sRTMnet', workers: int=24, atmosphere: str='auto', aerosol_model: str='continental', segmentation_size: int=40, line: str='analytical', presolve: bool=True, surface=None, num_neighbors=None, terrain_style: str='flat', pressure_elevation: bool=False, emulator: str | Path | None=None, ozone: float | None=None, band_model: str='coarse', inversion_windows=None, aot_prior_sigma: float | None=None, config_overrides: dict | None=None, ray_temp_dir: str | None=None, log_level: str='INFO', extra=()) -> list[str]
```

The ``isofit apply_oe`` command line for ``inputs``.

Args:
    engine: ``"sRTMnet"`` (JPL's operational emulator), ``"6s"`` or
        ``"LibRadTran"``. The last two run the same ``apply_oe`` pipeline
        with the table engine swapped by :mod:`hyperproc.atmos._runner`.
    workers: Ray CPUs for the look-up table and the inversions.
    atmosphere: ``"auto"`` (:func:`atmosphere_for`) or one of :data:`ATMOSPHERES`.
        6S ignores it (its template uses user-defined H2O/O3 on a standard
        profile); libRadtran maps it to the matching AFGL profile.
    aerosol_model: ``"continental"`` only on sRTMnet; see
        :data:`hyperproc.atmos.aerosols.AEROSOLS` for 6S and libRadtran.
    ozone: ozone column in atm-cm for 6S and libRadtran (default ISOFIT's 0.30).
    band_model: libRadtran REPTRAN resolution, ``"coarse"`` (default), ``"medium"`` or ``"fine"``.
    inversion_windows: fit windows in nm as ``((lo, hi), ...)``; default the
        sensor's entry in :data:`hyperproc.atmos.inputs.SENSORS`, else
        ISOFIT's own per-sensor defaults.
    aot_prior_sigma: width of the aerosol prior. ISOFIT 4.1.5 uses 0.1
        around a prior mean of 0.138, which pulls the retrieval toward
        that value and is why our AOT sits below the providers'; JPL's
        version-1 EMIT products used a loose prior instead. A number here
        replaces it (1.0 is effectively unconstrained).
    config_overrides: any other ISOFIT config values, keyed by
        slash-separated path, e.g.
        ``{"forward_model/atmosphere/statevector/H2OSTR/prior_sigma": 100}``.
    segmentation_size: SLIC superpixel size in pixels (JPL: 40).
    line: ``"analytical"`` (JPL), ``"empirical"``, or ``"pixel"`` for a
        full optimal-estimation inversion of every pixel (slow).
    presolve: retrieve water vapour first and centre its grid on the scene.
    surface: recipe ``.json`` or built ``.mat``; default :data:`DEFAULT_SURFACE`.
    num_neighbors: how many superpixels the analytical line fits each
        atmospheric term over: a dict keyed by term, one number for all,
        or a sequence in the order of :func:`atm_terms`. The default is
        :data:`ATM_NEIGHBORS`, which keeps the structure of the retrieved
        fields; every value is capped by the scene's superpixel count.
    terrain_style: ``"flat"`` (default, JPL's EMIT setting) lights every
        pixel with cos(sun zenith); ``"dem"`` uses the per-pixel cos(i)
        from the obs file inside the forward model, which normalises the
        direct irradiance for slope and aspect during the retrieval.
        hyperproc corrects topography in its own stage (SCS+C), so
        ``"flat"`` keeps the two from being applied twice.
    pressure_elevation: add surface elevation to the state vector
        (JPL's V1 EMIT processing did; V2 does not).
    emulator: a specific sRTMnet weights file (``sRTMnet_v100.h5`` to
        emulate JPL's V1 products); default the newest under the asset base.
    extra: further raw ``apply_oe`` options appended verbatim.

[Module and aliases](../hyperproc-atmos-correct.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.correct.build_command --runtime`.
