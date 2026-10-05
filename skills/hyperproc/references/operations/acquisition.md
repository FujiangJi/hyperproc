# Plan and approve actual acquisition

Reader support exceeds archive support. Anonymous bounded search is useful before selecting a download. Collection counts printed by the installed archive table are a package snapshot, not a live provider count. Query only supported sensor/level/backends; disclose missing size/sidecar information instead of assuming an empty estimate.

```python
import hyperproc as hp
hits = hp.search("EMIT", "L2A", bbox=(-121.0,34.0,-119.8,35.1),
                 date=("2023-04-20","2023-04-25"), count=5)
print(hits.table())
selected = hits[:1]
print(selected.size_gb, selected.unsized)
```

Do not put a download in this same exploratory snippet before the selection/volume plan is approved. NEON search yields site-months; listing flightlines uses `hp.files()` and needs NEON_TOKEN. DLR often lacks item sizes/asset lists; obtain a bounded provider estimate where practical or ask explicit approval for the unknown-size selection. Never treat unknown `size_mb` as zero bytes.

For the planning helper, save only approved-to-inspect record fields (name, size_mb, links); do not persist credential-bearing links/raw metadata. Placeholder link labels suffice for an offline count/size plan.

```json
[{"name":"chosen-granule","size_mb":2048,"links":["primary","ancillary"]}]
```

```bash
python /path/to/hyperproc/scripts/download_plan.py selection.json \
  --destination /data/chosen-scenes --budget-gib 5 --disk-factor 3
```

The helper never authenticates/downloads/writes; it reports known subtotal, unknown sizes/listings, budget/disk estimate and target. Disk factor is a planning choice for unpack/work copies, not measured completeness. Keep actual transfer destination, selected IDs/assets, reported sizes, ancillary requirements and user-approved budget in the run record.

**Before transfer, present that concrete plan and get approval unless the same selection and budget are already explicitly authorized.** If selection, total volume or destination materially expands, update the plan before continuing. A previously approved 2 GB scene is not permission to add a 35 GB flightline. For unknown sizes, agree a bounded selection and stopping/monitoring plan rather than an unrestricted query/download. The package itself may not enforce a hard byte cap.

After approval, execute the selected download with suitable credentials/workers and identify actual primary and companion files. DLR resumes `.part` files, but existing final nonempty files are reused without checksum proof. Stop on persistent failures; do not wrap it in endless retries. Distinguish cached/reused bytes from new transfer. Credentials/policy acceptance remain separate from volume approval.

See [archive details](archive-operations.md) for collections, credentials, NEON expansion, DLR CAS and map boundaries.
