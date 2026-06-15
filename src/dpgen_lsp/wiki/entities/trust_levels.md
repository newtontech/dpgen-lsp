# Trust levels

Trust levels define the model-deviation window used to select candidate frames.

## Force trust

- `model_devi_f_trust_lo`: lower force-deviation threshold
- `model_devi_f_trust_hi`: upper force-deviation threshold

The low threshold should be smaller than the high threshold.

## Optional thresholds

Some workflows also use energy or virial thresholds:

- `model_devi_e_trust_lo` / `model_devi_e_trust_hi`
- `model_devi_v_trust_lo` / `model_devi_v_trust_hi`

Use consistent units with the exploration engine and DP-GEN documentation.
