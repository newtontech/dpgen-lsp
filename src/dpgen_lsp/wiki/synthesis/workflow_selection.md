# Workflow selection

Use this guide to choose a DP-GEN workflow.

- Need a full active-learning loop from initial data to improved potential: use `dpgen run`.
- Need to reduce and relabel an existing dataset: use `dpgen simplify`.
- Need initial bulk structures and short AIMD data: use `dpgen init_bulk`.
- Need surface/slab structures: use `dpgen init_surf`.
- Need reactive molecular initial data from ReaxFF and Gaussian labeling: use `dpgen init_reaction`.

After generating initial data, feed the resulting labeled systems into `init_data_sys` or equivalent fields in the main `dpgen run` parameter file.
