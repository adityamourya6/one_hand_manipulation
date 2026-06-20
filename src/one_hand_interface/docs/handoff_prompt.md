You are taking over from a previous agent session. 

**Context & Environment:**
- **Workspace:** `/home/mourya/one_hand_ws`
- **ROS 2 Version:** Jazzy
- **Current Branch:** `feature/rich-environment`
- **Core Package:** `one_hand_interface` (an `ament_python` package)

**What We Have Built So Far:**
1. **Phase 1 (Foundations):** We successfully translated a Franka Emika Panda robot into MuJoCo, bridged it with `ros2_control` via the `mujoco_ros2_control` plugin, and set up `robot_state_publisher`. 
2. **Phase 1.5 (Rich Environment):** We significantly upgraded the MuJoCo simulation environment (`config/mujoco_assets/kitchen_scene.xml`). We extracted a high-fidelity table from the Robosuite dataset and dynamically spawned 5 ultra-detailed Google Scanned Objects (donuts, iced tea, mug, frypan, etc.) onto the table. The gripper's `joint_trajectory_controller` is fully operational and verified via ROS 2 CLI.
3. **Phase 2 (Classical Skeleton):** We completed the visualization skeleton by modifying `launch/sim.launch.py` to auto-launch an RViz window perfectly synchronized with the MuJoCo physics engine. RViz correctly displays the `tf2` transforms.

**Next Steps (Phase 3):**
We are now ready to begin **Phase 3: Motion Planning**. The objective is to add kinematic planning capabilities (e.g. using MoveIt2 or custom inverse kinematics) so that we can programmatically command the Panda arm to reach for the detailed objects on the table.

Please scan the `src/one_hand_interface` directory to familiarize yourself with the launch files (`sim.launch.py`), URDFs (`panda_mujoco.urdf.xacro`), and controller configurations (`controllers.yaml`), and then present a plan for Phase 3!
