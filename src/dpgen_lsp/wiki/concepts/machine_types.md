# Machine types

`machine.json` describes where each DP-GEN stage runs and how jobs are submitted.

## Local execution

Use `batch_type = Shell` for small tests or workstation runs. Keep resource requests small and avoid long production jobs.

## HPC schedulers

- `Slurm`: common on modern clusters; use `#SBATCH` headers through `custom_flags` when needed.
- `PBS`: PBS/Torque style clusters.
- `LSF`: LSF clusters using `bsub` style submission.

## Remote execution

SSH/remote contexts are useful when the editor host differs from the compute host. Validate `remote_root`, `username`, and host access before running long workflows.

## Cloud execution

Lebesgue/Bohrium cloud execution usually uses `context_type = Bohrium` and a `scass_type` such as `c2_m4_cpu`. Pick machine types that match the workload: CPU for DP-GEN orchestration and model deviation, GPU for training, and CPU-heavy nodes for FP calculations unless the backend supports GPUs.
