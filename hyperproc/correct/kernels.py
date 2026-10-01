"""BRDF kernels: Ross (volume scattering) and Li (geometric-optical) families.

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
"""

from __future__ import annotations

import numpy as np

VOLUME_KERNELS = ("ross_thick", "ross_thin")
GEOMETRIC_KERNELS = ("li_sparse", "li_dense", "li_sparse_r", "li_dense_r")


def phase_angle(sza, vza, raa):
    """Scattering phase angle xi between the sun and view directions."""
    cos_xi = np.cos(sza) * np.cos(vza) + np.sin(sza) * np.sin(vza) * np.cos(raa)
    return np.arccos(np.clip(cos_xi, -1.0, 1.0))


# --- volume scattering ------------------------------------------------------


def ross_thick(sza, vza, raa):
    """Ross-thick kernel (dense leaf canopy), Lucht et al. 2000 eq 38."""
    xi = phase_angle(sza, vza, raa)
    num = (np.pi / 2.0 - xi) * np.cos(xi) + np.sin(xi)
    return num / (np.cos(sza) + np.cos(vza)) - np.pi / 4.0


def ross_thin(sza, vza, raa):
    """Ross-thin kernel (sparse leaf canopy), Wanner et al. 1995 eq 29."""
    xi = phase_angle(sza, vza, raa)
    num = (np.pi / 2.0 - xi) * np.cos(xi) + np.sin(xi)
    return num / (np.cos(sza) * np.cos(vza)) - np.pi / 2.0


def volume_kernel(kind, sza, vza, raa):
    """Dispatch by name: ``"ross_thick"`` or ``"ross_thin"``."""
    if kind == "ross_thick":
        return ross_thick(sza, vza, raa)
    if kind == "ross_thin":
        return ross_thin(sza, vza, raa)
    raise ValueError(f"unknown volume kernel {kind!r}; choose from {VOLUME_KERNELS}")


# --- geometric-optical ------------------------------------------------------


def _li_terms(sza, vza, raa, b_r, h_b):
    """The shared pieces of every Li kernel, Wanner et al. 1995 eqs 43-47.

    The crown shape enters twice: ``b_r`` rescales both zenith angles to the
    equivalent spherical-crown geometry (eq 47), ``h_b`` sets the height at
    which the two shadows overlap (eq 44). ``cos t`` is clipped to [-1, 1] -
    beyond that the shadows do not overlap at all and the overlap term is 0.
    """
    sza_p = np.arctan(b_r * np.tan(sza))
    vza_p = np.arctan(b_r * np.tan(vza))
    sec_s = 1.0 / np.cos(sza_p)
    sec_v = 1.0 / np.cos(vza_p)
    tan_s, tan_v = np.tan(sza_p), np.tan(vza_p)

    d_sq = tan_s ** 2 + tan_v ** 2 - 2.0 * tan_s * tan_v * np.cos(raa)
    d_sq = np.maximum(d_sq, 0.0)                       # guard rounding
    cos_t = h_b * np.sqrt(d_sq + (tan_s * tan_v * np.sin(raa)) ** 2) / (sec_s + sec_v)
    t = np.arccos(np.clip(cos_t, -1.0, 1.0))
    overlap = (t - np.sin(t) * np.cos(t)) * (sec_s + sec_v) / np.pi

    cos_xi_p = (np.cos(sza_p) * np.cos(vza_p)
                + np.sin(sza_p) * np.sin(vza_p) * np.cos(raa))
    return overlap, sec_s, sec_v, cos_xi_p


def li_sparse(sza, vza, raa, b_r=1.0, h_b=2.0):
    """Li-sparse kernel, Wanner et al. 1995 eq 32 (not reciprocal)."""
    o, sec_s, sec_v, cos_xi_p = _li_terms(sza, vza, raa, b_r, h_b)
    return o - sec_s - sec_v + 0.5 * (1.0 + cos_xi_p) * sec_v


def li_sparse_r(sza, vza, raa, b_r=1.0, h_b=2.0):
    """Li-sparse-reciprocal kernel, Lucht et al. 2000 eq 40 (MODIS)."""
    o, sec_s, sec_v, cos_xi_p = _li_terms(sza, vza, raa, b_r, h_b)
    return o - sec_s - sec_v + 0.5 * (1.0 + cos_xi_p) * sec_s * sec_v


def li_dense(sza, vza, raa, b_r=1.0, h_b=2.0):
    """Li-dense kernel, Wanner et al. 1995 eq 33 (not reciprocal)."""
    o, sec_s, sec_v, cos_xi_p = _li_terms(sza, vza, raa, b_r, h_b)
    return (1.0 + cos_xi_p) * sec_v / (sec_s + sec_v - o) - 2.0


def li_dense_r(sza, vza, raa, b_r=1.0, h_b=2.0):
    """Li-dense-reciprocal kernel, Lucht et al. 2000 eq 41 (FlexBRDF default)."""
    o, sec_s, sec_v, cos_xi_p = _li_terms(sza, vza, raa, b_r, h_b)
    return (1.0 + cos_xi_p) * sec_s * sec_v / (sec_s + sec_v - o) - 2.0


def geometric_kernel(kind, sza, vza, raa, b_r=1.0, h_b=2.0):
    """Dispatch by name over :data:`GEOMETRIC_KERNELS`."""
    fn = {"li_sparse": li_sparse, "li_dense": li_dense,
          "li_sparse_r": li_sparse_r, "li_dense_r": li_dense_r}.get(kind)
    if fn is None:
        raise ValueError(f"unknown geometric kernel {kind!r}; choose from {GEOMETRIC_KERNELS}")
    return fn(sza, vza, raa, b_r=b_r, h_b=h_b)


# --- convenience ------------------------------------------------------------


def kernel_pair(sza, vza, raa, volume="ross_thick", geometric="li_dense_r",
                b_r=1.0, h_b=2.0):
    """Both kernels at once, as ``(k_vol, k_geo)``. Angles in radians."""
    return (volume_kernel(volume, sza, vza, raa),
            geometric_kernel(geometric, sza, vza, raa, b_r=b_r, h_b=h_b))


def reference_kernels(sza_ref, volume="ross_thick", geometric="li_dense_r",
                      b_r=1.0, h_b=2.0):
    """Kernels for the normalisation target: nadir view under solar zenith ``sza_ref``.

    This is what a BRDF-normalised ("NBAR-like") reflectance is expressed at.
    With ``vza = 0`` the relative azimuth is irrelevant; 0 is passed.
    """
    return kernel_pair(np.asarray(sza_ref, dtype=float), 0.0, 0.0,
                       volume=volume, geometric=geometric, b_r=b_r, h_b=h_b)
