# hyperproc 0.1.2 package and website review

Reviewed on 2026-10-03 against the current working tree, including the changes
since `55b41ec`, newly added files, package README, metadata, example pipelines,
and affected regression tests. Package implementation and original notebooks
were preserved. The package declares **0.1.2**; `CITATION.cff` agrees and records
**2026-10-03**. This review does not publish the package or create a release tag.

## Implementation review and corresponding website changes

| Changed source | Behavior observed in this checkout | Documentation synchronized |
|---|---|---|
| `hyperproc/__init__.py`, `CITATION.cff` | Version and citation date identify 0.1.2. | All API version labels, homepage, copyright, status, governance, and release metadata regenerated. |
| `hyperproc/archive/dlr.py` | Keeps partial files, requests byte ranges, handles 206/416, overwrites when Range is ignored, checks announced total size, retries transient errors and stops after consecutive no-progress failures. Authentication/permission errors do not use this retry path. | Archive workflow, troubleshooting, release notes, and complete source-derived API. |
| `hyperproc/_ncrc.py` | Diagnoses nonempty `.ncrc`, `.daprc`, `.dodsrc` without a final newline; skips unreadable paths; repair appends only a newline. | New internal API page, configuration, installation, and troubleshooting. |
| `hyperproc/archive/cmr.py` | Checks home-directory netCDF rc files after Earthdata login and warns before downloading. | Data-access/configuration guidance and generated source reference. |
| `hyperproc/atmos/setup.py` | `check()` reports affected home rc files; `setup()` repairs them before provisioning. | Installation and setup/configuration guidance explicitly distinguish reporting from file modification. |
| `hyperproc/atmos/correct.py` | Uses a conservative neighbor estimate; measured segmentation can lower but never raise it. Before ISOFIT, scans home/work rc files unless `NCRCENV_RC` is set. | Atmospheric workflow, reuse behavior, configuration, troubleshooting, and API source. |
| `py_tests/0_src_code/` changes | Data/output directories sit beside scripts; missing credentials can prompt on a terminal; noninteractive calls stop with instructions; acquisition pairing and policy flag improved. | Data-access pipeline section and EnMAP guide explain paths, `HYPERPROC_TESTS_DATA`, prompts, pairing, and `--accept-dlr-policy`. |
| `.gitignore` and moved example products | Example data/figures move under `py_tests/0_src_code/1_data` and `2_outputs`. | New pipeline paths documented. User-managed file moves and outputs were preserved. |

No existing public function signature was removed by the reviewed revisions.
The six added top-level functions are the three DLR transfer helpers and three
netCDF rc helpers. The reference now covers **54 modules, 465 top-level
definitions, and 68 public class methods/properties**.

## Inconsistencies fixed during the review

- Homepage installation used `{ python_requires }` instead of the expected
  double-brace placeholder, displaying raw text. Fixed and extended the build
  checker to reject malformed as well as unresolved snapshot placeholders.
- The README described Python 3.12 as an exclusive atmospheric requirement even
  though the current installed ISOFIT 4.1.5 metadata permits `>=3.11,<3.13`.
  README and website now recommend 3.12 while stating the actual constraints.
  Core hyperproc still declares `>=3.11`. This is not a tested Python matrix.
- README test totals were stale. Current collection found **748 tests**, of
  which **230** have archive test paths. README now distinguishes collected
  tests from a completed full-suite run and explains that `not data` can still
  include live network tests.
- Old release notes described previous help-message changes as the current
  release. Replaced them with the actual 0.1.2 behavior changes.
- Credential prose now reflects terminal prompts in revised example pipelines,
  rather than implying every later run is unconditionally noninteractive.

The user's expanded Miniconda installation instructions, optional SRF/notebook
installs, examples setup, and Windows/WSL distinctions were retained. Source
metadata and the local ISOFIT installation were used for package requirements;
no remote publication or upstream platform matrix was inferred.

## Verification

- Focused package regressions: **126 passed, 3 deselected** across
  `test_ncrc.py`, `test_archive_dlr.py`, and `test_atmos.py`, selecting
  `not data and not network`. DLR transfers were simulated; no live scene
  downloads or atmospheric retrievals were started.
- Full retained-test collection: **748 collected**; collection does not mean
  that all 748 were executed or passed.
- Five documentation example-auditor regressions passed.
- Static maintained-guide audit: **47 pages, 44 Python blocks, 79 source-bound
  calls**. These verify callable/argument shape and named installation extras,
  not scientific values or arbitrary dynamic behavior.
- Strict website build: **121 HTML pages**, **51,328 local references**,
  all API definitions/member anchors, source hashes and citation/package
  agreement, and **17 byte-identical notebook downloads**.
- Chromium verified version 0.1.2 across all 54 API module pages, the new helper
  module, updated source, homepage placeholder, installation constraints,
  archive recovery, atmospheric/troubleshooting text, and citation/release
  dates. Desktop and 390 px layouts passed without page-wide overflow or
  JavaScript errors. Existing breadcrumbs, category indication, and GitHub
  header remain present.

Stored notebook outputs and figures were preserved and not rerun. Thus tutorial
results remain historical saved outputs, not new evidence from running 0.1.2.
The user-created `_ncrc.py` and its test remain new working-tree files; include
them with the release sources. This review does not stage or commit user files.

## Reproduce and update

```bash
/home/fujiang/miniconda3/envs/hsi/bin/python -m pytest tests/test_ncrc.py tests/test_archive_dlr.py tests/test_atmos.py -m 'not data and not network' -q
docs-site/.venv/bin/python docs-site/manage.py build
docs-site/.venv/bin/python docs-site/manage.py check
```

After further package, metadata, guide, or saved notebook edits, rebuild and
refresh the site. The preview serves built files and does not rebuild on edits.
