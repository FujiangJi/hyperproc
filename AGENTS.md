# hyperproc project guidance

For hyperproc installation, data acquisition, hyperspectral processing, or scientific interpretation, read [the shared skill entry](skills/hyperproc/SKILL.md) and follow its applicable instructions. Codex and Claude Code use that same workflow and reference collection.

Read only the chapters needed for the current task:

- Environment setup: [installation by OS and capability](skills/hyperproc/references/installation/index.md).
- Product selection and spatial windows: [sensor grids](skills/hyperproc/references/sensors/grids.md), then the relevant sensor chapter.
- API calls: [API index](skills/hyperproc/references/api/index.md) and the installed-package inspection helpers linked from the skill entry.
- Acquisition: [search and download workflow](skills/hyperproc/references/operations/acquisition.md).
- Processing: select the appropriate route in the shared skill entry; consult [work-directory reuse](skills/hyperproc/references/operations/work-directory-reuse.md) when resuming runs.
- Deliverables: [science-readiness criteria](skills/hyperproc/references/workflows/science-ready.md) and [execution validation](skills/hyperproc/references/operations/execution-validation.md).
- Package revisions: [version maintenance](skills/hyperproc/references/operations/version-maintenance.md).

Resolve each reference's relative links from its own directory. Resolve helper scripts from `skills/hyperproc/scripts/` and use the intended Python environment.

Maintain scientific guidance, examples, and API details in `skills/hyperproc/SKILL.md` and its `references/` and `scripts/`. Keep this file a short routing entry; update the shared resources instead of creating separate Codex or Claude copies.
