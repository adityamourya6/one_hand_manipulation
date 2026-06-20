# Phase 2 — Classical Skeleton: Motion Planning, Self-Model, Scripted Manipulation, Swappable End-Effector Groundwork

## Goal

The arm can reliably plan and execute collision-free pick/place/pour motions in your kitchen scene, with no learning involved yet, and the underlying model supports attaching/detaching different end-effectors as a first-class concept rather than something bolted on later. This is your safety net and your baseline — every later phase either builds on top of this or gets compared against it.

## Why this phase matters more than it looks like it should

It's tempting to treat this as "boring plumbing" on the way to the interesting AI work in Phase 3. Resist that. Three things make this phase load-bearing:

1. **Phase 3's retargeted trajectories need a feasibility check.** When the video-to-goal pipeline produces "move the end-effector here, then here," you need something that can answer "is that even reachable, and does it collide with anything" before you trust it. That something is MoveIt 2, built here.
2. **You need a known-working baseline to debug against.** Once Phase 3 starts producing trajectories from learned/extracted goals and something fails, you need to be able to ask "is this a perception/retargeting bug, or is the underlying execution broken?" Having a hand-scripted, deterministic pick/place that you know works lets you isolate that question instantly instead of debugging blind through the whole stack.
3. **Retrofitting tool-changing into a model that wasn't built for it is genuinely painful.** MoveIt's kinematic model (built from the URDF) is not designed to be restructured at runtime — adding "the end-effector can change mid-task" as an afterthought in Phase 5 or 6 would mean reworking decisions made here. Building the groundwork for it now, while you're already deep in URDF/MoveIt setup, is much cheaper than coming back to it later.

---

## 2a. MoveIt 2 Setup

### Use the official Franka packages as your base

Franka Robotics maintains `franka_ros2` (the `frankarobotics/franka_ros2` GitHub repo) directly, which includes `franka_fr3_moveit_config` — an FR3-specific MoveIt configuration — alongside `franka_description` (URDF/xacro + meshes), `franka_msgs`, `franka_hardware`, and example controllers. Critically for you right now: it supports launching MoveIt against fake/simulated hardware directly —

```
ros2 launch franka_fr3_moveit_config moveit.launch.py robot_ip:=dont-care use_fake_hardware:=true
```

This is worth using as your very first MoveIt validation step, before plugging in the MuJoCo bridge from Phase 1 — it isolates "does MoveIt + the FR3 description work at all" from "does my MuJoCo integration work," which are two separate things that can each independently break.

Once that's confirmed, swap the hardware interface to the MuJoCo-backed one from Phase 1 (`mujoco_ros2_control` or `multipanda_ros2`) instead of `use_fake_hardware`. This is exactly the moment the Phase 1 hardware-interface abstraction earns its keep — your MoveIt config, controllers, and launch structure shouldn't need to change much, only what's underneath.

### Generating your own config (only if needed)

