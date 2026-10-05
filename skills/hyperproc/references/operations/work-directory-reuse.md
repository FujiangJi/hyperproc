# Recognize and prevent accidental ISOFIT reuse

A completed ISOFIT work directory can deliberately reuse prepared/retrieved state. Speed alone does not mean an error, and a cache hit is not a fresh retrieval benchmark.

**Symptoms to investigate:** different windows produce identical medians or spectra; the log reports existing inputs/completed outputs; elapsed retrieval information repeats; a supposedly new atmospheric retrieval returns suspiciously quickly; raster dimensions/placement disagree with the intended region. A reused result may be painted onto different ground if current template/geolocation is combined with older work products. These symptoms suggest a hypothesis, not proof every identical median is a reuse bug.

Before reuse, compare exact source acquisition/primary and companion files, grid, pixel window, wavelengths, engine, surface/aerosol assumptions, segmentation/neighbors, priors/overrides, and relevant package/dependency versions. Work directory naming must distinguish meaningful changes. Sharing a stem or array shape is insufficient.

The helper produces a suggested identity without writing or running retrieval:

```bash
python /path/to/hyperproc/scripts/run_context.py \
  --input /data/actual_product \
  --region '{"y":[600,800],"x":[600,800],"grid":"EMIT sensor"}' \
  --settings '{"engine":"sRTMnet","stages":["ac"],"workers":4}' \
  --work-root /work/isofit
```

These are POSIX shell quotes; use correctly escaped JSON or an adapted invocation on Windows. Add actual companion/reference/prior/coefficient files with further `--input` entries, and include scientifically effective settings/defaults. The helper hashes the run context, not file content; path/size/mtime are disclosed metadata fingerprints. Its directory suggestion is an aid, not a guarantee existing retrieval provenance matches.

If mismatch is confirmed, preserve useful diagnostics and use a fresh directory or explicitly chosen rerun stage. `redo="line"` reuses upstream state and is not a full fresh inversion; `redo="all"`/overwrite can replace work products. `dry_run` can write prepared inputs. Prefer a separate experiment directory over deleting another run's files.

Report reused versus fresh phases separately. A fast export of old retrieval does not establish atmospheric runtime or scientific accuracy for the new scene/window.
