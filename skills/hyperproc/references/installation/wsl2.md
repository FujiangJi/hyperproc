# Windows with WSL2 for atmospheric processing

Use a compatible Windows host and a WSL2 Linux distribution. If WSL is absent and the user authorizes its system-level installation, run from an administrator PowerShell:

```powershell
wsl --install -d Ubuntu
wsl --list --verbose
```

Restart if requested, initialize the Linux user, and verify the selected distribution uses version 2. Do not interpret a pending reboot as a completed usable environment. [Microsoft's WSL instructions](https://learn.microsoft.com/en-us/windows/wsl/install) describe prerequisites and troubleshooting.

All subsequent package commands run **inside the Linux terminal**, not Windows PowerShell. Check `uname -m`, follow [Linux installation](linux.md), and use Linux Python/conda/compilers. Windows Python, Windows conda and Windows pip do not install into the WSL environment.

Use Linux paths for inputs/output. A Windows file can be accessible under `/mnt/c/...`; large retrieval work is generally better placed on the Linux filesystem when possible. Check actual storage and access rather than assuming host free space equals available WSL work space. Avoid simultaneous Windows/Linux processes modifying the same work directory.

Before ISOFIT assets or scenes are downloaded, show concrete volume/unknowns/destination/disk plan and obtain approval unless already explicitly authorized. Then provision and verify [atmospheric assets](atmos-assets.md), select a bounded valid input window and a unique run context.

If a notebook runs on Windows but processing runs in WSL, explicitly configure/choose the Linux kernel or run the processing script within Linux; matching notebook appearance is not matching interpreter/environment. The scope of this route is this package's documented Linux build workflow, not a universal claim about all upstream Windows possibilities.
