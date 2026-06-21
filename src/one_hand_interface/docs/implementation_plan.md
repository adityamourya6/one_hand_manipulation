# Phase 1.5: Professional Environment & Verification

As requested, we have created and checked out a new branch (`feature/rich-environment`) so we can safely experiment without risking our stable `main` branch. 

Before we move on to Phase 2 (RViz integration and skeletons), we must ensure Phase 1 is 100% complete. This involves swapping out our minimal table for a professional, confined environment and verifying that the robot's physics and gripper are fully functional.

## Open Questions

> [!TIP]
> **Environment Scale:** Massive datasets like `RoboCasa` (which feature 2,500+ kitchen scenes) can take hundreds of gigabytes and hours to download. I propose we extract a single, highly-detailed, confined "kitchen corner" or "laboratory workspace" from the open-source **`robosuite`** library, and augment it with 5-10 high-fidelity household objects (e.g., cans, cereal boxes, tools). This will give us the professional environment you want instantly. Are you okay with this targeted approach?

## Proposed Changes

### 1. Professional Environment Integration
Instead of building a simple table from scratch, we will leverage industry-standard open-source XMLs.
- **Download Assets:** We will download professional XML arenas (featuring walls, tables, and bins) and detailed manipulation objects from `robosuite`.
- **Refactor `kitchen_scene.xml`:** We will replace the basic boxes with these high-fidelity `<include>` models, ensuring the workspace is confined to force the robot to maneuver carefully.

### 2. Finalize the Gripper Control (Phase 1 Checklist)
Our arm is currently running, but the fingers are lifeless. We must finish the fundamental hardware mapping.
- **Update `controllers.yaml`:** Add a `forward_command_controller` or `joint_trajectory_controller` specifically mapped to `fer_finger_joint1` and `fer_finger_joint2`.
- **Update `sim.launch.py`:** Spawn this new controller alongside the arm.

### 3. Systematic Phase 1 Verification
We will run a series of tests to guarantee the physics and controllers are trustworthy before moving to Phase 2.
- **Collision Test:** We will spawn a heavy object mid-air and let it fall onto the robot to ensure rigid body collisions and mass properties are active.
- **Joint Limit Test:** We will command the arm to exceed its physical limits (`2.8973` radians) to verify that MuJoCo mathematically blocks the movement, ensuring our safety constraints work.
- **Actuation Test:** We will send a manual ROS command via the terminal to physically open and close the gripper.

## Verification Plan & Results

**✅ 1. Professional Environment Integration:**
- Verified the kitchen assets load successfully. The true height of the counters was calibrated to 1.57m, and the robot pedestal was resized to exactly 1.25m to match.
- All 8 high-fidelity objects (donut, pan, brisk_tea, etc.) successfully spawn and fall onto the table/stove.

**✅ 2. Collision & Mass Property Test:**
- **Method:** A 10kg red box (`heavy_collision_test`) is defined in a separate scene file `kitchen_scene_collision_test.xml`. It is spawned only when explicitly requested via the `collision_test:=true` launch argument — it does **not** appear in the normal simulation.
- **Command to trigger (on-demand):**
  ```bash
  ros2 launch one_hand_interface sim.launch.py collision_test:=true
  ```
  The red box will immediately begin falling from `Z=1.5m` and strike the robot arm, visually confirming rigid body collisions.
- **Result:** Objects exhibit correct gravity acceleration and cleanly collide with the arm and countertops without clipping or exploding. Inertial singularities (`mjMINVAL`) were successfully patched.
- **Crash Note:** First attempt crashed because `mass` was set inside `<geom>` instead of `<inertial>`. Fix: always pair `<freejoint/>` bodies with explicit `<inertial>` tags. Documented in `mujoco_crash_postmortem.md`.


**✅ 3. Gripper Actuation Test:**
- **Gripper OPEN:**
  ```bash
  ros2 topic pub --once /fer_gripper_controller/commands std_msgs/msg/Float64MultiArray "{data: [0.04]}"
  ```
- **Gripper CLOSE:**
  ```bash
  ros2 topic pub --once /fer_gripper_controller/commands std_msgs/msg/Float64MultiArray "{data: [0.0]}"
  ```
- **Result:** Fingers visually spread open to 4cm and snapped shut. ✅

