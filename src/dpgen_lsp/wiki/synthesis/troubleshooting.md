# DP-GEN troubleshooting

## JSON parses but DP-GEN fails

Check paths relative to the working directory, not only the editor location. Validate pseudopotential, INCAR/INPUT, initial data, and system configuration paths.

## No FP tasks are selected

Review model deviation trust levels. If thresholds are too strict or too loose, frames may all be classified as accurate or failed.

## Too many FP tasks

Reduce `fp_task_max`, narrow trust windows, or shorten exploration jobs while debugging.

## Type or mass mismatch

Ensure `type_map`, `mass_map`, pseudopotential lists, and model type maps share the same ordering.

## Scheduler submission fails

Confirm `batch_type`, resource keys, queue/partition names, modules, and custom submit flags for the target cluster.
