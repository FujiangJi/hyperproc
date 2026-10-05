# hyperproc.atmos.inputs.SensorSpec

Release baseline **0.1.2**. Fields and declared members below come from the release source. Dataclass/inherited methods may be generated at runtime; inspect the installed class signature when constructing it.

How one hyperproc sensor maps onto ``apply_oe``.

Attributes:
    code: the ``sensor`` argument of ``apply_oe``. ``"NA"`` means the
        generic route, where the code becomes ``NA-YYYYMMDD``.
    unit_factor: multiply hyperproc radiance by this to get
        µW cm⁻² nm⁻¹ sr⁻¹. None means the conversion needs more than a
        factor and is not implemented yet.
    fid: ``strftime`` pattern that builds the file id ISOFIT will slice
        and parse back. ``{dt}`` in ``rdn`` marks where it goes.
    rdn: pattern of the radiance file name, so ISOFIT's slicing of the
        name yields exactly ``fid``.
    altitude_km: nominal platform altitude, used only when the product
        carries no path-length layer.
    tested: whether this route has been run through ISOFIT on a real
        granule and the reflectance compared against the provider's own
        product. A False entry only warns; it changes nothing else.

## Declared fields

```text
code: str
unit_factor: float | None
fid: str
rdn: str = '{fid}_rdn'
altitude_km: float | None = None
tested: bool = False
converter: str | None = None
id_pattern: str | None = None
inversion_windows: tuple | None = None
band_grid: str | None = None
```

## Declared members


[Module](../hyperproc-atmos-inputs.md).
