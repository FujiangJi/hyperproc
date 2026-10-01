"""Aerosol models each look-up-table engine can use.

sRTMnet is trained on one aerosol (continental) and cannot vary it. 6S selects
one of its built-in models by number; libRadtran starts from ``aerosol_default``
(Shettle rural boundary layer, background above 2 km) and can switch the
boundary-layer type to another Shettle haze. The keys below are what
``correct(aerosol_model=...)`` accepts.
"""

#: 6S ``iaer`` codes (4 = user-defined and 7 = stratospheric need extra input, so only these).
SIXS_AEROSOL = {"none": 0, "continental": 1, "maritime": 2, "urban": 3, "desert": 5, "biomass_burning": 6}

#: libRadtran Shettle haze types (``aerosol_haze``) layered on ``aerosol_default``
#: (rural boundary layer, background aerosol above 2 km, 50 km visibility).
#: None keeps ``aerosol_default`` alone, which is the rural type. OPAC mixtures
#: (``aerosol_species_file``) would need libRadtran's separately distributed
#: optical-property files, which the source tarball does not include.
LRT_AEROSOL = {"rural": None, "continental": None, "maritime": 4, "urban": 5, "tropospheric": 6}

AEROSOLS = {"sRTMnet": ("continental",), "6s": tuple(SIXS_AEROSOL), "LibRadTran": tuple(LRT_AEROSOL)}
