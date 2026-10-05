#!/usr/bin/env python3
"""Inspect a supported provider product; numerical sampling is opt-in and bounded."""
from __future__ import annotations
import argparse
import json
import math
import re
from pathlib import Path

SAFE_ATTRS = ('sensor', 'level', 'granule', 'stem', 'units', 'datetime', 'crs', 'transform', 'geometry_fixed')
GEOMETRY = ('sza', 'saa', 'vza', 'vaa', 'raa', 'slope', 'aspect', 'cos_i', 'elev', 'lat', 'lon')
SECRET_KEY = re.compile(r'token|password|passwd|secret|credential|auth|cookie|username', re.I)

def json_value(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items() if not SECRET_KEY.search(str(k))}
    if isinstance(value, (list, tuple)):
        return [json_value(v) for v in value]
    if hasattr(value, 'tolist'):
        return json_value(value.tolist())
    return str(value)

def parse_reader_options(payload: str) -> dict:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError('Reader options must be a JSON object.')
    def check(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if SECRET_KEY.search(key):
                    raise ValueError('Credential-like reader options are not accepted; use the proper existing credential configuration.')
                check(item)
        elif isinstance(value, list):
            for item in value:
                check(item)
    check(data)
    return data

def inspect_dataset(ds, *, sample: bool = False, window=None) -> dict:
    import hyperproc as hp
    import numpy as np
    var = hp.main_var(ds)
    cube = ds[var]
    report = {
        'main_variable': var,
        'dimensions': dict(ds.sizes),
        'cube': {'dims': list(cube.dims), 'shape': list(cube.shape), 'dtype': str(cube.dtype), 'one_full_cube_bytes': int(cube.size * cube.dtype.itemsize), 'units': json_value(cube.attrs.get('units'))},
        'attributes': {k: json_value(ds.attrs[k]) for k in SAFE_ATTRS if k in ds.attrs},
        'variables': {k: {'dims': list(v.dims), 'dtype': str(v.dtype), 'units': json_value(v.attrs.get('units'))} for k, v in ds.data_vars.items()},
        'geometry_available': [k for k in GEOMETRY if k in ds],
        'quality_related_variables': [k for k in ds.data_vars if any(x in k.lower() for x in ('mask', 'quality', 'flag', 'cloud', 'valid'))],
        'interpretation': 'Quantity and geometry provenance must be checked from provider metadata; names/available layers alone do not establish validity.',
        'sampling': None,
    }
    if window is not None and not sample:
        raise ValueError('Use --sample when supplying a numerical sampling window.')
    if 'wavelength' in ds.coords:
        wl = np.asarray(ds.wavelength.values, dtype=float)
        if wl.ndim != 1:
            raise ValueError('Expected one-dimensional wavelength coordinates.')
        valid = wl[np.isfinite(wl)]
        report['spectral'] = {
            'count': len(wl), 'coordinate_units': json_value(ds.wavelength.attrs.get('units')),
            'shared_interface_convention': 'nm; verify provider/source metadata',
            'min': float(valid.min()) if len(valid) else None,
            'max': float(valid.max()) if len(valid) else None,
            'finite': bool(np.isfinite(wl).all()),
            'strictly_increasing': bool(np.isfinite(wl).all() and np.all(np.diff(wl) > 0)),
        }
        for coord in ('fwhm', 'good_wavelength', 'band_index'):
            if coord in ds.coords:
                report['spectral'][coord] = json_value(ds[coord].values)
    if sample:
        if not all(d in cube.dims for d in ('y', 'x')):
            raise ValueError('Bounded sampling requires y/x cube dimensions.')
        ny, nx = ds.sizes['y'], ds.sizes['x']
        if window is None:
            wy, wx = min(128, ny), min(128, nx)
            y0, x0 = (ny-wy)//2, (nx-wx)//2
            window = [y0, y0+wy, x0, x0+wx]
        y0, y1, x0, x1 = window
        if not (0 <= y0 < y1 <= ny and 0 <= x0 < x1 <= nx):
            raise ValueError('Window must be nonempty half-open y/x ranges within cube dimensions.')
        # Prevent an accidentally enormous opt-in diagnostic; use a processing
        # script with an explicit resource plan for larger reads.
        block = cube.isel(y=slice(y0,y1), x=slice(x0,x1))
        expected_bytes = int(block.size * block.dtype.itemsize)
        if expected_bytes > 256 * 1024**2:
            raise ValueError('Sampling window exceeds 256 MiB of raw cube values; choose a smaller window.')
        arr = np.asarray(block.values)
        finite_mask = np.isfinite(arr)
        values = arr[finite_mask]
        report['sampling'] = {
            'window': list(window), 'cube_bytes': expected_bytes,
            'finite_fraction': float(finite_mask.mean()),
            'finite_min': float(values.min()) if values.size else None,
            'finite_max': float(values.max()) if values.size else None,
            'finite_mean': float(values.mean()) if values.size else None,
            'scope': 'Only this selected window, not a scene-wide quality assessment. Opening may already have read ancillary data.',
        }
    return json_value(report)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('product', type=Path)
    parser.add_argument('--sensor')
    parser.add_argument('--level')
    parser.add_argument('--reader-options', default='{}', help='JSON kwargs accepted by the sensor reader; no credentials.')
    parser.add_argument('--sample', action='store_true')
    parser.add_argument('--window', nargs=4, type=int, metavar=('Y0','Y1','X0','X1'))
    parser.add_argument('--output', type=Path, help='New JSON report; existing files are not overwritten.')
    args = parser.parse_args()
    if args.window is not None and not args.sample:
        parser.error('--window requires --sample')
    if args.output and args.output.exists():
        parser.error('Output already exists; choose a new report path.')
    options = parse_reader_options(args.reader_options)
    if any(k in options for k in ('path', 'sensor', 'level')):
        parser.error('Supply product, sensor and level via their dedicated arguments.')
    import hyperproc as hp
    ds = hp.open(args.product, sensor=args.sensor, level=args.level, **options)
    try:
        report = inspect_dataset(ds, sample=args.sample, window=args.window)
    finally:
        ds.close()
    payload = json.dumps(report, indent=2, allow_nan=False) + '\n'
    if args.output:
        with args.output.open('x') as stream:
            stream.write(payload)
    else:
        print(payload, end='')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
