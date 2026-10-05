# hyperproc.spectral.smoothing.find_spikes

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def find_spikes(spectrum, threshold: float=0.018, nups: int=1, ndowns: int | None=None, min_height: float=-np.inf) -> np.ndarray
```

Bands belonging to an upward spike, as R's ``pracma::findpeaks`` marks them.

A faithful port, because reproducing a published pipeline means reproducing
its peak finder. The sign of the first difference becomes a string of ``+``
and ``-``, runs matching ``[+]{nups,}[-]{ndowns,}`` are peaks, and a peak
survives when it exceeds the **higher** of its two ends by ``threshold``.

For every surviving peak exactly three bands are marked: the peak, the band
where its rise began and the band where its fall ended. Not the span
between them. On a real PRISMA spectrum that is 11 to 26 bands of 230.

Note that this finds maxima only. Downward spikes are left for the spline.

Args:
    spectrum: one spectrum, in the order the bands are stored.
    threshold: minimum height above the higher end of the peak.
    nups, ndowns: how many rises and falls make a peak; ``ndowns`` defaults
        to ``nups``.
    min_height: peaks below this absolute value are ignored.

Returns:
    Boolean mask, True where a band belongs to a peak.

[Module and aliases](../hyperproc-spectral-smoothing.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral.smoothing.find_spikes --runtime`.
