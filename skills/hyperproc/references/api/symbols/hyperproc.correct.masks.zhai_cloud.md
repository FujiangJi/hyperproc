# hyperproc.correct.masks.zhai_cloud

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def zhai_cloud(blue, green, red, nir, swir1=None, swir2=None, valid=None, cloud=True, shadow=True, T1=0.01, t2=0.1, t3=0.25, t4=0.5, T7=9, T8=9, stats=None)
```

Cloud and cloud-shadow mask of Zhai et al. (2018), *ISPRS J. Photogramm.*
144:235-253, without the spatial shadow refinement.

Bands are reflectance arrays at roughly 440, 550, 660, 850 nm and, when the
sensor reaches the SWIR, 1570 and 2110 nm. With SWIR (paper eqs 1a-b, 3):

    CI_1 = (NIR + 2 SWIR1) / (blue + green + red)
    CI_2 = (blue + green + red + NIR + SWIR1 + SWIR2) / 6
    CSI  = (NIR + SWIR1) / 2

and without it ``CI_1 = 3 NIR / (blue + green + red)``,
``CI_2 = mean(blue, green, red, NIR)``, ``CSI = NIR``. The thresholds
adapt to the scene (eqs 5-7), taken over ``valid`` pixels:

    T2 = mean(CI_2) + t2 (max(CI_2) - mean(CI_2))
    T3 = min(CSI)   + t3 (mean(CSI)  - min(CSI))
    T4 = min(blue)  + t4 (mean(blue) - min(blue))

cloud  = |CI_1| < T1  or  CI_2 > T2,      then a T7 x T7 median filter
shadow = CSI < T3  and  blue < T4,        then a T8 x T8 median filter

``stats`` (from :func:`zhai_stats`) fixes the scene statistics the
thresholds are built from, so a mask evaluated block by block uses the
same T2-T4 everywhere; without it they come from this call's ``valid``.

Returns True where a pixel is cloud and/or shadow - i.e. the *bad* pixels,
the opposite sense of the other masks here, so combine it as ``~zhai``.

Two implementation choices matter more than they look, both checked on a
NEON line (Sept 2026): (1) the tests are evaluated on ``valid`` pixels
only - evaluating them on the fill value too makes every no-data pixel
"shadow" and the median filter drags that flag T8/2 pixels into the
swath; (2) the indices are computed in float64 - summing int16 x10000
integers overflows on the brightest pixels, which on that line pulled
max(CI_2) from 0.79 to 0.55 and T2 down with it, flagging 2.5x more
pixels at t2 = 0.1.
The paper's suggested ranges: T1 in {0.01, 0.1, 1, 10, 100}; t2 in
1/10..1/2; t3 in 1/4..3/4; t4 in 1/2..5/6; T7, T8 odd in 3..11.

On the CI_1 test: this function keeps the form of the reference
implementation the package was validated against, ``|CI_1| < T1`` joined
to the brightness test by OR. With the default ``T1 = 0.01`` that term
practically never fires, so clouds are found by ``CI_2 > T2`` alone. An
independent implementation of the same paper writes ``|CI_1 - 1| < T1``
joined by AND (clouds have a flat spectrum, CI_1 near 1), and the paper's
own experiments used T1 = 1, which is only meaningful for that reading. A
deliberate decision (Sept 2026) kept the validated form; change both the
centring and the conjunction together if that decision is revisited.

[Module and aliases](../hyperproc-correct-masks.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.masks.zhai_cloud --runtime`.
