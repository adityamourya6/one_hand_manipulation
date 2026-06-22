# One Hand Manipulation — Project Status & Roadmap

> **Branch:** `feature/rich-environment` · **Package:** `one_hand_interface` · **ROS 2:** Jazzy · **Physics:** MuJoCo

---

## Phase 1: Core Foundations ✅ COMPLETE

**Goal:** Get a Franka Emika Panda robot running in MuJoCo with ROS 2 control.

| Item | Status | Details |
|------|--------|---------|
| Franka Panda URDF in MuJoCo | ✅ | `config/panda.xml` — full 7-DOF arm + gripper |
| `mujoco_ros2_control` bridge | ✅ | Locally compiled in Release mode to fix NVIDIA/ABI crashes |
| `robot_state_publisher` | ✅ | Publishes `/tf` and `/tf_static` from URDF |
| URDF xacro (`panda_mujoco.urdf.xacro`) | ✅ | World-anchored at `X=-0.25, Z=0.40` with `ros2_control` hardware interfaces |
| Arm controller (`fer_arm_controller`) | ✅ | `JointTrajectoryController` — 7 joints, position command interface |
| Gripper controller (`fer_gripper_controller`) | ✅ | `ForwardCommandController` — `fer_finger_joint1` with mimic on `fer_finger_joint2` |
| Launch file (`sim.launch.py`) | ✅ | Spawns: `robot_state_publisher`, `ros2_control_node`, 3 controllers, RViz |

