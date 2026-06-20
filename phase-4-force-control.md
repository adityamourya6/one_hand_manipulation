# Phase 4 — Force-Adaptive Control Layer

## Goal

Contact-rich tasks — tasks where the robot must regulate *force*, not just position (hammering, twisting open a jar, applying consistent pressure while wiping) — succeed in sim via impedance/admittance control and a force-primitive library, kept architecturally separate from the pure-motion policy work in Phase 3.

## Why this phase is different from everything before it

Be honest with yourself going in: this is the layer the source document calls "the genuine gap" — the one area where no existing zero-shot-from-video method works, and where even the best current research (ForceMimic/HybridIL, Reactive Diffusion Policy, FILIC) needs force-annotated demonstrations or sim-to-real RL, not a single video. There is no equivalent here to Phase 3's "adapt a published pipeline" path. This phase is closer to classical control engineering than to applying a research paper, which is actually good news in one sense — the math is well-understood and decades-old, not bleeding-edge — but it means the work is yours to implement carefully, not someone else's pipeline to adapt.

---

## 4a. Force and Torque Sensing in MuJoCo

### Two ways to get force data, and a real caveat about both

MuJoCo gives you force/torque information through two distinct mechanisms, and it's worth understanding both rather than picking one blindly:

- **`mj_contactForce`** — a direct query for the force/torque at a specific active contact, given a contact ID. This gives you raw, per-contact force data straight from the physics engine's constraint solver.
- **Dedicated `<force>`/`<torque>` sensor elements**, bound to a `<site>` in your MJCF — MuJoCo's sensor framework explicitly supports force-torque sensors as a built-in sensor type, alongside touch sensors, IMUs, and others, with results written into `mjData.sensordata` for you to read each step. This is generally the more natural fit for "I want a 6-axis F/T reading at my wrist," since you place a site where the real sensor would physically sit and read from it like a real device would report.

**The caveat worth knowing before you debug a confusing result:** force sensing in MuJoCo is a known source of real, documented confusion even among experienced users — one well-known GitHub issue shows a user's sensor reporting forces in the hundreds of thousands of units immediately upon contact, which is not physically meaningful and points to a setup/configuration issue (likely related to contact solver parameters or sensor site placement), not a MuJoCo bug. The practical lesson: validate your force readings against a known, simple physical scenario before trusting them in any control loop — for example, rest a known-mass object on a force sensor and confirm the reading is approximately mass × gravity, before using that same sensor inside an impedance controller. If your force readings look like nonsense, the contact solver's `solref`/`solimp` parameters (which govern contact stiffness/damping) are a likely place to look, not your control logic.

---

## 4b. Impedance Control — The Actual Implementation

### The core idea, precisely

Rather than commanding a position and accepting whatever force results (stiff position control), impedance control commands a *relationship* between position error and force — the robot behaves like a programmable spring-damper, applying torque proportional to how far it is from a desired pose, fused with measured external force. The standard Cartesian impedance control formulation, used directly in current contact-rich manipulation research (e.g. a 2025 peg-in-hole assembly paper using exactly this controller on a simulated Franka Panda) regulates the robot's motion in task space as:

**M(q)q̈ + C(q,q̇)q̇ + g(q) = J(q)ᵗF**

where **F** is the commanded Cartesian force/torque computed from the impedance law (desired stiffness/damping against the pose error), **J(q)** is the manipulator Jacobian mapping that Cartesian force into joint torques, and **M**, **C**, **g** are the standard mass/Coriolis/gravity terms of the robot's dynamics. This is not novel math you need to derive — it's the textbook robot dynamics equation, with the impedance law determining what **F** is at each timestep.

### What you actually need to build this, concretely

