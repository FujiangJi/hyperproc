#!/usr/bin/env python3
"""Suggest a work-directory identity from explicit scene/region/settings; no writes."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path


def context_for(inputs,region,settings,work_root):
    if not isinstance(settings,dict) or not isinstance(region,dict):
        raise ValueError('Region and settings must be JSON objects.')
    def reject_secret_keys(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if re.search(r'token|password|secret|credential|auth|cookie',str(key),re.I):
                    raise ValueError('Credential-like settings do not belong in a run context.')
                reject_secret_keys(item)
        elif isinstance(value,list):
            for item in value:
                reject_secret_keys(item)
    reject_secret_keys(settings)
    reject_secret_keys(region)
    identities=[]
    for item in inputs:
        path=Path(item).expanduser().resolve();stat=path.stat()
        if not path.is_file():
            raise ValueError('Context inputs must identify real primary/companion/reference files.')
        identities.append({'path':str(path),'size_bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns,'fingerprint_kind':'path-size-mtime; not a content checksum'})
    if not identities:
        raise ValueError('Supply at least one input.')
    context={'inputs':sorted(identities,key=lambda x:x['path']),'region':region,'settings':settings}
    encoded=json.dumps(context,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    digest=hashlib.sha256(encoded).hexdigest()[:16]
    directory=Path(work_root).expanduser().resolve()/('run-'+digest)
    return {**context,'context_sha256_prefix':digest,'suggested_work_dir':str(directory),'work_dir_exists':directory.exists(),'does_not_write':True,'reuse_note':'A context hash prevents many accidental scene/window/settings collisions; verify existing run provenance and effective defaults before reuse. Include companions, reference grids, priors, coefficients and all relevant explicit parameters. Metadata fingerprints are not content hashes.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,action='append',required=True)
    parser.add_argument('--region',required=True,help='JSON region plus its grid identity, e.g. {"y":[600,800],"x":[600,800],"grid":"EMIT sensor"}.')
    parser.add_argument('--settings',required=True,help='JSON effective engine/stages/masks/reference/overrides; exclude secrets.')
    parser.add_argument('--work-root',type=Path,required=True)
    args=parser.parse_args()
    report=context_for(args.input,json.loads(args.region),json.loads(args.settings),args.work_root)
    print(json.dumps(report,indent=2,allow_nan=False))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