If you end up needing a custom MoveIt config (e.g. a nonstandard end-effector, or a modified kinematic chain for your tool-changer setup), the MoveIt Setup Assistant is the standard tool — point it at your URDF/xacro, and it walks you through defining planning groups, end-effectors, and generating the Default Self-Collision Matrix (which pairs of links can skip collision checking because they're either always or never in contact — this matters for planning speed, since collision checking is typically the most computationally expensive part of planning, often accounting for the large majority of planning time).

### Validate basic planning

Minimum bar: plan-and-execute to a target end-effector pose via RViz2's MoveIt plugin, with collision checking active against at least one obstacle in the scene. Confirm it refuses (or replans around) a pose that would cause a collision — you want to see the safety net actually catch something, not just trust that it would.

---

## 2b. Kinematic Self-Model

This is largely "free" once 2a is working — don't build this from scratch.

### What MoveIt already gives you

- **Forward kinematics and Jacobians** are built directly into the `RobotState` class — given a joint configuration, you can query end-effector pose, and given a desired end-effector velocity, you can query the joint velocities needed (and vice versa). You won't be deriving these by hand; you're calling into `RobotState`.
- **Collision checking** lives in the `PlanningScene` (backed by FCL, the standard collision-checking library MoveIt uses). The `PlanningScene::isStateValid()` and `isPathValid()` calls are your "is this safe" oracle — exactly what you'll run every retargeted Phase 3 trajectory through before execution.
- **Joint limits and reachability** are derived from the URDF and enforced automatically during planning — you don't maintain a separate reachability model.

### Your actual job in this sub-phase

Mostly: wire up a `PlanningSceneMonitor` (the recommended way to keep a live, sensor-updated planning scene rather than a static one) and get comfortable calling `isStateValid()`/`isPathValid()` programmatically — ideally from Python via `pymoveit2`, which wraps forward/inverse kinematics, collision object management, and plan/execute calls in a friendlier interface than raw C++ MoveIt. Given you said you're not yet fluent in Python/ROS, lean on `pymoveit2` rather than writing raw MoveIt C++ — it'll get you to a working self-model check faster, and you can always drop to the C++ API later for anything it doesn't expose.

### Where the "self-awareness" framing from the original document lands

To be precise about scope, since "self-aware robot" is an evocative phrase that's worth grounding: what you're building here is exactly what the original document means by self-modeling — an accurate kinematic model (URDF + FK/Jacobians) plus reachability/collision checking. It is not anything resembling self-recognition or consciousness; the original doc is explicit that even the Lipson lab's "self-modeling" robotics research means engineering self-models (kinematic, occupancy, dynamics), not anything philosophical. Keep this framing in mind for any future investor-facing language — overclaiming "self-aware" risks credibility with anyone technical in the room.

### Optional stretch: occupancy self-model

A learned occupancy model (Lipson-lab style — the robot learns its own 3D shape/occupancy from observing itself move) is a legitimate stretch goal, but it's genuinely optional and not on the critical path. MoveIt's URDF-based collision model already gives you a correct, exact self-model for a simulated robot, since you have ground-truth geometry. The learned occupancy approach earns its value mainly when you *don't* have a trustworthy URDF — e.g. after physical damage, or on hardware whose exact geometry is uncertain. That's a real, interesting problem for later, on real hardware, not something sim-phase needs.

---

## 2c. Swappable End-Effector Groundwork

This sub-phase exists because of a specific use case: the arm finishes one operation (e.g. driving a nail) and needs to change to a different end-effector (e.g. a hammer) for the next step, triggered live, mid-task, by an upstream dispatcher (the LLM layer, much later). That requirement touches the kinematic model directly, so the groundwork belongs here, even though the actual orchestration logic comes much later (see the new Tool-Change Orchestration phase, after force control).

### The core constraint: MoveIt's kinematic chain isn't meant to change at runtime

This is worth understanding precisely, because it shapes the whole design: MoveIt's robot model is built from the URDF at load time, and the underlying URDF representation doesn't support modifying the kinematic chain on the fly — this is a known, longstanding limitation (tracked as an open feature request against MoveIt 2 itself), not something you're missing a flag for. You cannot simply "swap which link is the end-effector" as a live kinematic operation the way you might naively expect.

### The actual recommended pattern (this is what real tool-changing MoveIt deployments do)

The standard approach, used in both PickNik's official MoveIt Pro tooling and independent industrial integrations (e.g. users running real Zimmer-style tool-changers on multiple robots via MoveIt 2):

1. **Keep the robot description and tool descriptions in separate URDF/xacro files.** Your `robot.urdf` describes the Franka arm itself, with no gripper or tool-specific links or planning groups baked in. Each tool (gripper, hammer, screwdriver, etc.) gets its own small URDF file describing just that tool's geometry and TCP (tool center point) frame. This decoupling is what makes the rest of the pattern work — the robot model never has to "know" about a specific tool ahead of time.
2. **Treat tool attachment as a collision-object attach/detach operation, not a kinematic chain edit.** Rather than modifying the URDF's chain at runtime, you attach the tool's geometry to the robot's wrist link as an attached collision object — this is supported today, updates the planning scene's collision model correctly, and moves with the link it's attached to. Detaching removes it. This sidesteps the "URDF chain can't change at runtime" limitation entirely by not needing to change the chain — the tool just becomes additional geometry hanging off a fixed link.
3. **Maintain the actual TCP/actuation-frame offset yourself for planning targets.** Since the "end-effector" conceptually moves to wherever the currently-attached tool's working tip is, you need your own small layer that knows "if hammer is attached, the planning target pose needs to account for the hammer's TCP offset from the wrist; if gripper is attached, use the gripper's TCP offset instead." This is exactly the kind of function noted in independent research extending MoveIt for automatic tool-changing — a transform from the robot's wrist frame to the actuation frame of whichever end-effector is currently active. You're building a lightweight version of that same idea, not inventing something novel.
4. **The physical attach/detach mechanism is separate from the planning-side model update, and is MuJoCo/simulator-specific.** In MuJoCo specifically, the standard simulation-side approach is enabling/disabling a "weld" constraint at runtime — a weld constraint rigidly joins two bodies so they move together, which is how you simulate "the tool-changer has physically locked the tool to the wrist" versus "it's detached and sitting in its dock." This is a separate piece of engineering from the MoveIt-side collision attach/detach above — one is about physics simulation, the other is about planning/collision awareness — and both need to happen together for a tool swap to be coherent (don't let the planning scene think a tool is attached while MuJoCo's physics thinks it's still sitting in its rack, or vice versa).

### What to actually build in this phase (vs. later)

For Phase 2, the scope is narrow and deliberately stops short of full orchestration:

- Two separate, simple tool URDFs: a basic parallel gripper, and one "tool" stand-in (doesn't need to be a real hammer model yet — a simple geometric proxy is fine; realism is a later polish step).
- A wrist mount point on the Franka description that either tool can attach to.
- A manual (not yet LLM-triggered) script that: detaches whichever tool is currently attached (MoveIt collision object + MuJoCo weld disable), moves the arm to the other tool's fixed dock position, attaches the new tool (MoveIt collision object + MuJoCo weld enable), and verifies via `isStateValid()` that the resulting model is collision-consistent.
- The small TCP-offset lookup described above, so a planning target pose is correctly interpreted depending on which tool is currently active.

What's explicitly **not** in scope here: any LLM involvement, any behavior-tree-style failure handling/verification beyond a basic state check, and any real tool-changer hardware mechanics (ATI/Schunk-style automatic coupling) — those belong to the dedicated Tool-Change Orchestration phase once Phase 3 (so there's a real task to dispatch) and Phase 4 (so the post-swap task, like hammering, is an actual force-controlled primitive) exist to integrate with.

---

## 2d. Scripted Pick/Place/Pour Baseline

### Build this with no ML, on purpose

Hand-code a basic task sequence — pick up the cup, move above the bowl, tilt, return — using MoveIt's planning API directly (`pymoveit2`'s `move_to_pose`, collision object management for the cup/bowl, etc.). The goal is determinism: given the same scene, this should succeed the same way every time.

### This becomes your regression test

Once Phase 3 starts producing learned/retargeted trajectories, you'll want to answer "did this fail because the new pipeline is wrong, or because something fundamental broke" quickly. Keep this scripted baseline runnable as a standing test you can re-run after any change to the underlying stack (MuJoCo bridge updates, MoveIt config changes, end-effector swap logic, etc.) to confirm nothing upstream silently broke.

### What to actually script for your kitchen task list

Build one scripted sequence per task family (pour, wipe, stack, open) using only primitive-object scenes from Phase 1. Don't aim for elegance — a sequence of explicit waypoints and gripper open/close calls is fine. The value is in having ground truth, not in code quality.

---

## 2e. Perception Scaffolding (Light Touch)

### Why this belongs in Phase 2, not Phase 3

Camera setup and validation is infrastructure, not perception intelligence — get it right now, while you have a simple scene and no model complexity to confound debugging, rather than discovering a camera calibration bug while also debugging a segmentation model in Phase 3.

### What to validate

- Render RGB (and depth, if your MuJoCo camera setup supports it) from a camera placed sensibly relative to your kitchen scene — eye-level "looking at the tabletop" framing, similar to how a human demo video would be shot, since Phase 3 needs your sim camera and your demo videos to be at least roughly comparable viewpoints.
- Confirm camera intrinsics/extrinsics are correct by projecting a known 3D point (e.g. the cup's known position in the scene) into image space and checking it lands where you'd expect. This is a five-minute sanity check now that will save you hours of "is my 6D pose estimation wrong, or is my camera model wrong" confusion in Phase 3.
- If using depth: confirm depth values are in sensible units and aligned with the RGB frame.

---

## Risks and Watch-Outs

- **Don't let the optional occupancy self-model become a time sink.** It's interesting, it's not required, and MoveIt's URDF-based model already correctly serves every actual need in this phase.
- **Resist polishing the scripted baseline.** It exists to be a regression test, not a deliverable. Time spent making it elegant is time not spent on Phase 3.
- **Camera/perception scaffolding bugs are sneaky.** A wrong intrinsics value or a flipped axis won't necessarily crash anything — it'll just quietly produce wrong 6D poses later that look like a Phase 3 model problem. The sanity-check step above exists specifically to rule this out early.
- **If FR3's official MoveIt config and your MuJoCo bridge disagree on something** (link names, joint ordering, controller interface types), expect to spend real time reconciling them — this is a known friction point given the bridges in Phase 1 are community-maintained, not officially blessed by Franka Robotics itself.
- **Don't build the full tool-change orchestration here.** It's tempting, once you're in the URDF/MoveIt weeds, to keep going and wire up LLM-triggered swapping immediately. Resist — there's no real task or force-controlled primitive to swap *into* yet (those are Phases 3 and 4), so building the orchestration now means building it against fake placeholder tasks, which is wasted motion. Get the manual swap mechanism solid; let it sit until the rest of the stack catches up.
- **Keep the MoveIt-side attach/detach and the MuJoCo-side weld constraint in sync deliberately.** These are two independent systems that both need to agree on "is the tool attached right now." A bug where they disagree is exactly the kind of thing that silently produces nonsensical collision checks or physically wrong simulation — verify both sides explicitly after every swap during development, not just one.

## What "Done" Looks Like

- `ros2 launch franka_fr3_moveit_config moveit.launch.py ...` (or your adapted launch) works against your MuJoCo-backed hardware interface from Phase 1, not just `use_fake_hardware`.
- You can call `pymoveit2` (or raw MoveIt) to plan-and-execute to a target pose, with collision checking demonstrably active (it refuses or replans around an obstacle you placed deliberately).
- You have one scripted, deterministic, repeatable sequence per kitchen task family (pour, wipe, stack, open) on primitive objects, that you can re-run as a regression test.
- Your MuJoCo camera setup produces RGB(-D) frames with validated intrinsics/extrinsics, framed similarly to how a human demo video would be shot.
- You can explain clearly what your "self-model" actually is (URDF + FK/Jacobians + collision geometry) without overstating it.
- Two separate tool URDFs exist (gripper + one tool stand-in), and a manual script can detach one, dock, attach the other, and verify collision-consistency — with MoveIt's attached-object state and MuJoCo's weld-constraint state kept in agreement.
- You can explain why MoveIt's kinematic chain can't be modified at runtime, and why attaching tools as collision objects (rather than editing the chain) is the correct workaround rather than a hack.

---

## Scope Note: Deviations From `One-Hand_Robot.md`

Continuing the tracking started in the Phase 1 doc:

- **MuJoCo instead of Isaac Sim / Isaac ROS** — unchanged from Phase 1's note; still applies here for all simulation work in this phase.
- **Swappable end-effector groundwork is being built earlier and more incrementally than the source document implies.** The doc's Layer 5 (multi-tool execution) describes the finished capability — an automatic tool changer (ATI/Schunk-style) with a behavior tree orchestrating tool-change → primitive selection → verification — as a single architectural layer, without distinguishing "the kinematic/planning-side groundwork" from "the live orchestration logic." We've split that into two: the groundwork here in Phase 2 (because it touches the kinematic model and is cheaper to build alongside the rest of the URDF/MoveIt work), and a dedicated Tool-Change Orchestration phase later (after force control), once there are real tasks and real force-controlled primitives to swap between. This split is ours, not the doc's.
- **No real tool-changer hardware decision yet (ATI vs. Schunk vs. other).** The doc recommends specific hardware; we're deferring that choice until we're past sim-only work, since in sim the physical coupling mechanism is modeled abstractly (a MuJoCo weld constraint) rather than as a specific real device.
- **The 5-phase (now 6-phase, with Tool-Change Orchestration inserted) build order remains ours, not the doc's**, as noted in Phase 1.
