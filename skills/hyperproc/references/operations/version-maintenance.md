# Installed versions and maintainable knowledge

The offline API baseline is a released, verified 0.1.2 wheel. Live scripts read installed source/metadata/registry, so a compatible 0.1.3 installation updates their signatures and support tables without rebuilding the skill. That does **not** automatically update physical meanings, processing behavior, QA semantics, algorithm assumptions or scientific validation.

For a newer installed version:

1. Record distribution version, imported path and Python/dependencies. Detect editable/shadowed sources when metadata differs from code.
2. Use `api_index.py --list-modules` and exact `--symbol ... --runtime --doc` for proposed calls. No truncated signatures; missing optional imports are reported explicitly.
3. Read the new release notes/relevant installed source and published documentation for changed behavior. Preserve the user's selected version rather than silently downgrading to this baseline.
4. Rerun relevant small known-answer/integration checks; do not launch every expensive retrieval/download just to update signature knowledge.
5. Revise only affected scientific chapters, sensor support/grid statements and offline symbol references when maintaining this skill. Keep source hashes/review date and validation scope accurate.

AST mode includes all installed Python modules and declared functions/classes/members without importing optional submodules. Runtime mode confirms a selected callable's actual alias, generated class signature or decorator behavior. It may fail if optional dependencies are absent; absence is not proof the symbol never exists. Native/C/inherited dynamically created objects may need runtime inspection rather than AST declarations.

The root skill routes to short topic files. There is one canonical offline symbol reference and one set of operational guidance, with external links to website context. No duplicate 47-guide/120-article mirrors are retained. Machine inventories are for scripts; do not load them wholesale into the agent context.

Use the [validation record](../provenance/validation.md) to separate reviewed baseline coverage from actual runtime tests and independent scientific claims.
