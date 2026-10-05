# hyperproc.correct.coefficients.TopoCoefficients

Release baseline **0.1.2**. Fields and declared members below come from the release source. Dataclass/inherited methods may be generated at runtime; inspect the installed class signature when constructing it.

Per-image topographic correction coefficients with their fit diagnostics.

## Declared fields

```text
method: str
fit_method: str
wavelength: np.ndarray
c: np.ndarray
status: list
slope: np.ndarray
intercept: np.ndarray
r: np.ndarray
effect: np.ndarray
t: np.ndarray
n_samples: int
calc_mask: dict = field(default_factory=dict)
apply_mask: dict = field(default_factory=dict)
diagnostic: dict = field(default_factory=dict)
source: dict = field(default_factory=dict)
meta: dict = field(default_factory=dict)
```

## Declared members

- [n_ok](hyperproc.correct.coefficients.TopoCoefficients.n_ok.md)
- [verdict](hyperproc.correct.coefficients.TopoCoefficients.verdict.md)
- [c_for](hyperproc.correct.coefficients.TopoCoefficients.c_for.md)
- [summary](hyperproc.correct.coefficients.TopoCoefficients.summary.md)
- [to_dict](hyperproc.correct.coefficients.TopoCoefficients.to_dict.md)
- [to_json](hyperproc.correct.coefficients.TopoCoefficients.to_json.md)
- [from_dict](hyperproc.correct.coefficients.TopoCoefficients.from_dict.md)
- [from_json](hyperproc.correct.coefficients.TopoCoefficients.from_json.md)

[Module](../hyperproc-correct-coefficients.md).