- **The Jacobian** — available directly from MuJoCo (`mj_jacSite` or equivalent) or from MoveIt's `RobotState` (Phase 2). You don't need to derive this by hand.
- **The mass matrix M(q)** — also directly queryable from MuJoCo (`mj_fullM`).
- **A reference implementation to build from, not from scratch.** Franka's own official community resources page lists a maintained set of "Differential IK & Operational Space Control" single-file MuJoCo examples specifically for the 7-DOF Panda, covering differential IK, nullspace control, and operational space control — operational space control and impedance control are closely related formulations, and this is a legitimate, current starting point rather than something to reinvent. Separately, there's an actively structured `franka-emika-panda-simulation` repository whose `osc_controller.py` explicitly exposes the Jacobian and mass-matrix retrieval functions needed for exactly this kind of controller, with a working simple impedance controller demo (`test_env.py`) included.
- **Your job is integration and tuning, not derivation.** Take a reference operational-space/impedance controller, adapt it to your specific Franka MuJoCo model and chosen end-effector (accounting for whatever's currently attached via Phase 2's swappable end-effector groundwork — the effective mass/inertia at the wrist changes depending on which tool is mounted, which matters for impedance behavior), and tune stiffness/damping gains against the force-sensing validation from 4a.

---

## 4c. Force-Primitive Library

### What this is and why it's hand-coded, on purpose

A small library of parameterized, reusable contact behaviors, built deliberately without learning — this is the doc's explicitly recommended fallback for tasks where zero-shot video transfer doesn't work, and it's the right call here, not a compromise. Build:

- **Guarded approach** — move toward a target until measured force exceeds a threshold, then stop. This is your basic "don't crash into things with force" primitive, useful any time the exact contact point isn't perfectly known (which, given Phase 3's perception pipeline, it often won't be).
- **Constant-force pressing** — maintain a target force against a surface while moving along a path (e.g. wiping with consistent pressure, rather than a fixed height that might hover above or crush into the surface depending on small errors).
- **Spiral/peg-in-hole search** — for insertion-style tasks, a small spiral search pattern combined with guarded force feedback, recovering from small position/orientation errors that a pure position-control approach would simply fail at.
- **Torque-thresholded fastening / twist** — apply rotational force up to a torque limit (e.g. opening a jar without crushing it, or — your stated example — driving a nail with a hammering motion under force control rather than blind position control).

### Parameterize by Phase 3's output

Each primitive should take parameters derived from the goal extracted in Phase 3 (target pose, approach direction, force/torque thresholds) rather than being hard-coded per-task. This is what lets "wipe this counter" and "wipe that counter" reuse the same constant-force-pressing primitive with different path parameters, rather than needing a new primitive per surface.

---

## 4d. (Stretch, Not Required for v1) Learned Force Adaptation

Once 4a-4c work reliably, a legitimate next step — but genuinely optional, and the most compute-hungry part of the entire project — is training a small residual policy on top of your hand-coded primitives (Reactive-Diffusion-Policy-style: a slow semantic/visual policy plus a fast force/tactile residual loop running at control rate). This is explicitly flagged in the source document as needing force-annotated demonstration data, which you don't have yet, and as the area best suited to cloud GPU rental rather than local hardware, consistent with your stated local-first-with-cloud-for-training policy from earlier. Don't start this until the hand-coded primitives are solid — there's no reason to add learned complexity on top of an unvalidated foundation.

## 4e. (Stretch, Real Future Scope) The MPC Spine — "Foundation Model as Brain, MPC as Spine"

### Why this is being added as explicit scope, not left implicit

The source document's actual recommendation for the control layer is more ambitious than 4a-4c alone: it calls for a Model Predictive Control spine — specifically Contact-Implicit MPC, MPPI, or Nonlinear MPC, running at 100 Hz to 1 kHz via solvers like `acados` or `TinyMPC` — handling safety, collision, and contact dynamics mathematically, with the higher-level foundation model/LLM layer treated as the "brain" issuing goals into that spine. Classical impedance control (4a-4c) is a genuinely good starting point and the right thing to get working first, but it isn't the same capability: impedance control gives you a compliant response to force after the fact, while a proper MPC spine optimizes the trajectory *ahead of time*, subject to collision, contact, and dynamics constraints, inside the solve itself. That's a real, meaningful gap between what 4a-4c delivers and what the source document actually envisions, and it's being named explicitly here rather than left as something the project quietly settled for.

### What "mathematically handling safety" actually means, concretely

