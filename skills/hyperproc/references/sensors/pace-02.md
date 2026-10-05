## Geometry and mapping

PACE data are read as a latitude/longitude swath. L1B geometry can supplement L2; scanline summaries or incomplete geometry are not equivalent to a complete angle field. Keep corresponding products available where the workflow needs them.

`hp.georeference()` has PACE-specific defaults, including a geographic target grid. Choose resolution and footprint handling deliberately; a wide swath and coarse spatial support require different assumptions from a metre-scale airborne line.
