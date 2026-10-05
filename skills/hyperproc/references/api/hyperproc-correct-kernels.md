# hyperproc.correct.kernels

Release baseline **0.1.2**; source `hyperproc/correct/kernels.py`. Choose a callable below rather than loading every declaration.

BRDF kernels: Ross (volume scattering) and Li (geometric-optical) families.

Written from the equations, not ported from another implementation:

* Ross-thick / Ross-thin - Roujean et al. (1992) after Ross (1981), in the
  form used by the MODIS BRDF/albedo algorithm (Wanner, Li & Strahler 1995;
  Lucht, Schaaf & Strahler 2000, eqs 38-39).
* Li-sparse / Li-dense and their reciprocal variants - Wanner et al. (1995)
  eqs 32-34, with the reciprocal forms of Lucht et al. (2000) eq 40-41. The
  "R" kernels are symmetric in the two zenith angles and are what MODIS and
  FlexBRDF (Queally et al. 2022) use.

Conventions, chosen to match the rest of ``hyperproc``:

* All angles in **radians**. Zenith angles are measured from the vertical.
* ``raa`` is the relative azimuth ``vaa - saa``. Every kernel depends on it
  only through ``cos(raa)`` and ``sin^2(raa)``, so its sign and any multiple
  of 2 pi are irrelevant - ``hyperproc`` readers' ``raa`` (mod 360, in
  degrees) can be passed straight through ``np.radians``.
* ``b_r`` and ``h_b`` are the Li-kernel crown shape ratios: ``b/r`` (vertical
  to horizontal crown radius) and ``h/b`` (crown centre height to vertical
  radius). MODIS uses ``b_r = 1, h_b = 2`` (spherical crowns). Published NEON
  processing used ``b_r = 2.5``; that is a modelling choice, not a
  default this module makes for you.

Every kernel is exactly zero for an overhead sun and nadir view, which is the
first thing the tests check.

## Declared callables and classes

- [phase_angle](symbols/hyperproc.correct.kernels.phase_angle.md)
- [ross_thick](symbols/hyperproc.correct.kernels.ross_thick.md)
- [ross_thin](symbols/hyperproc.correct.kernels.ross_thin.md)
- [volume_kernel](symbols/hyperproc.correct.kernels.volume_kernel.md)
- [_li_terms](symbols/hyperproc.correct.kernels._li_terms.md) — internal
- [li_sparse](symbols/hyperproc.correct.kernels.li_sparse.md)
- [li_sparse_r](symbols/hyperproc.correct.kernels.li_sparse_r.md)
- [li_dense](symbols/hyperproc.correct.kernels.li_dense.md)
- [li_dense_r](symbols/hyperproc.correct.kernels.li_dense_r.md)
- [geometric_kernel](symbols/hyperproc.correct.kernels.geometric_kernel.md)
- [kernel_pair](symbols/hyperproc.correct.kernels.kernel_pair.md)
- [reference_kernels](symbols/hyperproc.correct.kernels.reference_kernels.md)

## Constant expressions

- [VOLUME_KERNELS](constants/hyperproc.correct.kernels.VOLUME_KERNELS.md)
- [GEOMETRIC_KERNELS](constants/hyperproc.correct.kernels.GEOMETRIC_KERNELS.md)
