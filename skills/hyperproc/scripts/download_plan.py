#!/usr/bin/env python3
"""Prepare an offline volume/disk report from selected granule metadata; never download."""
from __future__ import annotations
import argparse
import json
import math
import shutil
from pathlib import Path


def plan_download(items, destination, budget_gib=None, disk_factor=3.0):
    if not isinstance(items,list) or not items:
        raise ValueError('Provide a nonempty JSON array of explicitly selected granules.')
    if disk_factor<1 or not math.isfinite(disk_factor):
        raise ValueError('Disk allowance factor must be finite and >=1.')
    if budget_gib is not None and (not math.isfinite(budget_gib) or budget_gib<=0):
        raise ValueError('Budget must be a positive finite GiB value.')
    names, known, unknown=[],[],[]
    assets=0;unlisted=0
    for item in items:
        name=item.get('name')
        if not isinstance(name,str) or not name:
            raise ValueError('Each selected record needs a name.')
        names.append(name)
        size=item.get('size_mb')
        if isinstance(size,(int,float)) and not isinstance(size,bool) and math.isfinite(size) and size>0:
            known.append(float(size))
        else:
            unknown.append(name)
        links=item.get('links')
        if isinstance(links,list) and links:
            assets+=len(links)
        else:
            unlisted+=1
    if len(set(names)) != len(names):
        raise ValueError('Selected granule identifiers must be unique; resolve duplicate selections before planning.')
    dest=Path(destination).expanduser().resolve();existing=dest
    while not existing.exists() and existing!=existing.parent:
        existing=existing.parent
    free=shutil.disk_usage(existing).free
    # Consistent with package Results size_gb convention, but providers may round
    # or omit ancillary assets. This is a reported estimate, not measured bytes.
    subtotal_gib=sum(known)/1024.0
    complete=not unknown and not unlisted
    return {'selected_granules':names,'granule_count':len(names),'known_asset_link_count':assets,'granules_without_asset_listing':unlisted,'reported_size_subtotal_gib':subtotal_gib,'unknown_size_granules':unknown,'complete_reported_estimate':complete,'budget_gib':budget_gib,'within_budget':subtotal_gib<=budget_gib if complete and budget_gib is not None else None,'destination':str(dest),'disk_free_gib':free/1024**3,'disk_allowance_factor':disk_factor,'estimated_disk_allowance_gib':subtotal_gib*disk_factor if complete else None,'estimated_fits_disk':subtotal_gib*disk_factor<=free/1024**3 if complete else None,'does_not_download':True,'approval_instruction':'Show this concrete selection, known volume and unknowns, destination and unpack/work allowance. Obtain user approval before transfer unless this exact selection and budget are already explicitly authorized. Unknown sizes are not zero. Missing size/listing requires a bounded provider estimate or explicit approval of unknown-size transfer.','estimate_note':'Reported MB-to-GiB convention follows Results; provider units/rounding, sidecars and unpacked/work files can differ. Disk factor is a disclosed planning choice, not a measured guarantee.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('selection',type=Path,help='JSON [{name,size_mb,links}]; omit credential-bearing provider payloads.')
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--budget-gib',type=float)
    parser.add_argument('--disk-factor',type=float,default=3.0)
    args=parser.parse_args()
    report=plan_download(json.loads(args.selection.read_text()),args.destination,args.budget_gib,args.disk_factor)
    print(json.dumps(report,indent=2,allow_nan=False))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
