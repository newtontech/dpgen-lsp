# `numb_models`

`numb_models` is the number of models trained in each active-learning iteration.

Typical value: `4`.

Related fields:

- `default_training_param`: shared model/training settings
- `training_iter0_model_path`: optional pretrained model paths for iteration 0
- model deviation trust levels: uncertainty is measured across the ensemble

If `training_iter0_model_path` is provided, its length should match `numb_models`.
