# hyperproc.atmos.correct.neighbor_cap

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def neighbor_cap(inputs: Inputs, segmentation_size: int) -> int
```

Most neighbours the scene can support.

Asking for more neighbours than there are superpixels makes the KD-tree
query return out-of-range indices and the analytical line crashes with an
IndexError. The count is estimated conservatively at half the nominal
count, and a previous run's label image, where there is one, can only
lower that (SLIC merges small segments, so it yields fewer than
pixels/size: a 60 x 60 patch at size 40 gave 61, not 90).

Only lower: taking the measured count outright made the cap - and with it
``--num_neighbors`` - depend on whether the work dir had run before. On a
window small enough for the cap to bind, the second call then always
asked for different settings from the first and found its own finished
product "made with different settings" (45 against 72 on 60 x 60 DESIS
and EnMAP windows). After a crash the measured count is still what lowers
the retry.

[Module and aliases](../hyperproc-atmos-correct.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.correct.neighbor_cap --runtime`.
