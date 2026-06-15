# Training parameters

`default_training_param` contains the DeePMD-kit training configuration used by DP-GEN.

Common sections:

- `model`: descriptor and fitting network configuration
- `learning_rate`: learning-rate schedule
- `loss`: loss prefactors for energy, force, and virial
- `training`: systems, batch size, stop batch, seeds, and output frequency

For DP-GEN, keep the training systems managed by the workflow unless you have a specific reason to override them.
