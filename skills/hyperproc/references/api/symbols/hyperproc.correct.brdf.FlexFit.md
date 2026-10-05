# hyperproc.correct.brdf.FlexFit

Release baseline **0.1.2**. Fields and declared members below come from the release source. Dataclass/inherited methods may be generated at runtime; inspect the installed class signature when constructing it.

Fitted FlexBRDF coefficients for one group of images.

## Declared fields

```text
bins: list
coeffs: np.ndarray
volume: str
geometric: str
b_r: float
h_b: float
sza_ref: float
n_per_bin: np.ndarray
r2: np.ndarray
wavelength: np.ndarray | None = None
meta: dict = field(default_factory=dict)
```

## Declared members

- [to_dict](hyperproc.correct.brdf.FlexFit.to_dict.md)
- [from_dict](hyperproc.correct.brdf.FlexFit.from_dict.md)

[Module](../hyperproc-correct-brdf.md).
