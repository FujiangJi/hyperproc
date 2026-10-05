#!/usr/bin/env python3
"""Report installed metadata without importing hyperproc or authenticating."""
from __future__ import annotations
import argparse
import importlib.metadata as md
import importlib.util
import json
import platform
import sys
from pathlib import Path

BASELINE = '0.1.2'
CAPABILITIES = {
    'core': ['numpy', 'xarray', 'dask', 'rasterio', 'rioxarray', 'h5py', 'netCDF4', 'h5netcdf', 'scipy', 'pyproj', 'shapely', 'affine', 'threadpoolctl'],
    'search': ['earthaccess', 'requests'],
    'search-map': ['earthaccess', 'requests', 'ipyleaflet', 'ipywidgets', 'geopandas'],
    'atmos': ['isofit'],
    'brdf': ['earthengine-api'],
    'srf': ['openpyxl', 'requests'],
    'notebooks': ['jupyterlab', 'ipykernel', 'nbconvert', 'matplotlib', 'pandas'],
    'test': ['pytest'],
}

def inspect_environment(capabilities: list[str]) -> dict:
    needed = ['hyperproc'] + CAPABILITIES['core']
    for name in capabilities:
        needed.extend(CAPABILITIES[name])
    versions = {}
    for name in dict.fromkeys(needed):
        try:
            versions[name] = md.version(name)
        except md.PackageNotFoundError:
            versions[name] = None
    try:
        dist = md.distribution('hyperproc')
        declared = list(dist.requires or [])
        py_requires = dist.metadata.get('Requires-Python')
    except md.PackageNotFoundError:
        declared, py_requires = [], None
    constraints, warnings = [], []
    try:
        from packaging.requirements import Requirement
        from packaging.specifiers import SpecifierSet
        from packaging.markers import default_environment
        extras = [''] + [c for c in capabilities if c != 'core']
        if 'search-map' in extras and 'search' not in extras:
            extras.append('search')
        for raw in declared:
            req = Requirement(raw)
            if req.marker and not any(req.marker.evaluate({**default_environment(), 'extra': e}) for e in extras):
                continue
            try:
                ver = md.version(req.name)
            except md.PackageNotFoundError:
                ver = None
            constraints.append({'requirement': raw, 'installed': ver, 'satisfied': ver is not None and (not req.specifier or ver in req.specifier)})
        if py_requires and platform.python_version() not in SpecifierSet(py_requires):
            warnings.append('Active Python does not satisfy installed hyperproc Requires-Python.')
    except ImportError:
        warnings.append('packaging is unavailable; dependency version constraints were not evaluated.')
    if versions['hyperproc'] != BASELINE:
        warnings.append('Installed hyperproc differs from skill baseline 0.1.2; verify the intended installed signatures/source before processing.')
    if 'atmos' in capabilities and versions.get('isofit'):
        isofit_python = md.metadata('isofit').get('Requires-Python')
        try:
            if isofit_python and platform.python_version() not in SpecifierSet(isofit_python):
                warnings.append('Active Python does not satisfy installed ISOFIT Requires-Python.')
        except NameError:
            pass
    else:
        isofit_python = None
    missing = [k for k, v in versions.items() if v is None]
    bad_constraints = [c for c in constraints if not c['satisfied']]
    return {
        'baseline': BASELINE, 'python_executable': sys.executable,
        'python_version': platform.python_version(), 'platform': platform.platform(),
        'requested_capabilities': capabilities, 'versions': versions,
        'hyperproc_import_discoverable': importlib.util.find_spec('hyperproc') is not None,
        'requires_python': py_requires, 'isofit_requires_python': isofit_python,
        'dependency_constraints': constraints, 'missing': missing,
        'metadata_ready': not missing and not bad_constraints and not any('Active Python' in w for w in warnings),
        'warnings': warnings,
        'scope': 'Metadata/discovery only; imports, ABI, credentials, data, scientific applicability and external assets are not validated.',
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capability', action='append', choices=sorted(CAPABILITIES), default=[])
    parser.add_argument('--credentials', action='store_true', help='Local credential availability booleans only; no authentication.')
    parser.add_argument('--atmos-engine', action='append', help='Opt-in installed atmospheric asset/compiler check for an engine; no setup/download.')
    parser.add_argument('--output', type=Path, help='New JSON file; existing files are not overwritten.')
    args = parser.parse_args()
    report = inspect_environment(args.capability or ['core'])
    if args.credentials:
        try:
            import hyperproc as hp
            report['credentials'] = {str(k): bool(v) for k, v in hp.archive.credentials().items()}
        except Exception as exc:
            report['credentials_error_type'] = type(exc).__name__
    if args.atmos_engine:
        try:
            from hyperproc.atmos.setup import check
            report['atmospheric_assets'] = check(engines=tuple(args.atmos_engine), verbose=False)
        except Exception as exc:
            report['atmospheric_check_error_type'] = type(exc).__name__
    payload = json.dumps(report, indent=2, allow_nan=False) + '\n'
    if args.output:
        with args.output.open('x') as stream:
            stream.write(payload)
    else:
        print(payload, end='')
    return 0 if report['metadata_ready'] else 2

if __name__ == '__main__':
    raise SystemExit(main())
