# Phase 2 Tasks

- `[x]` Create `rviz` configuration directory in `one_hand_interface`.
- `[x]` Add default `view_robot.rviz` configuration file.
- `[x]` Update `setup.py` to install the `rviz` directory.
- `[x]` Modify `sim.launch.py` to accept a `rviz` launch argument (default true) and spawn the `rviz2` node.
- `[x]` Build and test RViz integration with MuJoCo.

## Schema Update (Gate Status)
Per the Human Verification Gate (HVG) rules, each sub-phase row must now include a Gate Status:
`PENDING_REVIEW | APPROVED | REVISE_REQUESTED | ROLLED_BACK | ESCALATED`
