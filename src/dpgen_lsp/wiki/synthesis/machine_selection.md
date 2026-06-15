# Machine selection

Choose resources by stage.

## Training

Use GPU nodes when DeePMD-kit is GPU-enabled. Keep one task per GPU unless benchmarking shows better packing.

## Model deviation

Usually CPU-friendly and embarrassingly parallel. Use scheduler arrays or multiple cores depending on the exploration engine.

## FP labeling

Use resources required by the selected `fp_style`:

- VASP/ABACUS/PWscf/CP2K: MPI CPU nodes are common.
- Gaussian: CPU nodes with memory suited to molecule size.
- Custom: match the user script requirements.

## Debugging

Start with `local-shell` or a short queue. After JSON and paths are validated, switch to production machine templates.
