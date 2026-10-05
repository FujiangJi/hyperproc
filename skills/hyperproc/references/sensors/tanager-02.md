## Ancillary information

Available masks, geometry, retrieval layers, and optional uncertainty can be attached. Check the actual variables: the SR uncertainty layer can be named `reflectance_uncertainty`, while downstream functions may only recognize an `uncertainty` variable. Do not assume end-to-end propagation without inspecting the selected path.

Provider good-band information is level-dependent. The reader can mask flagged spectral values when requested; inspect dimensions and `good_wavelength` rather than assuming bad bands were physically removed.
