# Post-Mortem: MuJoCo ROS 2 Control Crashing Issue

## The Problem
When attempting to launch the simulation using `ros2 launch one_hand_interface sim.launch.py`, the MuJoCo viewer would either:
1. Crash with a `glDeleteRenderbuffers` OpenGL segmentation fault.
2. Flash open for a split second and instantly auto-close with a C++ `std::bad_alloc` string memory corruption error.

## The Root Causes

### 1. The NVIDIA / OpenGL Bug (`glDeleteRenderbuffers`)
The default, pre-compiled binary version of `mujoco_ros2_control` (installed via `apt` in `/opt/ros/jazzy`) contains a known conflict with hybrid NVIDIA graphics pipelines on Linux. When the system attempts to offload rendering or manage the GLFW OpenGL context, the pre-compiled binary fails to handle the context switch properly and crashes the entire ROS 2 node. 

### 2. The ABI Mismatch Bug (`std::bad_alloc` / Auto-closing)
To bypass the NVIDIA bug, the repository was originally set up to compile `mujoco_ros2_control` directly from its raw C++ source code. However, during a workspace cleanup, the `build/` and `install/` directories were deleted. 

When the workspace was recompiled using a standard `colcon build`, the `mujoco_ros2_control` package was compiled without specific optimization flags. Because the rest of the ROS 2 Jazzy system is compiled in `Release` mode, compiling our local package in `Debug` mode created an **ABI (Application Binary Interface) mismatch**. This caused the C++ `std::string` memory allocator to corrupt the heap during initialization, instantly crashing the physics engine before the window could even be drawn.

## How We Overcame It

To achieve a perfectly stable, crash-free simulation window, we had to combine two specific fixes:

1. **Clean Slate:** We wiped the corrupted binaries by deleting the `build/` and `install/` directories entirely.
2. **Targeted Release Build:** We executed a highly-targeted `colcon build` command that accomplished three things:
   - Built only the necessary packages (skipping broken hardware packages like `franka_gripper` that were missing system dependencies).
   - Passed the `-DCMAKE_BUILD_TYPE=Release` flag to ensure our local C++ compiler perfectly matched the memory allocator ABI used by the core ROS 2 system.
   - Passed the `--allow-overriding mujoco_ros2_control` flag to explicitly tell ROS 2 to ignore the buggy NVIDIA-incompatible binary in `/opt/ros/jazzy` and use our locally compiled, optimized version instead.

### The Winning Command
```bash
rm -rf build/ install/ && \
colcon build \
  --cmake-args -DCMAKE_BUILD_TYPE=Release \
  --packages-select franka_description mujoco_ros2_control mujoco_ros2_control_plugins one_hand_interface \
  --allow-overriding mujoco_ros2_control mujoco_ros2_control_plugins
```

By ensuring the local package was built with strict `Release` optimizations, we successfully bypassed both the OpenGL driver conflict and the C++ memory corruption, restoring the simulation to perfect working order!

## Phase 1.5/2 Issues: The Rich Environment Crash
When attempting to load the `robosuite` high-fidelity rich environment, MuJoCo exhibited the exact same `glDeleteRenderbuffers` crash. However, the root causes were entirely different XML parser bugs:

### 1. XML Schema Violation (Duplicate Assets & Invalid Scope)
The `robosuite` objects (`prefixed.xml`) were mistakenly included *inside* the `<worldbody>` tag of the main `kitchen_scene.xml`. In MuJoCo, object files contain `<asset>` declarations (textures, materials), which **must** be declared globally at the root `<mujoco>` level. Additionally, the new `robosuite_assets/table_arena.xml` and the old `kitchen_scene.xml` both defined a material named `table_mat`, violating MuJoCo's strict unique-name requirement.

**Fix:** Cleaned up the legacy assets from `kitchen_scene.xml` and moved all `<include>` tags for high-fidelity objects out of the `<worldbody>` and into the global scope.