A standard impedance controller has no built-in notion of an upcoming collision or contact event — it reacts to force once contact happens. A Contact-Implicit MPC formulation, by contrast, embeds contact physics directly into the predictive control problem, allowing the controller to autonomously plan contact events as part of the optimization rather than reacting to them once they occur — meaning the planned trajectory itself respects contact and collision constraints over the prediction horizon, not just the current instant. This is the actual mathematical safety guarantee the source document is pointing at, and it's a categorically different capability from anything in 4a-4c.

### The concrete tools, and why they're a credible starting point rather than a research risk

- **`acados`** is a modular, actively maintained software package for solving the nonlinear optimal control problems that MPC requires, repeatedly and fast — its own documentation lists production usage inside `openpilot` (the open-source driver-assistance system) for real-time lateral and longitudinal MPC, which is a meaningful existence proof that this isn't fragile research code; it's solving real, real-time control problems in deployed systems today. It offers Python, MATLAB, and Simulink interfaces that generate self-contained C code deployable on embedded platforms — directly relevant to eventually running this at the rates the doc specifies (100 Hz-1 kHz) rather than only in offline experimentation.
- **`TinyMPC`** is a high-speed, low-memory-footprint convex MPC solver from Carnegie Mellon's Robotic Exploration Lab (with a 2026 ICRA paper specifically on extending it with conic constraints), MIT-licensed, built in C/C++ specifically for resource-constrained robotics hardware. Critically for your setup: it already has a dedicated **`tinympc-mujoco`** interface repository — meaning the bridge into the exact simulation stack you've already built doesn't need to be invented from scratch, it already exists as a maintained starting point, the same pattern that made the Phase 1 ROS 2-MuJoCo bridge tractable.

### Where this sits relative to everything else in Phase 4