**✅ 4. Individual Joint Tests (all 7 DOF verified one by one):**
- **Joint 1 — Base rotation:**
  ```bash
  ros2 topic pub --once /fer_arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{joint_names: ['fer_joint1','fer_joint2','fer_joint3','fer_joint4','fer_joint5','fer_joint6','fer_joint7'], points: [{positions: [1.5, 0.0, 0.0, -1.5, 0.0, 1.5, 0.0], time_from_start: {sec: 3}}]}"
  ```
- **Joint 2 — Shoulder forward:**
  ```bash
  ros2 topic pub --once /fer_arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{joint_names: ['fer_joint1','fer_joint2','fer_joint3','fer_joint4','fer_joint5','fer_joint6','fer_joint7'], points: [{positions: [0.0, -1.5, 0.0, -1.5, 0.0, 1.5, 0.0], time_from_start: {sec: 3}}]}"
  ```
- **Joint 3 — Upper arm roll:**
  ```bash
  ros2 topic pub --once /fer_arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{joint_names: ['fer_joint1','fer_joint2','fer_joint3','fer_joint4','fer_joint5','fer_joint6','fer_joint7'], points: [{positions: [0.0, 0.0, 1.5, -1.5, 0.0, 1.5, 0.0], time_from_start: {sec: 3}}]}"
  ```
- **Joint 4 — Elbow bend:**
  ```bash
  ros2 topic pub --once /fer_arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{joint_names: ['fer_joint1','fer_joint2','fer_joint3','fer_joint4','fer_joint5','fer_joint6','fer_joint7'], points: [{positions: [0.0, 0.0, 0.0, -2.5, 0.0, 1.5, 0.0], time_from_start: {sec: 3}}]}"
  ```
- **Joint 5 — Forearm roll:**
  ```bash
  ros2 topic pub --once /fer_arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{joint_names: ['fer_joint1','fer_joint2','fer_joint3','fer_joint4','fer_joint5','fer_joint6','fer_joint7'], points: [{positions: [0.0, 0.0, 0.0, -1.5, 1.5, 1.5, 0.0], time_from_start: {sec: 3}}]}"
  ```
- **Joint 6 — Wrist bend:**
  ```bash
  ros2 topic pub --once /fer_arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{joint_names: ['fer_joint1','fer_joint2','fer_joint3','fer_joint4','fer_joint5','fer_joint6','fer_joint7'], points: [{positions: [0.0, 0.0, 0.0, -1.5, 0.0, 3.0, 0.0], time_from_start: {sec: 3}}]}"
  ```
- **Joint 7 — Wrist spin:**
  ```bash
  ros2 topic pub --once /fer_arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{joint_names: ['fer_joint1','fer_joint2','fer_joint3','fer_joint4','fer_joint5','fer_joint6','fer_joint7'], points: [{positions: [0.0, 0.0, 0.0, -1.5, 0.0, 1.5, 2.0], time_from_start: {sec: 3}}]}"
  ```
- **Result:** All 7 joints moved independently and smoothly. ✅

**✅ 5. Full Coordinated Reach Pose (all joints simultaneously):**
  ```bash
  ros2 topic pub --once /fer_arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{joint_names: ['fer_joint1','fer_joint2','fer_joint3','fer_joint4','fer_joint5','fer_joint6','fer_joint7'], points: [{positions: [0.5, -0.5, 0.2, -2.0, 0.5, 1.8, 0.785], time_from_start: {sec: 3}}]}"
  ```
- **Result:** Arm transitioned smoothly to a realistic reach configuration targeting the countertop. ✅

**✅ 6. Joint Limit Safety Test (joint1 commanded to 3.5 rad, limit = 2.8973 rad):**
  ```bash
  ros2 topic pub --once /fer_arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{joint_names: ['fer_joint1','fer_joint2','fer_joint3','fer_joint4','fer_joint5','fer_joint6','fer_joint7'], points: [{positions: [3.5, 0.0, 0.0, -1.5, 0.0, 1.5, 0.0], time_from_start: {sec: 2}}]}"
  ```
- **Result:** MuJoCo hard-clamped joint1 at its physical limit of `2.8973 rad`. The over-commanded `3.5 rad` was mathematically blocked. Safety constraints confirmed. ✅

---

## Next Steps: Phase 3 (Motion Planning)
With the underlying kinematics and environment completely verified up to standard, we are now ready to implement **MoveIt2** to programmatically generate inverse kinematics (IK) paths to these objects.
