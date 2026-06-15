# FP task limits

`fp_task_min` and `fp_task_max` control how many candidate frames are labeled in one iteration.

- `fp_task_min`: minimum number of FP tasks to launch
- `fp_task_max`: maximum number of FP tasks to launch

`fp_task_min` should not exceed `fp_task_max`.

Use lower values while debugging templates and larger values for production active-learning iterations.
