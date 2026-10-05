#!/usr/bin/env python3
"""Read installed reader registry and archive coverage; no network/authentication."""
from __future__ import annotations
import argparse
import json


def reader_rows(hp):
    return [{'sensor': sensor, 'level': level, 'implemented': entry.loader is not None, 'expects': entry.expects, 'note': entry.note} for (sensor, level), entry in sorted(hp.REGISTRY.items())]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true')
    args=parser.parse_args()
    try:
        import hyperproc as hp
        data={'version': hp.__version__, 'source': hp.__file__, 'readers':reader_rows(hp), 'archive_table':hp.archive.describe(), 'archive_counts_note':'Collection counts printed by describe are the installed package snapshot, not a fresh provider query.', 'grid_note':'Registry reports support, not matching ground. Read references/sensors/grids.md and verify actual transforms/GLT/geolocation.'}
        if args.json:
            print(json.dumps(data,indent=2))
        else:
            print('hyperproc',data['version'])
            for row in data['readers']:
                print(row['sensor'],row['level'],'ready' if row['implemented'] else 'not implemented','—',row['expects'])
            print('\nARCHIVES\n'+str(data['archive_table']))
            print('\n'+data['grid_note'])
        return 0
    except Exception as exc:
        print(json.dumps({'status':'unavailable','error_type':type(exc).__name__,'action':'Check the active Python and installed hyperproc.'}))
        return 2

if __name__=='__main__':
    raise SystemExit(main())