This is explicitly sequenced **after** 4a-4c, not instead of them, for the same reason 4d is sequenced after them: there's no reason to add a more sophisticated control layer on top of a foundation you haven't validated. Practically, the relationship between this stretch goal and 4a-4c's force-primitive library isn't "replace the primitives" — a mature MPC spine can still be the thing that executes toward goals the primitives express (e.g., "maintain this force while moving along this path" becomes a constraint inside the MPC's optimization, rather than a hand-coded feedback loop), so the primitive library's parameterization work isn't wasted even if this stretch goal is eventually pursued.

### What "done" looks like for this stretch goal, if pursued

- A working MPC formulation (start with Nonlinear MPC via `acados` before attempting full Contact-Implicit MPC, since the latter is a strictly harder problem) running on your Franka MuJoCo model, solved fast enough to be usable in a closed loop — even if not yet at the doc's full 100 Hz-1 kHz target initially.
- A side-by-side comparison against the 4a-4c impedance controller on at least one shared contact-rich task, so you have an honest, measured sense of what the MPC spine actually buys you in practice versus the classical approach, rather than assuming the more sophisticated method is automatically better for your specific tasks.
- A clear, demonstrated case where the MPC spine's foresight (planning around an upcoming contact event before it happens) produces a measurably different and better outcome than the reactive impedance controller — this is the concrete evidence that would justify the added complexity going forward.

---

## Risks and Watch-Outs

- **Validate force sensing against a known physical scenario before trusting it in any control loop.** Given the documented confusion even experienced users hit with MuJoCo's force sensors, skipping this step risks building an entire impedance controller on top of garbage force readings without realizing it.
- **Contact solver parameters (`solref`/`solimp`) are a likely culprit for weird force behavior**, not your control code — check these before assuming your impedance math is wrong.
- **Account for the currently-attached end-effector's effect on dynamics.** A hammer and a gripper don't have the same mass/inertia at the wrist; your impedance controller's behavior will shift accordingly, and this connects directly back to Phase 2's swappable end-effector groundwork — make sure whichever tool is "attached" in MuJoCo (weld constraint enabled) is reflected in the dynamics your controller is computing against.
- **Don't build the learned residual policy (4d) or the MPC spine (4e) until 4a-4c are solid.** Both are the most expensive, most optional parts of this phase, and adding either prematurely just compounds debugging difficulty.
- **This is the layer where "zero-shot" genuinely doesn't apply — don't try to force it to.** Resist the temptation to make this phase fit the same "works from one video" story as Phase 3. The source document is explicit and your own plan agrees: force-primitives parameterized by Phase 3's extracted goal is the correct architecture, not a consolation prize.
- **Tune incrementally on simple scenarios before complex ones.** Get guarded-approach working reliably on a flat, simple contact case before attempting peg-in-hole search or torque-thresholded fastening — these primitives compound in complexity, and debugging a spiral search with an untuned underlying impedance controller is much harder than debugging either piece alone.
- **If pursuing the MPC spine (4e), don't skip straight to Contact-Implicit MPC.** Nonlinear MPC via `acados` without contact-implicit terms is already a meaningfully harder control problem than impedance control; validate that first before adding contact-implicit complexity on top.

## What "Done" Looks Like

- You can read validated, sane force/torque readings from your MuJoCo Franka model at the wrist (or wherever your sensor site is placed), confirmed against a known simple physical test case.
- A working Cartesian impedance controller, adapted from a reference implementation (Franka's official community OSC examples or an equivalent), runs on your Franka MuJoCo model and demonstrably behaves like a compliant spring-damper rather than a stiff position controller — pushing on the end-effector during a hold should produce proportional, recoverable displacement, not either rigid resistance or unchecked drift.
- At least guarded-approach and constant-force-pressing primitives work reliably and are parameterized (not hard-coded per task).
- At least one genuinely contact-rich task from your kitchen list (or your stated hammering/fastening example) succeeds under force control, distinctly from a pure-position Phase 3 execution of the same task.
- You can explain why this phase couldn't use the same zero-shot-from-video approach as Phase 3, in your own words, grounded in what the source document calls the genuine gap.
- (If 4e is pursued) A working NMPC or Contact-Implicit MPC formulation runs on the Franka MuJoCo model via `acados` or `TinyMPC`, with an honest, measured comparison against the 4a-4c impedance controller on a shared task.

---

## Scope Note: Deviations From `One-Hand_Robot.md`

Continuing the tracking from Phases 1-3:

- **No sim-to-real RL (DextrAH-G/ClutterDexGrasp-style) attempted in this phase.** The source doc treats this as the most credible path to zero-shot-to-hardware contact skills; we're deferring it as a stretch goal (4d) behind the hand-coded primitive library, consistent with the doc's own staged recommendation that hand-coded primitives come before learned force adaptation.
- **The MPC spine ("Foundation Model as Brain, MPC as Spine") is now explicit future scope (4e), not abandoned.** An earlier version of this plan implicitly settled for classical impedance control as if it satisfied the source document's control-layer recommendation — on reflection, that was an unstated narrowing, not a reasoned substitution; impedance control and a true Contact-Implicit/Nonlinear MPC spine are genuinely different capabilities (reactive compliance versus constraint-aware predictive optimization), and the gap is now named and sequenced as real future work using the doc's own named tools (`acados`, `TinyMPC`) rather than left on the table.
- **MuJoCo instead of Isaac Sim / Isaac Lab** — unchanged from prior phases. The doc's sim-to-real RL examples (DextrAH-G, ClutterDexGrasp) were built in Isaac Gym/Isaac Lab; if we pursue 4d later, this is a place where the MuJoCo-vs-Isaac substitution could matter more than it has in earlier phases, since RL training infrastructure differs meaningfully between the two ecosystems. Worth revisiting explicitly if/when 4d becomes active work. (4e's MPC tooling, by contrast, has direct MuJoCo support via `tinympc-mujoco`, so this substitution concern doesn't apply there.)
- **No real F/T sensor hardware (Bota Systems FR3 kit, as the doc suggests) — simulated sensing only**, consistent with the project's sim-first phase. This will need real validation once hardware exists, since simulated and real force sensors behave differently in practice (noise characteristics, sampling rate, calibration drift).
- **The 6-phase build order (with Tool-Change Orchestration inserted after this phase) remains ours, not the doc's**, as noted previously.
