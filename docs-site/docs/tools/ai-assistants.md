# Using hyperproc with an AI assistant

The repository carries an **agent skill**: a set of instructions and helper
scripts that teach Claude Code and Codex how this package works. It is
distributed with the source, not with the wheel, and installing it is
optional.

## What it carries

The skill is not a copy of this documentation. It holds the things that are
easy to get wrong and that fail quietly:

- **Which grid a window indexes**, per sensor and level. Equal index ranges
  are not automatically the same ground: EMIT's atmospheric route works on the
  sensor grid while the default reader maps through the GLT, and PRISMA L1 is
  a swath where L2D is a mapped UTM grid.
- **Work-directory rules** for atmospheric retrieval, including the symptoms
  of a reused run: identical medians, repeated stored runtimes, or a
  retrieval that finished suspiciously fast on a different region.
- **What a diagnostic verdict means.** `skip`, `refuse` and `inconclusive`
  from the topographic gate, and an angular test that reports it cannot tell,
  are results to report rather than obstacles to work around.
- **Which products can be searched** and which have to be ordered, since the
  readers cover more than any public archive publishes.
- Helper scripts that read your **installed** package rather than a stored
  copy, so the sensor matrix and the API signatures cannot drift from the
  version you actually have.

## Installing it

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/FujiangJi/hyperproc.git
cd hyperproc && git sparse-checkout set skills
./skills/install.sh --claude
```

The last line takes `--claude`, `--codex` or `--both`.

| Option | Installs to |
|---|---|
| `--claude` | `~/.claude/skills/hyperproc` |
| `--codex` | `./skills/hyperproc`, plus a routing entry at the project root |

For Codex the routing entry's paths are generated from where the skill
actually landed, because an `AGENTS.md` copied from elsewhere would point at
directories that do not exist. **An existing `AGENTS.md` is never
overwritten**: the entry is written beside it as `AGENTS.hyperproc.md` for
you to merge.

Working inside a clone of this repository needs none of this. The root
`AGENTS.md` and `.claude/skills/hyperproc` are already in place.

## Checking it

```bash
python skills/hyperproc/scripts/env_report.py
python skills/hyperproc/scripts/sensor_table.py
python skills/hyperproc/scripts/validate_runtime.py
```

The first reports the interpreter, the installed version, which extras are
importable and which archives hold a credential, as booleans and never a
secret. The second prints the current reader and archive matrices. The third
runs deterministic checks against the installed package and names each one.

## What it does not do

It does not make the scientific decisions, download anything on its own, or
read or write your credentials. It reports what a diagnostic found, including
when the honest answer is that the data cannot support a conclusion.

The guidance was reviewed against a specific release. A newer hyperproc may
behave differently, and the skill's own
[version maintenance](https://github.com/FujiangJi/hyperproc/blob/main/skills/hyperproc/references/operations/version-maintenance.md)
notes say how to check.
