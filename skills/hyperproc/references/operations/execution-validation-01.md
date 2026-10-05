## A useful completion contract

Deliver the output the user requested, its generating Python script/command, and enough provenance to repeat and interpret it. Simple inspection does not require a fabricated complex directory tree. For multi-stage processing, keep source data immutable and separate work/cache/output directories according to the user's conventions. Use distinct experiment names for parameter changes and report when a file was reused.

Before execution establish: input identity and quantity, eligible bands/region, required sidecars/geometry, selected QA, intended stages, dependencies/assets/access, estimated memory/disk and outputs. Resolve only material ambiguities. Continue authorized reversible local work without adding an approval checklist for hypothetical risk.
