"""``python -m hyperproc.atmos._runner``: ``apply_oe`` with the config adjusted.

Usage::

    python -m hyperproc.atmos._runner [--engine 6s --aerosol-model maritime --ozone 0.28]
        [--set forward_model/atmosphere/statevector/AOT550/prior_sigma=1.0]
        -- <every apply_oe argument, --emulator_base included>

Two things it can change that ``apply_oe`` does not expose: which engine
fills the look-up table, and any single value of the ISOFIT configuration
(``--set``), such as the aerosol prior.

``apply_oe`` is driven exactly as for sRTMnet (the ``--emulator_base`` keeps it
on that code path, which also sets the one-component forward model). Two hooks
change what runs underneath:

* ``template_construction.build_config`` is wrapped so that, right after
  ``apply_oe`` writes a config (the water-vapour presolve and the full one),
  the sRTMnet engine block is replaced by a 6S or libRadtran block. Geometry
  and date for 6S come from the MODTRAN template ``apply_oe`` also writes,
  the same way ISOFIT's own sRTMnet driver derives its 6S runs.
* ISOFIT's engine registry maps ``6s`` and ``LibRadTran`` to the hyperproc
  subclasses with the aerosol model exposed (:mod:`hyperproc.atmos.engines`).

Everything downstream (superpixel inversions, analytical line) is unchanged
and reads the swapped config.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


def libradtran_dir() -> Path:
    """The libRadtran tree holding ``bin/uvspec`` under ISOFIT's asset base."""
    from isofit.data import env
    base = Path(env.libradtran)
    for cand in [base] + sorted(p for p in base.glob("*") if p.is_dir()):
        if (cand / "bin" / "uvspec").is_file():
            return cand
    raise FileNotFoundError(f"no built libRadtran (bin/uvspec) under {base}; run hyperproc-atmos-setup --engine LibRadTran")


def apply_overrides(cfg: dict, overrides: dict):
    """Set values in a config by slash-separated path.

    Returns ``(changed, missing)``. A path that this config does not have is
    reported rather than raised: ``apply_oe`` writes two configs and the
    water-vapour presolve has no aerosol term, so an aerosol override applies
    to one of them only. The caller checks that every override reached at
    least one config.
    """
    changed, missing = [], []
    for path, value in overrides.items():
        node = cfg
        keys = [k for k in str(path).replace(".", "/").split("/") if k]
        for k in keys[:-1]:
            if not isinstance(node, dict) or k not in node:
                node = None
                break
            node = node[k]
        if not isinstance(node, dict) or keys[-1] not in node:
            missing.append(path)
            continue
        changed.append((path, node[keys[-1]], value))
        node[keys[-1]] = value
    return changed, missing


