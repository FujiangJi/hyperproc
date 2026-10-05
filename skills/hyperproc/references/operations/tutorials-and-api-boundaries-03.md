## Tutorial interpretation

The published site contains 17 notebook-derived tutorials plus curated guides. Read [tutorial index](https://fujiangji.github.io/hyperproc/tutorials/) and [caveats](https://fujiangji.github.io/hyperproc/tutorials/caveats/). The manifest records reviewed page URLs/hashes; this bundle does not duplicate their full text. The [AVIRIS-3 walkthrough](https://fujiangji.github.io/hyperproc/tutorials/aviris3-walkthrough/) explains grouped corrections, retrieval reuse and limitations.

Downloaded notebook code may include local helpers such as `load_product()`, plotting, mosaic naming or scene pairing utilities. These are not additional package functions; inspect their definitions before adapting, or use an actual released API. Notebook variables like `FOUND`, `hits`, `mapped`, `datasets`, and `samples` require earlier setup; copied cell execution in isolation can be wrong. Replace local absolute paths and credentials placeholders with the user's actual authorized resources.

Saved execution numbers, figures, timing, map centers/footprints and outputs are historical. Static pages regenerate from notebooks/build inputs; they do not rerun the code. A missing widget state may prevent restoring the exact Jupyter map. Saved Leaflet map interactivity is browser pan/zoom, not live server search/download.

The saved AVIRIS-3 comparison at approximately 865 nm on one 500×500 window (median difference +0.0022, RMSE 0.0023, correlation 0.9998) is not a full-spectrum accuracy claim. Cached work is visible. Forced topographic demonstration does not justify applying every refused/inconclusive fit. Report the documented SWIR degradations as well as visible/NIR improvements.
