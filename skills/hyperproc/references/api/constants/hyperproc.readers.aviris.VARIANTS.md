# hyperproc.readers.aviris.VARIANTS

Release **0.1.2** source expression; not an evaluated runtime value. For a later release inspect the installed source.

```text
(_Variant('AVIRIS-3', re.compile('(AV3\\d{8}t\\d{6})'), rdn=('*_RDN_ORT',), rfl=('*_RFL_ORT',), obs=('*_OBS_ORT',), unc=('*_UNC_ORT',), atm=('*_ATM_ORT',)), _Variant('AVIRIS-5', re.compile('(AV5\\d{8}t\\d{6}_\\d{3})'), rdn=('*_L1B_RDN_*_RDN.nc',), rfl=('*_RFL_ORT.nc',), obs=('*_L1B_ORT_*_OBS.nc',), unc=('*_UNC_ORT.nc',)), _Variant('AVIRIS-NG', re.compile('(ang\\d{8}t\\d{6})'), rdn=('*_rdn_*_img',), rfl=('*_rfl_*_img',), obs=('*_obs_ort',)), _Variant('AVIRIS-Classic', re.compile('(f\\d{6}t\\d{2}p\\d{2}r\\d{2})'), rdn=('*_sc01_ort_img', '*rdn*_ort_img'), rfl=('*_corr_*_img', '*_refl_*_img'), obs=('*_obs_ort',), atm=('*_h2o_*_img',)))
```

[Module](../hyperproc-readers-aviris.md).
