## Recommended processing record

Use a JSON manifest with actual values (no invented defaults). Choose appropriate optional fields for the workflow:

```json
{
  "skill_baseline": "hyperproc-0.1.2",
  "run_id": "user-chosen-scene-and-region",
  "environment": {"python": "actual", "hyperproc": "actual", "dependencies": {}},
  "inputs": [{"path": "actual path", "granule": "actual identity", "sensor": "actual", "level": "actual", "quantity": "surface_reflectance", "units": "actual", "fingerprint": "hash or disclosed size/mtime only"}],
  "region": {"selection": "pixel_window", "y": [0, 128], "x": [0, 128], "grid_source": "actual source grid"},
  "spectral_support": {"wavelength_units": "nm", "bands_used": [], "excluded_bands": [], "response_source": null},
  "quality": {"drop": ["fill", "cloud", "cloud_shadow", "cirrus"], "available_sources": [], "unknown_conditions": []},
  "stages": [{"name": "actual stage", "call": "verified qualified callable", "parameters": {}, "diagnostic_verdict": null, "reuse": false}],
  "geometry": {"crs": "actual or null", "transform": "actual full affine", "sources": {}, "angle_units": "degrees"},
  "outputs": [{"path": "actual", "quantity": "actual", "checks": {}}],
  "limitations": [],
  "status": "actual completion status"
}
```

Do not claim a source checksum when only file size/mtime was observed. Full multigigabyte hashing can be substantial I/O; use available provider hashes or a transparently labeled metadata fingerprint when appropriate. Exclude secrets and unnecessary provider raw metadata. Keep coefficient JSON and the paired band table alongside relevant products.
