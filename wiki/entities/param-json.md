# param.json

`param.json` describes the DP-GEN workflow: atom types, initial training data,
exploration configurations, model-deviation jobs, first-principles labeling
style, and engine-specific templates or parameters.

The LSP validates JSON syntax, docs-backed top-level fields, cross-field
consistency inside each file, and cross-artifact stage alignment between
`param.json` and `machine.json` (train / model_devi / fp).
relationships such as `mass_map` and `fp_pp_files` alignment with `type_map`,
threshold ordering, and path/glob existence for generated-input preflight.
