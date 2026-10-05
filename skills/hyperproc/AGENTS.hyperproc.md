<!--
  Template. install.sh replaces {{SKILL_ROOT}} with the path the skill was
  installed to, relative to the project root, and writes the result where
  Codex looks for it. Nothing reads this file in place.
-->

# hyperproc project guidance

For hyperproc installation, data acquisition, hyperspectral processing, or scientific interpretation, read [the shared skill entry]({{SKILL_ROOT}}/SKILL.md) and follow its applicable instructions. Codex and Claude Code use that same workflow and reference collection.

Read only the chapters needed for the current task:

- Environment setup: [installation by OS and capability]({{SKILL_ROOT}}/references/installation/index.md).
- Product selection and spatial windows: [sensor grids]({{SKILL_ROOT}}/references/sensors/grids.md), then the relevant sensor chapter.
- API calls: [API index]({{SKILL_ROOT}}/references/api/index.md) and the installed-package inspection helpers linked from the skill entry.
- Acquisition: [search and download workflow]({{SKILL_ROOT}}/references/operations/acquisition.md).
- Processing: select the appropriate route in the shared skill entry; consult [work-directory reuse]({{SKILL_ROOT}}/references/operations/work-directory-reuse.md) when resuming runs.
- Deliverables: [science-readiness criteria]({{SKILL_ROOT}}/references/workflows/science-ready.md) and [execution validation]({{SKILL_ROOT}}/references/operations/execution-validation.md).
- Package revisions: [version maintenance]({{SKILL_ROOT}}/references/operations/version-maintenance.md).

Resolve each reference's relative links from its own directory. Resolve helper scripts from `{{SKILL_ROOT}}/scripts/` and use the intended Python environment.

Maintain scientific guidance, examples, and API details in `{{SKILL_ROOT}}/SKILL.md` and its `references/` and `scripts/`. Keep this file a short routing entry; update the shared resources instead of creating separate Codex or Claude copies.
