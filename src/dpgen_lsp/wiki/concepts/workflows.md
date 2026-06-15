# DP-GEN workflows

DP-GEN uses separate workflows for different stages of potential development.

## `dpgen run`

Main active-learning loop. It uses `param.json` for system, training, exploration, and first-principles settings, and `machine.json` for execution resources. Each iteration contains:

1. `00.train`
2. `01.model_devi`
3. `02.fp`

## `dpgen simplify`

Dataset reduction workflow. It trains an ensemble, evaluates model deviation on existing data, picks representative uncertain frames, and optionally relabels them with FP calculations.

## `dpgen init_bulk`

Initial bulk data generation. Stages typically include relaxation, perturb/scale, short AIMD, and data collection.

## `dpgen init_surf`

Surface configuration generation. It builds slabs with selected Miller indices and vacuum settings, then perturbs/scales them for later exploration.

## `dpgen init_reaction`

Reactive initial data workflow driven by ReaxFF trajectories and Gaussian-style force calculations.
