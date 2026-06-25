# MuJoCo Tool Mating Guide

This document outlines the standard procedure and critical rules for successfully mating custom tools and dexterous end effectors to the Franka robot arm using the universal adapter system in MuJoCo.

## 1. Adapter Coordinate Frame (Zero Offset Rule)
The root body of your custom tool (`tool_physical_[name]`) must act as the exact geometric origin where it mates with the robot. 
* **DO NOT** embed internal offsets: Previously, tools copied from the default Franka hand included an internal `pos="0 0 0.107"` offset. This causes the tool to sink into the robot's wrist when attached because the robot's mount point already provides the necessary offset from `link7`.
* The `franka_adapter_male` geometry block must be placed precisely at `pos="0 0 0"` within the tool's adapter base.

## 2. Tool Orientation (The 180° Flip)
By default, standard tools are modeled pointing "inward" (towards their base). To mount perfectly to the robot wrist and point outward towards the workspace, a 180-degree flip around the Y-axis must be applied (`quat="0 1 0 0"`).

**There are two valid ways to handle this depending on the native mesh:**
* **Standard Tools (Robotiq, Allegro, etc.):** The tool natively faces inward. You must apply `quat="0 1 0 0"` to the *entire tool root body* when attaching it to the robot. The adapter mesh inside the tool remains at `quat="1 0 0 0"`.
* **Natively Flipped Tools (e.g. 3-Finger Shadow Hand):** The tool natively faces outward. Do NOT flip the entire tool body. Instead, you must flip ONLY its adapter base (`<body name="adapter_male_base" pos="0 0 0" quat="0 1 0 0">`) so the mounting pegs point inward towards the robot wrist, while the hand points outward.

## 3. Resolving MuJoCo XML Naming Collisions
Complex dexterous hands (like the Allegro and Shadow hands) define dozens of custom `<material>` and `<default class="...">` physics attributes. When injecting these tools into the main robot XML, **MuJoCo will instantly crash** if a tool defines a class or material that already exists in the base robot (e.g., `<default class="visual">` or `<material name="black">`).
* **Solution:** Before merging the tool into the robot tree, deeply iterate through the tool's XML and dynamically rename any colliding classes or materials (e.g., prefix them with the tool name: `allegro_visual`, `shadow_black`).
* You must then update the `class` and `material` attributes on every single `<geom>` and `<joint>` inside the tool tree to match the new prefixed names.

## 4. Preserving Physics Constraints (Linkages & Tendons)
Many grippers are not just simple kinematic trees. Parallel-linkage grippers (like the Robotiq 2F-85) and complex hands rely on specialized physics constraints to prevent their fingers from falling apart under gravity.
When copying a tool into the robot XML, you **must** copy the following tags from the tool's root into the robot's root:
* `<equality>` (Connects parallel linkages)
* `<tendon>` (Drives underactuated fingers)
* `<contact>` (Excludes collision pairs)
* `<actuator>` (Motors)

## 5. MuJoCo Plugin Extensions
If an end effector relies on a software controller plugin (for example, the 3-finger Shadow Hand requires the `mujoco.pid` plugin), the `<extension>` tag must be copied from the tool XML to the robot XML. If the `<extension>` tag is missing, MuJoCo will fail to load the actuator elements and crash.

---

### Example Valid Tool Structure:
```xml
<mujoco model="example_tool">
  <compiler angle="radian"/>
  
  <!-- Unique defaults to avoid collisions -->
  <default>
    <default class="example_tool_visual">
      <geom type="mesh" contype="0" conaffinity="0" group="2"/>
    </default>
  </default>

  <!-- Required Constraints -->
  <equality> ... </equality>
  <tendon> ... </tendon>

  <worldbody>
    <!-- Root body with NO internal Z-offset -->
    <body name="tool_physical_example" childclass="example_tool_visual">
      
      <!-- Male Adapter at origin -->
      <body name="adapter_male_base" pos="0 0 0">
        <geom type="mesh" mesh="franka_adapter_male"/>
        <!-- Primitive geometries to enclose the base -->
      </body>

      <!-- Rest of the tool components -->
      <body name="example_tool_base" pos="0 0 -0.02">
         ...
      </body>
    </body>
  </worldbody>
</mujoco>
```