**Key files:**
- [panda_mujoco.urdf.xacro](file:///home/mourya/one_hand_ws/src/one_hand_interface/urdf/panda_mujoco.urdf.xacro)
- [controllers.yaml](file:///home/mourya/one_hand_ws/src/one_hand_interface/config/controllers.yaml)
- [sim.launch.py](file:///home/mourya/one_hand_ws/src/one_hand_interface/launch/sim.launch.py)

---

## Phase 1.5: Professional Environment ✅ COMPLETE

**Goal:** Replace the basic table with a rich, realistic kitchen and high-fidelity objects.

| Item | Status | Details |
|------|--------|---------|
| Kitchen environment (robosuite) | ✅ | Full kitchen with counters (1.57m), cabinets, stove, microwave, oven, sink |
| Robot pedestal | ✅ | 1.25m tall (80% of counter height), black box at `X=-0.25` |
| Google Scanned Objects (5) | ✅ | `brisk_tea`, `frypan`, `donut`, `coffee`, `mug` — with textures |
| Robosuite Objects (3) | ✅ | `cereal`, `milk`, `bread` — with freejoints and explicit inertials |
| Object collision physics | ✅ | All objects have `contype=1`, `conaffinity=1`, and valid inertials |
| Scene file | ✅ | `kitchen_scene.xml` — clean, no test objects |
| Collision test scene | ✅ | `kitchen_scene_collision_test.xml` — on-demand via `collision_test:=true` |

**Available objects not yet in scene** (downloaded but not included in `kitchen_scene.xml`):
- `chef_knife`, `wire_basket` (Google Scanned Objects)
- `can`, `bottle`, `lemon`, `plate-with-hole`, `round-nut`, `square-nut`, `door` (robosuite)

**Key files:**
- [kitchen_scene.xml](file:///home/mourya/one_hand_ws/src/one_hand_interface/config/kitchen_scene.xml)
- [kitchen_scene_collision_test.xml](file:///home/mourya/one_hand_ws/src/one_hand_interface/config/kitchen_scene_collision_test.xml)

---

## Phase 1.5 Verification ✅ COMPLETE (11/11 tests passed)

| # | Test | Command | Result |
|---|------|---------|--------|
| 1 | Environment loads | `ros2 launch one_hand_interface sim.launch.py` | ✅ |
| 2 | Collision (10kg box hits arm) | `ros2 launch one_hand_interface sim.launch.py collision_test:=true` | ✅ |
| 3 | Gripper open | `ros2 topic pub --once /fer_gripper_controller/commands std_msgs/msg/Float64MultiArray "{data: [0.04]}"` | ✅ |
| 4 | Gripper close | `ros2 topic pub --once /fer_gripper_controller/commands std_msgs/msg/Float64MultiArray "{data: [0.0]}"` | ✅ |
| 5 | Joint 1 (base) | See implementation_plan.md for exact command | ✅ |
| 6 | Joint 2 (shoulder) | See implementation_plan.md | ✅ |
| 7 | Joint 3 (upper arm) | See implementation_plan.md | ✅ |
| 8 | Joint 4 (elbow) | See implementation_plan.md | ✅ |
| 9 | Joint 5 (forearm) | See implementation_plan.md | ✅ |
| 10 | Joint 6 (wrist bend) | See implementation_plan.md | ✅ |
| 11 | Joint 7 (wrist spin) | See implementation_plan.md | ✅ |
| 12 | Full coordinated pose | See implementation_plan.md | ✅ |
| 13 | Joint limit safety (3.5 rad → clamped at 2.8973) | See implementation_plan.md | ✅ |

---

## Phase 2: Classical Skeleton 🚧 IN PROGRESS

**Goal:** The arm can reliably plan and execute collision-free pick/place/pour motions in the kitchen scene, with support for swappable end-effectors.

### 2.1 RViz Integration ✅ COMPLETE
Synchronized MuJoCo physics with RViz visualization.

| Item | Status | Details |
|------|--------|---------|
| RViz config file | ✅ | `rviz/view_robot.rviz` — RobotModel + TF displays |
| RViz launch argument | ✅ | `rviz:=true` (default) or `rviz:=false` to skip |
| TF tree synchronization | ✅ | `/tf` and `/tf_static` flow correctly from `robot_state_publisher` → RViz |
| RobotModel display | ✅ | Full arm renders correctly, `Global Status: Ok` |

### 2.2 Motion Planning (MoveIt2) ❌ NOT STARTED
**Goal:** Programmatically command the arm to reach for objects using inverse kinematics.

#### What needs to be done:

**2.2.1 MoveIt2 Configuration Package**
Create a new ROS 2 package `one_hand_moveit_config` containing:
- **SRDF file (`fer.srdf`):** Semantic robot description defining planning groups (`fer_arm`, `fer_gripper`), end-effector links, and self-collision exclusion matrix
- **Kinematics solver (`kinematics.yaml`):** Configure KDL or TracIK solver for the `fer_arm` group
- **MoveIt controllers (`moveit_controllers.yaml`):** Map MoveIt's `FollowJointTrajectory` action to our `fer_arm_controller`
- **Planning pipeline (`ompl_planning.yaml`):** Configure OMPL planners (RRTConnect, PRM, etc.)

**2.2.2 Launch Integration**
- Add `move_group` node to `sim.launch.py` (or create a separate `moveit.launch.py`)
- Load SRDF, kinematics, and planner configs as parameters
- Update `view_robot.rviz` to include the `MotionPlanning` display plugin

**2.2.3 Programmatic Control**
- Create `reach_object.py` — a Python node that:
  1. Reads an object's known position (hardcoded or from TF)
  2. Sends a Cartesian pose goal to MoveIt
  3. MoveIt plans a collision-free trajectory
  4. Trajectory executes on the real MuJoCo arm via `fer_arm_controller`

### Plan of action:
1. Generate SRDF using MoveIt Setup Assistant or manually
2. Create the `one_hand_moveit_config` package with all YAML configs
3. Wire `move_group` into the launch file
4. Test interactive planning in RViz (drag end-effector → Plan & Execute)
5. Write `reach_object.py` for autonomous reaching
6. Verify the arm avoids counter collisions while reaching objects

---

## Phase 3: Zero-Shot Video-to-Goal Pipeline ❌ NOT STARTED

**Goal:** Extract object-centric goals from a human demonstration video and produce a robot trajectory that succeeds on a new instance of that task, leveraging RIGVid/OKAMI concepts.

---

## Known Issues & Crash Documentation

All MuJoCo crashes are documented in [mujoco_crash_postmortem.md](file:///home/mourya/one_hand_ws/src/one_hand_interface/docs/mujoco_crash_postmortem.md). Key rules learned:

| Rule | Reason |
|------|--------|
| Always compile `mujoco_ros2_control` in `Release` mode | ABI mismatch with ROS 2 causes `std::bad_alloc` crash |
| Keep file paths under 128 characters | MuJoCo silently truncates longer paths |
| Always pair `<freejoint/>` with explicit `<inertial>` | Geom-level mass is insufficient for dynamic bodies |
| No duplicate names across included XMLs | MuJoCo strict unique-name requirement |
| Object `<include>` tags go outside `<worldbody>` | Asset declarations must be at root `<mujoco>` level |

---

## File Structure Summary

```
src/one_hand_interface/
├── config/
│   ├── kitchen_scene.xml              # Main scene (clean)
│   ├── kitchen_scene_collision_test.xml # Scene with falling box
│   ├── controllers.yaml               # ros2_control config
│   ├── panda.xml                      # MuJoCo robot model
│   ├── k/                             # Kitchen assets (counters, oven, etc.)
│   ├── o/                             # Objects (brisk_tea, donut, frypan, etc.)
│   └── r/                             # Robosuite table arena assets
├── docs/
│   ├── implementation_plan.md         # Phase 1.5 plan + all test commands
│   ├── handoff_prompt.md              # Context for new agent sessions
│   └── mujoco_crash_postmortem.md     # All crash causes and fixes
├── launch/
│   └── sim.launch.py                  # Master launch (rviz, collision_test args)
├── rviz/
│   └── view_robot.rviz                # RViz display config
└── urdf/
    └── panda_mujoco.urdf.xacro        # Robot URDF with world anchor + ros2_control
```

---

## HVG Schema (For Completed Sub-Phases)
Per the Human Verification Gate rules, each completed sub-phase entry must log the gate decision in the following format:
```yaml
- Sub-phase: <name>
  Gate Command: PROCEED
  Timestamp: <iso8601>
  Open Postmortems at Approval: <none | list>
  Notes: <human's REVISE/OVERRIDE reasoning, if any>
```
