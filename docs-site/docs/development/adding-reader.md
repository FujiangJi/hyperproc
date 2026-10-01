# Adding a sensor reader

This is a development checklist, not a claim that an absent reader already exists.

## 1. Establish the measurement contract

Collect authoritative product documentation and a legally accessible fixture. Record the physical quantity, units, scaling, nodata, detector layout, wavelengths, response widths, bad-band policy, grid, acquisition metadata, and geometry/QA provenance.

## 2. Decode without losing distinctions

Build a provider-specific module under `readers/` and use the shared helpers only where their assumptions match the product. Return the common `(y, x, wavelength)` organization where appropriate. Do not invent absent geometry, interpret an unknown mask optimistically, or merge incompatible detector grids.

## 3. Register narrow patterns

Add a loader and `Entry` definitions in `registry.py`. Distinguish levels explicitly, avoid broad filename patterns that capture unrelated products, and provide meaningful errors for unsupported cases. Confirm that any directory discovery is consistent with `hp.open()`'s dispatch rules.

## 4. Test physical correctness

Use known-value fixtures for scaling and fill handling; independently compare wavelength ordering, band indices, transforms, and ancillary fields. Test subsets and rotated grids, not only a successful full-image read. A same-shaped cube is not evidence of correct units or geolocation.

## 5. Treat downstream routes separately

Reader support does not automatically authorize an ISOFIT sensor specification, BRDF model, geometry repair, or quality decoder. Add and validate those interfaces independently. Record which optional fields each downstream function requires.

## 6. Document and retain evidence

Add the sensor guide, a bounded tutorial, reproducible regression tests, and limitations. Run the documentation generator and check API/link coverage. Do not claim “supported” for an unimplemented registry entry or a notebook that contains no saved execution evidence.

See [shared reader helpers](../api/hyperproc-readers-_common.md) and [registry API](../api/hyperproc-registry.md).
