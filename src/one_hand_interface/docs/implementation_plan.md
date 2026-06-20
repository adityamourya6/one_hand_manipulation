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

## Verification Plan
1. Run `ros2 launch one_hand_interface sim.launch.py`.
2. Visually confirm the new professional, confined environment is loaded and textured correctly.
3. Observe the Collision Test (falling objects).
4. Run `ros2 topic pub` commands in the terminal to trigger the Joint Limit and Gripper Actuation tests.