def rewrite_config(cfg_path: str | Path, engine: str | None, settings: dict, overrides: dict | None = None) -> None:
    """Adjust one ISOFIT config: swap the engine block and apply ``--set`` overrides."""
    from isofit.data import env
    from hyperproc.atmos.engines import write_settings

    cfg_path = Path(cfg_path)
    cfg = json.loads(cfg_path.read_text())
    if overrides:
        changed, missing = apply_overrides(cfg, overrides)
        for path, was, now in changed:
            print(f"config {cfg_path.name}: {path} {was} -> {now}", flush=True)
        for path in missing:
            print(f"config {cfg_path.name}: {path} not in this config, skipped", flush=True)
        rewrite_config.applied.update(path for path, *_ in changed)
    if engine is None:
        cfg_path.write_text(json.dumps(cfg, indent=4, sort_keys=True))
        return
    eng = cfg["forward_model"]["atmosphere"]["engine"]
    tpl_path = Path(eng["template_file"])
    tpl = json.loads(tpl_path.read_text())
    mi = tpl["MODTRAN"][0]["MODTRANINPUT"]
    if settings.get("ozone") is not None and mi["ATMOSPHERE"].get("O3STR") != settings["ozone"]:
        mi["ATMOSPHERE"]["O3STR"] = float(settings["ozone"])       # atm-cm; libRadtran reads it from here
        tpl_path.write_text(json.dumps(tpl, indent=4))
    block = {k: v for k, v in eng.items() if k not in ("emulator_file", "emulator_aux_file")}
    if engine == "6s":
        geo, surf = mi["GEOMETRY"], mi["SURFACE"]
        dt = datetime(2000, 1, 1) + timedelta(days=geo["IDAY"] - 1) + timedelta(hours=geo["GMTIME"])
        rel, vaa = float(geo["PARM1"]), float(geo["TRUEAZ"])
        block.update(engine_name="6s", engine_base_dir=str(env.sixs), day=dt.day, month=dt.month,
                     elev=float(surf["GNDALT"]), alt=float(geo["H1ALT"]), solzen=float(geo["PARM2"]),
                     solaz=float(min(vaa + rel, vaa - rel)), viewzen=180.0 - float(geo["OBSZEN"]), viewaz=vaa)
    elif engine == "LibRadTran":
        # ISOFIT's libRadtran engine writes radiance-mode tables with all six
        # transmittance components; the config has to say so, otherwise the
        # forward model reads them as one-component transmittances and the
        # retrieval rails (AOT 1.0, H2O at the grid top on the EMIT window).
        block.update(engine_name="LibRadTran", engine_base_dir=str(libradtran_dir()),
                     reptran_band_model=settings.get("band_model") or "coarse",
                     rt_mode="rdn", multipart_transmittance=True)
    else:
        raise ValueError(f"runner handles 6s and LibRadTran, not {engine!r}")
    cfg["forward_model"]["atmosphere"]["engine"] = block
    cfg_path.write_text(json.dumps(cfg, indent=4, sort_keys=True))
    write_settings(eng["sim_path"], engine=engine, **settings)


def install(engine: str | None, settings: dict, overrides: dict | None = None) -> None:
    """Wrap ``build_config`` so every config apply_oe writes is adjusted."""
    import isofit.utils.apply_oe as ao

    rewrite_config.applied = set()

    if engine is not None:
        from hyperproc.atmos.engines import register

        register()
    tmpl = ao.tmpl
    original = tmpl.build_config

    def build_config(paths, *args, **kwargs):
        result = original(paths, *args, **kwargs)
        for cfg in (paths.h2o_config_path, paths.isofit_full_config_path):
            if os.path.isfile(cfg):
                rewrite_config(cfg, engine, settings, overrides)
        # Whether an override matched is judged after the whole run: build_config
        # is called twice and writes the full config file both times, holding the
        # water-vapour presolve state the first time (no aerosol term in it).
        return result

    tmpl.build_config = build_config


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv:
        print("usage: _runner [--engine {6s,LibRadTran}] [--aerosol-model M] [--ozone ATM_CM] "
              "[--band-model B] [--set PATH=VALUE ...] -- <apply_oe args>", file=sys.stderr)
        return 2
    cut = argv.index("--")
    p = argparse.ArgumentParser(prog="hyperproc.atmos._runner")
    p.add_argument("--engine", choices=("6s", "LibRadTran"))
    p.add_argument("--set", action="append", default=[], metavar="PATH=VALUE",
                   help="set one ISOFIT config value, e.g. forward_model/atmosphere/statevector/AOT550/prior_sigma=1.0")
    p.add_argument("--aerosol-model", default=None)
    p.add_argument("--ozone", type=float, default=None, help="ozone column in atm-cm (0.30 = 300 DU)")
    p.add_argument("--band-model", default=None, help="libRadtran REPTRAN band model: coarse, medium, fine")
    a = p.parse_args(argv[:cut])
    settings = {k: v for k, v in (("aerosol_model", a.aerosol_model), ("ozone", a.ozone), ("band_model", a.band_model))
                if v is not None}
    overrides = {}
    for item in a.set:
        path, _, raw = item.partition("=")
        try:
            overrides[path] = json.loads(raw)
        except ValueError:
            overrides[path] = raw
    if a.engine is None and not overrides:
        print("nothing to change: pass --engine or --set", file=sys.stderr)
        return 2
    install(a.engine, settings, overrides)
    from isofit.utils.apply_oe import cli

    cli.main(args=argv[cut + 1:], standalone_mode=False)
    never = set(overrides) - getattr(rewrite_config, "applied", set())
    if never:
        raise KeyError(f"these config overrides matched nothing in the configs apply_oe wrote: {sorted(never)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
