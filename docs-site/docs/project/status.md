# Documentation status

This site documents the adjacent **hyperproc {{ source_version }}** checkout. Its manifest records {{ api_modules }} Python modules, {{ functions_and_classes }} top-level functions/classes, {{ notebooks }} notebooks, and {{ saved_figures }} saved PNG figures. Version and counts are refreshed at build time.

| Evidence | Source and meaning |
|---|---|
| Package version and Python requirement | `hyperproc/__init__.py` and `pyproject.toml`; Python {{ python_requires }} |
| Maintainer and repository | `pyproject.toml`; Fujiang Ji, [FujiangJi/hyperproc](https://github.com/FujiangJi/hyperproc) |
| License and citation | Root `LICENSE` (MIT) and `CITATION.cff` |
| Source-derived API | Statically extracted signatures, docstrings, and source |
| Saved notebook result | Stored output from a previous run; not rerun for this site |
| Documentation verification | Strict build and local links, assets, fragments, API coverage, notebook copies, and source hashes |
| Scientific validation | Requires separate algorithm tests and independent benchmarks |

The current source includes archive search/download and the optional notebook map, in addition to readers, corrections, quality, spectral tools, alignment, and export. Reader coverage and archive-search coverage are distinct; see [data access](../getting-started/data-access.md).

## Remaining evidence limits

A local version and packaging declaration do not verify PyPI availability, a GitHub release/tag, or a complete platform/dependency CI matrix. The citation metadata declares a release date; the website does not verify a release archive or DOI. Institutional approval of the affiliation artwork remains unconfirmed.

The build never imports hyperproc, executes notebooks, queries archives, or runs retrievals. No public deployment is configured. [Testing and reproducibility](../development/testing.md) describes the package's test layers.
