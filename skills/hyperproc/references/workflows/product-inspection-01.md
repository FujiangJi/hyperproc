## Metadata-first sequence

1. Identify product primary file and its delivery directory; retain XML/HDR/OBS/MASK/geolocation siblings.
2. Use `hp.sniff(path)` for filename-only identification. When detection is ambiguous, explicit `sensor=` and `level=` are appropriate only if metadata confirms them.
3. Read the actual reader signature in the atlas and its sensor guide. `hp.open` forwards kwargs; accepted arguments differ across readers. Do not pass a universal `chunks=`/`geometry=`/`good_bands_only=` argument set blindly.
4. Open and inspect `hp.main_var(ds)`, cube dimensions/dtype, attributes, wavelength order/range, good bands, FWHM, mapped/sensor grid, and geometry sources.
5. Estimate one full cube's bytes as the product of dimensions times dtype itemsize. Budget additional intermediate arrays/masks/geometry and reader I/O.
6. Select a representative observed region for numerical diagnostics. A center window can be empty in rotated scenes. Check fill fraction and choose another justified window if needed.
7. Record physical quantity from provider metadata and units. Do not decide from `reflectance` versus `radiance` variable naming alone.

Use the bundled helper for deterministic reporting:

```bash
python /path/to/hyperproc/scripts/inspect_product.py /data/provider_product --sensor EMIT --level L2A
python /path/to/hyperproc/scripts/inspect_product.py /data/provider_product --sample --window 3000 3256 400 656 --output /work/inspection.json
```

By default only metadata and small wavelength coordinate arrays are inspected. `--sample` reads only the selected spectral cube window for numeric statistics, but the reader may already perform geometry/ancillary I/O during open. Default sampled spatial window is up to 128×128 at the center. Explicit windows use half-open `[y_start:y_stop, x_start:x_stop]` pixel indices and are validated against dimensions. Do not interpret one sampled window as a scene-wide quality assessment. Reader options are explicit JSON and are forwarded only when the reader accepts them; the helper rejects credential-like options.
