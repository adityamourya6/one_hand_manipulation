# Phase 1 — Foundations: ROS 2 + MuJoCo + the Bridge Between Them

## Goal

A ROS 2 node can command a simulated Franka arm's joints/end-effector through standard ROS 2 interfaces (topics/actions), with MuJoCo as the physics backend instead of real hardware. This is the load-bearing wall everything else in the project stands on — get this solid before writing any "smart" code.

## Why this phase exists before anything else

Phases 2–5 all assume two things are already true: you can describe and move the robot through ROS 2's standard abstractions, and the physics under that robot is trustworthy enough that success in sim means something. Phase 1 is where both of those get proven, cheaply, before any perception or learning complexity gets added on top.

---

## Track A: ROS 2 Fundamentals

### A1. Core concepts

Work through these in order, ideally with small throwaway exercises rather than reading-only:

- **Nodes** — a single-purpose process that does one job (e.g. "publish joint states").
- **Topics** — pub/sub channels for streaming data (joint states, camera images).
- **Services** — request/response, for one-off calls (e.g. "reset the simulation").
- **Actions** — long-running tasks with feedback and a result (e.g. "execute this trajectory," which is exactly what you'll use to command the arm).
- **Parameters** — runtime-configurable values per node.
- **Launch files** — Python-based files that start multiple nodes with the right configuration together.
- **Packages + colcon** — ROS 2's build system; you'll be building/rebuilding packages constantly, so get comfortable with `colcon build --symlink-install` early (the `--symlink-install` flag avoids re-copying Python files on every change, which saves real time during iteration).

**Recommended path:** the official ROS 2 tutorials (turtlesim-based exercises) — write a custom publisher/subscriber pair from scratch yourself rather than only running provided examples, since typing it out is what makes the pub/sub model actually click.

### A2. tf2 basics

`tf2` is ROS 2's system for tracking coordinate frames over time (e.g. "where is the end-effector relative to the camera relative to the table"). This matters more than it looks like it should right now — by Phase 3 you'll be converting a 6D object pose from a camera frame into the robot's base frame, and tf2 is the standard, correct way to do that instead of hand-rolling transform math.

Minimum bar for Phase 1: understand static vs. dynamic transforms, `tf2_ros` broadcasters/listeners, and how to visualize the transform tree in RViz2.

### A3. ros2_control architecture

This is conceptually the trickiest part of Phase 1 if you're new to ROS, so budget real time here — understand the *abstraction* on its own, separate from getting it working with MuJoCo specifically.

The architecture has four pieces that matter:

- **Controller Manager** — the central coordinator; loads/unloads controllers, runs the real-time control loop.
- **Hardware Interface** — an abstraction layer between controllers and "whatever the joints actually are" (a real motor driver, or in your case, MuJoCo). This is the piece you'll eventually swap from "simulated" to "real Franka" with minimal other changes — that's the entire point of the abstraction, and it's why getting this right now pays off directly at the real-hardware stage later.
- **Controllers** — things like the Joint Trajectory Controller, which take a desired trajectory and compute commands.
- **URDF `<ros2_control>` tags** — your robot description file declares what hardware interface and what command/state interfaces (position, velocity, effort) it exposes.

**Why this matters for you specifically:** this is the exact layer where your "ROS 2 now, real hardware later" goal gets satisfied. The hardware interface for MuJoCo and the hardware interface for a real Franka are different implementations of the *same* abstraction — your controllers, your MoveIt config, your higher-level code don't need to know or care which one is running underneath.

---

## Track B: MuJoCo Fundamentals

### B1. Install and load a Franka model

Use **MuJoCo Menagerie**'s Franka Emika Panda model (`google-deepmind/mujoco_menagerie`, `franka_emika_panda/`) as your starting point — it's a curated collection of well-designed MuJoCo models, maintained specifically so the community isn't fighting "bad" models that don't behave as expected, which matters since a sloppy MJCF can quietly poison every result downstream of it. Note Menagerie's model is the Panda specifically; if you want FR3 specifically there's a maintained separate model (`JeanElsner/panda_mujoco`) and Menagerie's README is the place to check current status of which variant they ship, since this evolves.

Install via the official MuJoCo Python bindings (`pip install mujoco`). Confirm the install by loading the Menagerie XML directly and stepping the simulation with no control input — just watch it sag under gravity correctly. This trivial test catches most installation/path problems early.

### B2. Core API fluency

Before touching ROS 2 integration, get comfortable purely in Python with:

- Stepping the simulation (`mj_step`).
- Reading joint state (`qpos`, `qvel`).
- Sending commands directly — position, velocity, or torque/effort, depending on actuator type defined in the MJCF.
- Reading contact forces (this becomes essential in Phase 4, but it's worth knowing the API exists now).
- Rendering a camera view (`mujoco.Renderer` or the built-in viewer) — this is your Phase 3 perception pipeline's eventual image source, so validate early that you can extract RGB (and ideally depth) frames, with sane camera intrinsics/extrinsics, since Phase 3's accuracy depends entirely on this being correct.

### B3. Build a minimal kitchen-ish scene

Start with primitive geometry, not realistic meshes — a box for a cup, a flattened cylinder for a bowl, a thin box for a sponge. The goal here is a scene you can iterate on fast, not a pretty one. Realistic meshes/textures are a polish step for much later, and pulling them in early just slows down iteration without adding learning value yet.

---

## Track A+B Convergence: The ROS 2 ↔ MuJoCo Bridge

This is the genuinely hard part of Phase 1, and it's worth understanding *why* it's hard before diving in: MuJoCo is not ROS-native the way Gazebo is. There's no single official, universally-adopted bridge — instead there are several actively maintained community efforts at different levels of generality. As of now, the realistic options are:

### Option 1 — `ros-controls/mujoco_ros2_control` (recommended starting point)

This is a `ros2_control` system interface that wraps MuJoCo as a hardware/system interface, built directly out of a 2024 Google Summer of Code project mentored by people from the MoveIt and ros2_control teams, with the explicit goal of providing another simulator option for ROS 2 and MoveIt since Gazebo "was unstable when contacts between objects existed." That last point is worth sitting with — this isn't just your assessment from earlier in the conversation, it's the stated motivation from the people who maintain ROS 2's own control stack for building a MuJoCo-specific path in the first place.

The project delivered both the ros2_control–MuJoCo interface itself and accompanying examples, implementing joint command and state interfaces for position, velocity, and effort control. It's the closest thing to an "official" path and is the one to start with, since it's positioned as a general-purpose interface rather than tied to one specific robot.

### Option 2 — `multipanda_ros2` (Franka-specific, more mature for this exact robot)

This is a more Franka-specific, actively developed project. It reimplements most of franka_ros's features for ROS 2 Humble specifically for the Panda/FR3, after Franka's own official franka_ros2 dropped Panda support, and integrates multi-arm MuJoCo simulation so the same controller code runs on both simulated and real robots. It even implements a generic ros2_control SystemInterface for simple single-arm setups, and notably has a **2026 arXiv paper** specifically documenting the sim-to-real bridging work (Škerlj et al., "Bridging the Sim-to-Real Gap with multipanda_ros2," arXiv:2602.02269) — meaning this exact problem you're about to solve has been written up as a research contribution this year, which is a useful sign this is a real, current pain point and not a solved/trivial one.

It's worth knowing this project's known rough edges going in: FrankaState currently implements only the basics (torque, joint position/velocity, end-effector pose, external force estimate), gravity compensation is approximated by reading MuJoCo's own computed gravity term rather than a separate model, joint position control specifically is flagged as potentially causing "bad motor behaviors" with torque or velocity control recommended instead, and the default MoveIt config has a dependency (warehouse_ros_mongo) that's deprecated and needs a workaround. None of these are dealbreakers, but go in expecting to read GitHub issues and patch small things rather than expecting a flawless `pip install`-style experience.

### Option 3 — `RobotControlStack` (skip for Phase 1, worth knowing about for later)

Worth flagging even though it's not the right choice right now: this is a ROS-free framework that unifies MuJoCo simulation and real robot control behind one Python API, natively supporting Franka FR3/Panda, UR5e, xArm7, and SO101, explicitly designed for training/deploying VLA models and RL agents — its entire pitch is that traditional middleware like ROS 2 and MoveIt are built for asynchronous distributed systems, which becomes a bottleneck for the synchronous execution patterns modern ML training wants. This is directly relevant to your Phase 3–4 work later (training/running VLA-style policies), but it deliberately skips ROS 2, which conflicts with your stated deployment goal for this phase. Worth bookmarking — you may end up using something like this *underneath* your ROS 2 layer for the actual policy inference loop later, while ROS 2 still owns hardware abstraction and orchestration. Not a Phase 1 concern; mentioned here so you recognize it later and don't think you're rediscovering it from scratch.

### Recommended approach for Phase 1

Start with `mujoco_ros2_control` to learn the general pattern with a simple setup, then move to `multipanda_ros2` once you specifically need Franka-shaped fidelity (gravity comp, external force estimate, Cartesian control) for Phase 2 onward. Don't try to write a bridge completely from scratch — both of these are real, maintained starting points, and the GSoC project specifically exists so people in your position don't have to.

### Validation step (Phase 1 "done" condition)

Send a joint trajectory goal via a standard ROS 2 action call (the same call you'd make against a real Franka driver) and confirm the simulated arm moves correctly in the MuJoCo viewer, with joint state feedback flowing back over the expected topics. If you can do this, the abstraction is proven and everything above it in later phases can be built without worrying about the plumbing underneath.

---

## Risks and Watch-Outs

- **The bridge is the highest-risk item in this phase.** If it stalls for multiple weeks with no forward progress, that's a legitimate signal to temporarily fall back to controlling MuJoCo directly from Python (no ROS 2 in the loop) for Phase 2–3 prototyping, and revisit the ROS 2 integration once you have an end-to-end pipeline worth wrapping. Don't let this single integration point block all downstream learning.
- **Contact stability was Gazebo's specific, documented weak point** that motivated `mujoco_ros2_control`'s creation in the first place — this is corroborating evidence for the MuJoCo-over-Gazebo call made earlier, not just an opinion.
- **Expect to patch small things.** Both bridge projects above have known rough edges (deprecated dependencies, partial feature coverage). This is normal for actively-developed robotics middleware, not a sign you picked wrong.
- **Don't over-invest in tf2 depth right now.** Understand it well enough to use it correctly in Phase 3; deep mastery isn't needed yet.

## What "Done" Looks Like

- You can explain, in your own words, what a hardware interface abstraction buys you and why it's the right place to draw the sim/real boundary.
- A ROS 2 action call moves the simulated Franka's joints in MuJoCo, with state feedback flowing back over standard topics.
- You have a minimal primitive-object kitchen scene in MuJoCo, with working camera rendering (RGB, ideally depth) at sane intrinsics/extrinsics.
- You understand enough `ros2_control` and `tf2` to read other people's robot launch files/configs without feeling lost.

---

## Scope Note: Deviations From `One-Hand_Robot.md`

This project plan follows the source document's overall architecture in spirit, not strictly line-for-line. Tracking the deltas explicitly here (and in each subsequent phase doc) so nothing silently falls off the radar as the project grows:

- **MuJoCo instead of Isaac Sim / Isaac ROS.** The source doc's recommended stack is built on Jetson AGX Thor + Isaac ROS (cuMotion, FoundationPose, nvblox). That assumes Omniverse-class GPU hardware we don't have (6GB VRAM laptop). MuJoCo is a deliberate substitution for better contact physics at low hardware cost — it means Isaac ROS's specific accelerated tools (cuMotion, FoundationPose, nvblox) aren't available to us yet and will need MuJoCo-compatible equivalents or a revisit once/if better GPU hardware enters the picture.
- **The ROS 2 ↔ MuJoCo bridge problem (this entire phase) doesn't really exist in the source doc.** It assumes the more ROS/Isaac-native Jetson ecosystem, so this integration work is something we're solving that the doc doesn't address.
- **No Jetson hardware, no edge-inference latency targets yet.** The doc's Section 5 (π0.5/GR00T/Gemini Robotics ms/Hz benchmarks on Thor) is currently not applicable — we're sim-only on a laptop. Revisit once real hardware is in play.
- **Layer 5 (multi-tool execution / automatic tool changer, dual end-effectors) is explicitly deferred.** Not yet planned for in any phase. Flagging it here so it's tracked rather than forgotten — it will need its own treatment when we reach Phase 5 (multi-tool execution / personality integration), including a decision on tool-changer hardware (ATI/Schunk-style, as the doc suggests) once we're past sim-only and into real hardware planning.
- **The 5-phase build order is ours, not the doc's.** The source document presents its 6 layers as a target architecture, not a prescribed build sequence (its own "staged" section does something similar but isn't identical to our phase breakdown). We sequenced phases based on what's lowest-risk to validate first for a 2-person, sim-first team.
