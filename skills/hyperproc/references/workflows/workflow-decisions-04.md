## Example request interpretations

“Compute NDVI for this EMIT L2A” means a bounded reflectance/QA/index/export workflow. Do not automatically retrieve atmosphere or normalize BRDF.

“Correct these NEON L1 flightlines” is ambiguous scientifically: NEON DP1 is already reflectance. Inspect residual terrain/angular effects and choose the airborne branch only if warranted.

“Use EnMAP L1B” requires detector selection and grid/geometry handling; it is not a merged orthorectified cube simply because L1C can be one.

“Download all nearby scenes” requires clarifying or deriving a meaningful scope; `count=-1` means unrestricted result enumeration. Start with bounded anonymous search if that advances the task, then select and budget the explicitly authorized transfer.

“Make the notebook map interactive on the static site” cannot execute Python archive queries without a kernel/service. Saved Leaflet footprints can pan/zoom, while ipyleaflet Python controls are a separate environment capability.
