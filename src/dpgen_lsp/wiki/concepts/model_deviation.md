# Model deviation

Model deviation estimates uncertainty by comparing predictions from an ensemble of trained models.

## Trust levels

For force-based selection:

- below `model_devi_f_trust_lo`: accurate region, usually no FP labeling
- between low and high trust: candidate frames for FP labeling
- above `model_devi_f_trust_hi`: failed or extrapolated region, often skipped or handled separately

Energy and virial trust levels follow the same low/high convention when enabled.

## Ensemble size

`numb_models` controls the model ensemble size. Four models is common. The length of `training_iter0_model_path`, when used, should match `numb_models`.

## Job layout

`model_devi_jobs` defines systems, temperatures, pressures, step counts, and task grouping. `sys_idx` values should point to valid entries in `sys_configs`.
