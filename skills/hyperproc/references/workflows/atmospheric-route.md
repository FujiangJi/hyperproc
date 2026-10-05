# Supported at-sensor input → retrieved surface reflectance

Confirm physical input meaning/units, required companions, geolocation/angles/elevation, wavelengths/FWHM and usable window. NEON DP1 is reflectance, PRISMA L2B surface radiance is not L1, and PACE L1B needs the dedicated TOA-reflectance conversion. EnMAP L1B detectors are unregistered; use an appropriate mapped L1C comparison route when a merged cube is needed.

1. Check selected Python/ISOFIT/assets/engine and [provision only approved missing assets](../installation/atmos-assets.md).
2. Define region on the actual atmospheric source grid. **EMIT process opens L1B with `ortho=False`; its window is sensor-grid, not default mapped L2A indices.** Use the [grid table](../sensors/grids.md).
3. Choose scientific priors/engine/retrieval controls and a bounded worker/resource budget. Read [advanced atmospheric details](advanced-corrections.md) and exact installed signature.
4. Use a unique source/window/settings work directory; check [reuse symptoms](../operations/work-directory-reuse.md).
5. Run a representative small retrieval, inspect outputs/QA/spectra and geographic placement before scaling up.

```python
from hyperproc.atmos import check, process

report = check(engines=("sRTMnet",))
if not report["ok"]:
    raise RuntimeError("Missing atmospheric prerequisites; review the check report")
products = process(
    "/data/actual_supported_at_sensor_product",
    "/work/products/scene-window-srtmnet",
    work_dir="/work/isofit/unique-scene-region-settings",
    engine="sRTMnet", stages=("ac",), workers=4,
    window={"y": (600, 800), "x": (600, 800)},
    layers=("aot550", "h2o"), quality=True, format="GTiff",
)
print(products)
```

Replace placeholders and prove the window intersects observations. Four workers is a cautious example, not an optimum. Process returns a product record, not automatically a Dataset; inspect actual keys and reopen the right file/output using an appropriate reader or staged `read_outputs`/`to_map_grid` with valid source context.

Preparation standardizes radiance to µW cm⁻² nm⁻¹ sr⁻¹ and excludes unsupported RT bands outside 350–2500 nm. Preserve returned band metadata. Do not manually apply one guessed sensor scaling formula. `dry_run` can still prepare files; cached results are not fresh retrievals. Neighbor caps/segmentation and missing elevation/angles can invalidate a tiny window; size alone does not establish viable inversion support.

The `("ac","brdf")` stage list invokes satellite normalization, not grouped airborne FlexBRDF. Choose BRDF only with applicable land parameters/geometry and explicit target choices. Airborne retrieved reflectance can feed the separate airborne route with valid restored geometry and independently checked coefficient transfer.

Evaluate multiple bands/surfaces, failed/fill pixels, retrieval layers and independent/reference evidence. Finish [science readiness](science-ready.md) and retain actual priors, parameters, work reuse, mapped grid, QA and disk checks. Do not claim physical accuracy merely from a plausible 865 nm correlation.
