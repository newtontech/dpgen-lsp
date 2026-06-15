# First-principles engines

`fp_style` selects the first-principles backend used in the labeling stage.

## Common engines

- `vasp`: widely used for materials systems; requires `fp_pp_path`, `fp_pp_files`, and `fp_incar`.
- `gaussian`: useful for molecular and cluster calculations; uses Gaussian keywords and charge/multiplicity options.
- `cp2k`: suitable for large molecular/material systems; check stress tensor output if virials are needed.
- `abacus`: supports plane-wave and LCAO workflows; pseudopotential and orbital lists must match `type_map`.
- `pwscf`: Quantum ESPRESSO `pw.x`; requires pseudopotentials and either `fp_params` or `user_fp_params`.
- `siesta`: localized orbital DFT; requires SIESTA `fp_params` and pseudopotential files.
- `pwmat`: PWmat first-principles backend.
- `cpx`: Quantum ESPRESSO `cp.x` / CPMD workflow.
- `amber/diff`: DPRc/Amber differential labeling, usually paired with `model_devi_engine = amber`.
- `custom`: user-supplied FP script using dpdata-compatible input and output formats.

## Simplify special case

In `dpgen simplify`, `fp_style = none` means the input data is already labeled or no relabeling is wanted.
