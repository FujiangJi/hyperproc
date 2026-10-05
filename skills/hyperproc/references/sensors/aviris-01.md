## Open

```python
import hyperproc as hp
ds = hp.open("/path/to/AV320231005t181518_L2A_OE_product_RFL_ORT")
hp.describe(ds)
print(ds.attrs.get("geometry_check"), ds.attrs.get("geometry_fixed"))
```

The path is a naming illustration: use the actual provider product. Explicit registry aliases include `AVIRIS`, `AVIRIS-CLASSIC`, `AVIRIS-NG`, `AVIRIS3`, and `AVIRIS5`; reported sensor attributes can use display names such as `AVIRIS-3`.
