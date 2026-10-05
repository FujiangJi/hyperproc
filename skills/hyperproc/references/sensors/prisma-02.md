## Geometry and quality

For L1, geometry/geolocation can be borrowed from suitable L2 siblings, with other fallback paths documented in the reader. That dependency should be recorded. Elevation may need to be supplied separately. Optional error matrices and retrieval maps are not interchangeable with a provider good-band list.

`good_bands_only=True` is not a general PRISMA quality switch; the reader rejects that request when no provider good-band flag exists. L2D padding also requires attention.
