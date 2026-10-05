# Choose an installation route

Inspect existing interpreter/environment before creating another. Core hyperproc declares Python >=3.11; **Python 3.12 is the practical baseline** for this skill and reviewed ISOFIT 4.1.5 (which requires >=3.11,<3.13). Miniforge base Python may be newer; create a separate 3.12 processing environment. Installed metadata, not a future blanket restriction, determines compatibility.

| Platform | Chapter | Processing scope |
|---|---|---|
| Linux x86_64 / aarch64 | [Linux](linux.md) | Core and optional atmosphere, subject to engine/dependency availability |
| macOS Apple Silicon / Intel | [macOS](macos.md) | Native architecture core; atmosphere with working build tools/assets |
| Windows x86_64, native | [Windows](windows.md) | Core/other extras; verify dependency imports and small output |
| Windows requiring atmosphere | [WSL2](wsl2.md) | Run this release's Linux-oriented engine build inside WSL2 |
| Existing suitable Python, no conda | [venv](venv.md) | Pip-wheel route; external compilers still separate |

Use an existing Miniconda/Anaconda/Miniforge environment if it is suitable; the bootstrap choice is not a package requirement. Do not mix macOS arm64 and Rosetta x86_64 libraries in one environment. On unsupported OS/architecture combinations, verify wheels/toolchains rather than promising every package installs.

[Capabilities and package constraints](capabilities.md), [ISOFIT assets/build](atmos-assets.md), and [installation verification](verification.md) are separate so a core-only task need not read/run atmospheric setup. The commands below are recipes, not permission to mutate unrelated environments. An explicit request to install into an agreed isolated environment authorizes routine dependency installation there; data/asset transfers need their own concrete size/scope plan.

Canonical reviewed package source: [release manifest](../provenance/release-manifest.json). Official installation sources are cited in the OS chapters. Commands were reviewed on 2026-10-04; only the available Linux environment received runtime checks, not every OS.