### 2. The 128-Character File Path Truncation Bug
The most insidious crash was caused by the deeply nested Google Scanned Object folders (e.g., `Brisk_Iced_Tea_Lemon_12_12_fl_oz_355_ml_cans_144_fl_oz_426_lt`). 
Because the URDF was explicitly resolving the absolute system path (`/home/mourya/one_hand_ws/install/...`) to pass into `mujoco_ros2_control`, the total filepath lengths exceeded 150+ characters. 
MuJoCo's internal path parser has a hardcoded legacy limit of 128 characters. It silently truncated the string mid-word (e.g., `/home/mourya/one_hand_ws/instal`), resulting in an "Unrecognized File" error which immediately threw the OpenGL crash.

**Fix:** 
1. Renamed all object folders to their shortest descriptive names (e.g., `brisk_tea`, `frypan`).
2. Updated the URDF to use a **relative path** (`src/one_hand_interface/config/...`) instead of the absolute `install` path, ensuring all paths remain well under 100 characters.

## Phase 1.5/2 Issues: Object Importing Crashes
When importing the standard `robosuite` objects (cereal, milk, bread) directly into the `kitchen_scene.xml`, the simulation crashed with three distinct new parsing errors:

### 1. Duplicate Site Names
Because all the `robosuite` objects contained identical site tags (e.g., `name="bottom_site"` and `name="top_site"`) intended for tracking, including multiple objects in the same global namespace caused a duplicate name collision.
**Fix:** Removed the unnecessary `site` tags from the XML configurations since they were not needed for basic rendering.

### 2. mjMINVAL Mass and Inertia Error
MuJoCo logged the error: `Error: mass and inertia of moving bodies must be larger than mjMINVAL`. The `robosuite` objects relied strictly on `density` tags instead of explicitly defining mass, and since we turned them into physics-enabled objects, MuJoCo calculated their dynamic mass to be 0, causing physics solver failures.
**Fix:** Explicitly defined `<inertial mass="..." pos="0 0 0" diaginertia="0.001 0.001 0.001"/>` for all three imported objects.

### 3. Nested Freejoint Error
MuJoCo logged the error: `Error: free joint can only be used on top level`. The `robosuite` object XMLs had their main body tag wrapped inside an extra unnamed `<body>` tag. A `<freejoint/>` mathematically defines an object's relationship to the root world coordinate system and cannot be buried inside sub-bodies.
**Fix:** Stripped out the wrapper `<body>` tags so that the object body and its freejoint became direct descendants of the `<worldbody>`.

## Crash: Verification Heavy Box Missing Explicit Inertia
**Date:** 2026-06-21  
**Trigger:** Added a `<freejoint/>` body (`heavy_collision_test`) for collision verification testing without explicit inertia.

### Root Cause
MuJoCo requires that all **moving bodies** (bodies with joints, including freejoints) have valid mass and inertia values greater than `mjMINVAL` (~1e-14). When only `mass` is set inside a `<geom>` tag (not inside `<inertial>`), MuJoCo cannot auto-compute the inertia tensor for a `freejoint` body and throws:

```
Error: mass and inertia of moving bodies must be larger than mjMINVAL
failed to load the model
```

The process then exits with signal `-11` (SIGSEGV) as the controller manager tries to access a null physics world pointer.

### Fix
Moved mass declaration out of the `<geom>` and added an explicit `<inertial>` tag:
```xml
<body name="heavy_collision_test" pos="-0.25 0.0 1.5">
    <freejoint/>
    <inertial mass="10.0" pos="0 0 0" diaginertia="0.1 0.1 0.1"/>
    <geom type="box" size="0.15 0.15 0.15" rgba="0.9 0.1 0.1 1" contype="1" conaffinity="1"/>
</body>
```

### Key Rule
**Always** pair `<freejoint/>` with an explicit `<inertial>` tag. Never rely on geom-level mass for dynamically simulated bodies.
