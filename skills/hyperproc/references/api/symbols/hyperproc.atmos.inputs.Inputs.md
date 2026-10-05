# hyperproc.atmos.inputs.Inputs

Release baseline **0.1.2**. Fields and declared members below come from the release source. Dataclass/inherited methods may be generated at runtime; inspect the installed class signature when constructing it.

What :func:`prepare_inputs` wrote, and what the ISOFIT run needs to know.

## Declared fields

```text
work_dir: str
sensor: str
code: str
fid: str
rdn: str
loc: str
obs: str
wavelengths: str
shape: tuple
unit_factor: float
datetime: str
stem: str
granule: str
window: dict | None = None
bands: list | None = None
stats: dict = field(default_factory=dict)
```

## Declared members

- [subset](hyperproc.atmos.inputs.Inputs.subset.md)
- [output](hyperproc.atmos.inputs.Inputs.output.md)
- [json](hyperproc.atmos.inputs.Inputs.json.md)
- [save](hyperproc.atmos.inputs.Inputs.save.md)
- [load](hyperproc.atmos.inputs.Inputs.load.md)
- [describe](hyperproc.atmos.inputs.Inputs.describe.md)

[Module](../hyperproc-atmos-inputs.md).
