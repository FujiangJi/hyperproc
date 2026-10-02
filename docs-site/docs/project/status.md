# Documentation status

This site documents the adjacent **hyperproc {{ source_version }}** checkout. Its manifest records {{ api_modules }} Python modules, {{ functions_and_classes }} top-level functions/classes, {{ class_members }} public class methods/properties, {{ notebooks }} notebooks, and {{ saved_figures }} saved PNG figures. Version and counts are refreshed at build time.

| Evidence | Source and meaning |
|---|---|
| Package version and Python requirement | `hyperproc/__init__.py` and `pyproject.toml`; Python {{ python_requires }} |
| Maintainer and repository | `pyproject.toml`; Fujiang Ji, [FujiangJi/hyperproc](https://github.com/FujiangJi/hyperproc) |
| License and citation | Root `LICENSE` (MIT) and `CITATION.cff` |
| Source-derived API | Statically extracted signatures, docstrings, and source |
| Saved notebook result | Stored output from a previous run; not rerun for this site |
| Documentation verification | Strict build; links/assets/fragments; function/class/member coverage; source-signature checks for maintained Python examples; install extras; notebook copies; package/README/metadata and website source hashes |
| Scientific validation | Requires separate algorithm tests and independent benchmarks |

The current source includes archive search/download and the optional notebook map, in addition to readers, corrections, quality, spectral tools, alignment, and export. Reader coverage and archive-search coverage are distinct; see [data access](../getting-started/data-access.md).

## Remaining evidence limits

A local version and packaging declaration do not verify PyPI availability, a GitHub release/tag, or a complete platform/dependency CI matrix. The citation metadata declares a release date; the website does not verify a release archive or DOI. Current artwork has no institutional affiliation label.

The build never imports hyperproc, executes notebooks, queries archives, or runs retrievals. No public deployment is configured. [Testing and reproducibility](../development/testing.md) describes the package's test layers.
