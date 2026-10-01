"""Recover metadata for saved granule IDs; no scene downloads or notebook execution."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from granule_recordings import result_context


def recover(context):
    import hyperproc as hp
    sensor, level = context['sensor'], context['level']
    # Re-query the recorded interval only to find metadata for the recorded IDs.
    # Never replace the notebook's result set with whatever the archive returns.
    results = hp.search(sensor, level, **context['kwargs'], count=150, verbose=False)
    granules = []
    for row in context['rows']:
        candidates = [g for g in results if g.name.startswith(row['name']) and g.time
                      and g.time.strftime('%Y-%m-%d %H:%M') == row['time']]
        exact = [g for g in candidates if g.name == row['name']]
        candidates = exact or candidates
        if len(candidates) != 1 or candidates[0].bbox is None:
            raise ValueError(f"{sensor} {level}: saved identifier {row['name']} has {len(candidates)} metadata matches")
        granule = candidates[0]
        granules.append({'name': granule.name, 'saved_name': row['name'], 'sensor': sensor,
                         'level': level, 'time': row['time'], 'bbox': list(granule.bbox),
                         'size_mb': row['size_mb'], 'cloud': row['cloud'], 'browse': granule.browse,
                         'extent_kind': 'site location' if sensor == 'NEON' else 'granule bounding box'})
    return {'key': context['key'], 'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'query': context, 'granules': granules}


def main():
    notebook_path = ROOT.parent/'tests/0_src_code/search_download_tutorial.ipynb'
    notebook = json.loads(notebook_path.read_text())
    output = ROOT/'map-recordings'/notebook_path.stem
    output.mkdir(parents=True, exist_ok=True)
    jobs = []
    for index, cell in enumerate(notebook['cells']):
        if cell.get('cell_type') != 'code' or 'search_map(' not in ''.join(cell.get('source', [])) or not any('application/vnd.jupyter.widget-view+json' in o.get('data', {}) for o in cell.get('outputs', [])):
            continue
        context = result_context(notebook, index)
        if context is None:
            raise ValueError(f'No saved result context for map cell {index+1}')
        if (output/(context['key']+'.json')).exists():
            print(f'cell {index+1}: recorded metadata already available', flush=True)
        else:
            jobs.append((index+1, context))
    failures = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(recover, context): number for number, context in jobs}
        for future in as_completed(futures):
            number = futures[future]
            try:
                record = future.result()
                (output/(record['key']+'.json')).write_text(json.dumps(record, indent=2)+'\n')
                print(f"cell {number}: matched {len(record['granules'])} saved granules", flush=True)
            except Exception as error:
                failures.append(number)
                print(f'cell {number}: {type(error).__name__}: {error}', flush=True)
    if failures:
        raise SystemExit(f'Unresolved map cells: {failures}')


if __name__ == '__main__':
    main()
