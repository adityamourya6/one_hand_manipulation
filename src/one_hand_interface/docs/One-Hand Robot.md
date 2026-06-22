# Foundation Model as Brain, MPC as Spine

### A Comparative Analysis and Ranked Research Roadmap for a Jetson-Deployable, Self-Aware, Contact-Rich Collaborative Anthropomorphic Arm

_Markdown deliverable — save as `cobot_mpc_brain_spine_roadmap.md`. This document is the complete, self-contained report; copy the entire content below into a `.md` file to download._

---

## TL;DR

- **The proposed two-tier split — a learned cognitive layer for perception/language/planning plus a pure-mathematics MPC spine for real-time motion and contact control — is the highest-probability architecture for a Jetson-Nano-constrained, cross-embodiment, contact-rich cobot.** It wins precisely where end-to-end VLAs fail: hard safety/constraint guarantees, kHz contact reactivity, sample efficiency, debuggability, and the ability to run the safety-critical loop on a CPU at milliwatt cost while the heavy model runs slowly or off-board.
- **The Jetson Nano constraint eliminates most foundation models but barely touches MPC.** NVIDIA's official Isaac-GR00T hardware spec requires "1 GPU with 16 GB+ VRAM" for inference, so GR00T N1.5/N1.6 will not load on an 8 GB Orin Nano; only heavily compressed sub-0.5B VLAs (SmolVLA, NanoVLA, SwiftVLA, LiteVLA-Edge) fit, running at single-digit-to-~20 Hz. Meanwhile acados-class NMPC runs at >150 Hz on embedded ARM, TinyMPC runs MPC on a 168 MHz microcontroller, and GPU MPPI achieves a 17.63 ms median solve on the Orin Nano. The realistic design is **low-rate cognition (1–10 Hz) + high-rate MPC (100 Hz–1 kHz)**.
- **Discard the dream of one monolithic end-to-end policy doing everything on a Nano.** Keep: contact-implicit / hybrid force-position MPC on a rigid-body model identified by classical system-ID, with CBF safety filters, a self-model for reach/self-collision/damage, and a small distilled VLA or cloud VLM for goals. The single biggest technical risk is contact/friction model mismatch on unknown materials — mitigate with online residual learning (GP/NN) and tube/robust MPC, not with a bigger neural policy.

---

## Key Findings

1. **MPC is computationally cheap and embedded-proven; foundation models are not.** TinyMPC (Nguyen et al., _TinyMPC: Model-Predictive Control on Resource-Constrained Microcontrollers_, ICRA 2024, arXiv:2310.16985) runs convex MPC on ARM Cortex-M microcontrollers with "a maximum speed-up of 8x over OSQP" (its conic extension, arXiv:2403.18149, reaches "up to 20.4× faster execution" vs OSQP); GPU MPPI achieved "a 17.63 ms median computation time versus 31.02 ms for CPU-only execution" on a Jetson Orin Nano (Applied Sciences 2025, 15(16):9114); cuRobo "enables processing 512 parallel trajectories with 64 timesteps each at 500Hz" on a Jetson Orin NX (arXiv:2508.04146). By contrast, GR00T N1.5 needs ≥16 GB VRAM (NVIDIA Isaac-GR00T spec) and π0 (PaliGemma-3B) achieves only ~19 Hz even on a Blackwell Jetson Thor.
    
2. **Contact-rich tasks (drilling, screwing, insertion) are exactly where the MPC literature is strongest and where end-to-end policies are weakest.** Contact-implicit MPC (CIMPC), hybrid force-position MPC, and multi-contact feedback MPC running in real time on 7-DOF arms are all demonstrated. ForceVLA2 (Yang Li et al., arXiv:2603.15169) reports that adding explicit hybrid force-position control to a VLA delivers success "outperforming pi0 and pi0.5 by 48.0% and 35.0%, respectively, across the 5 tasks" — evidence that even the VLA community concedes raw vision-language policies under-handle force.
    
3. **Self-modeling has two viable, complementary branches.** Classical system-ID (inertial-parameter ID via QR/least-squares on Fourier excitation trajectories; Stribeck+viscous friction ID) gives the deterministic rigid-body model MPC needs and is cheap. Lipson-lab visual/learned self-models give task-agnostic morphology learning, damage detection, and recovery. The pragmatic path: classical ID for the MPC plant model + online learned residual (GP/NN) for the unmodeled part + a self-model layer for reachability/self-collision/damage adaptation.
    
4. **On a Jetson Nano the only realistic architecture is a rate-split hierarchy.** Cognition (VLM/VLA or cloud) at 1–10 Hz sets goals/sub-goals/keypoints; MPC at 100 Hz–1 kHz on CPU (acados) or GPU (MPPI/cuRobo) handles motion + contact + safety. This is the same "System 2 / System 1" or "brain/cerebellum" split now converging across the field (π0.5, Helix, hierarchical-VLA studies) — but with the low level being _optimal control_ rather than a learned policy, which is what buys the safety guarantees and the tiny compute footprint.
    

---

## Details

### 1. MPC Deep-Dive for an Anthropomorphic Arm

**The core OCP.** Every formulation below solves, at each control tick, a finite-horizon optimal control problem (OCP): minimize a running cost ℓ(x,u) summed over the horizon plus a terminal cost φ(x_N), subject to the dynamics x_{k+1}=f(x_k,u_k), path constraints (joint position/velocity/torque limits, force limits), and safety constraints, then apply the first control and re-solve (receding horizon). The state x is typically joint positions/velocities (and contact forces for contact-aware variants); the control u is joint torques or accelerations. This is the math the entire low level rests on.

**Formulations and where each fits the cobot:**

|Formulation|What it adds|Best for in this build|Solver / library|Demonstrated capability|
|---|---|---|---|---|
|Joint-space / whole-body NMPC|Full rigid-body dynamics, joint limits, self-collision|Reaching, free-space motion, posture optimization|acados, Crocoddyl, OCS2, Aligator + Pinocchio|7-DOF arm real-time; GPU whole-body (MPCGPU) scales to kHz with up to 512 knot points on a Kuka iiwa|
|Task / operational-space MPC|Cartesian tracking via Jacobian|End-effector path following for drawing, drilling approach|acados, TSID|30–90 Hz typical|
|Contact-implicit MPC (CIMPC)|Contact as complementarity constraints; no pre-scheduled mode sequence|Non-prehensile manipulation, sorting, tool-contact onset|Posa-lab LCP/ADMM (C3, Consensus Complementarity), DDP variants (Kim et al. 2025)|Bi-manual ~100 Hz (Kurtz 2023); 24-DOF humanoid 50 Hz; Franka non-prehensile real-time (arXiv:2505.13350)|
|Hybrid force-position MPC|Splits axes into force-controlled and position-controlled|Drilling (axial force + lateral position), screwing, peg-in-hole|acados + FT sensor|Robot-assisted bone-drilling path deviation cut 56.6% (PMC10458884); peg-in-hole insertion|
|Impedance / admittance-aware MPC (MPFC)|Regulates dynamic stiffness/damping at contact|Compliant insertion, human handover, safe contact|Model Predictive Force Control on KUKA LWR|KUKA LWR IV Fast Research Interface runs at 1 kHz in joint-impedance mode (arXiv:1506.09084)|
|Robust / tube MPC|Bounds disturbances; nominal + ancillary feedback keeps state in a "tube"|Unexpected resistance, unknown material stiffness|Convex collision-aware tube MPC (arXiv:2508.21677), smooth-MPC (arXiv:2103.09693)|Real-time on 6-DOF industrial arm with collision-avoidance guarantees|
|Nonlinear MPC + RTI/SQP|Real-time iteration: one SQP step per tick|The general workhorse for the arm|acados (SQP-RTI, HPIPM, BLASFEO)|sub-ms–few-ms per solve on workstation; >150 Hz on embedded ARM|
|Learned-residual / Neural-MPC|Nominal model + learned correction|Adapting to unmodeled friction/material|Real-time Neural-MPC (UZH, arXiv:2203.07747), GP-MPC|NN residual integrated with optimization times <3 ms; GP-MPC >100 Hz|
|MPPI (sampling-based)|Derivative-free, handles non-smooth contact, GPU-parallel|Contact-rich / non-smooth tasks where gradients are poor|cuRobo reactive, Hydrax (JAX/MJX), MPPI-Generic, Isaac Gym MPPI|17.63 ms median on Orin Nano GPU; 0.629 ms for 512 samples (MPPI-Generic on Orin Nano)|

**Constraint handling and safety.** Hard constraints (joint/torque limits) enter the QP/NLP directly; soft constraints use slack variables (acados rigorously exploits slack structure). For safety, **Control Barrier Functions (CBFs)** are the key tool: they convert collision/joint-limit/singularity avoidance into constraints guaranteeing forward-invariance of a safe set. Stanford's Operational Space CBF (OSCBF, stanfordasl.github.io/oscbf) "scales to hundreds of simultaneous constraints while retaining real-time control rates, ensuring collision avoidance, singularity prevention, and workspace containment"; the MIT Humanoid CBF-WBC work (arXiv:2207.00692) uses CBFs with full dynamics for self-collision avoidance; CBF-MPC hybrids (flexible active-safety MPC with optimized decay rates, 2025 IEEE RA-L) embed CBFs as MPC decision variables. CBFs are computationally light — ideal for a Nano.

**Dynamics and contact models.** Rigid-body dynamics and analytical derivatives come from **Pinocchio** (one of the fastest RBD libraries, stack-of-tasks/pinocchio). Contact is modeled either via complementarity (LCP, in CIMPC) or via compliant/smoothed contact (to enable gradients). Friction uses Coulomb+viscous at minimum; Stribeck models capture low-velocity/stick-slip and temperature effects — shown to improve torque tracking by up to 70.37% on an Indy7 cobot (MDPI Sensors 22(24):9708).

**Real-time solvers (the embedded story):**

- **acados** — C-based, BLASFEO+HPIPM backend, SQP-RTI, CasADi front-end; the de-facto choice for embedded NMPC; ms-range solves; runs on Jetson/Raspberry Pi (arXiv:1910.13753).
- **OSQP / ProxQP / qpOASES** — QP solvers for linear/convex-MPC and CBF-filter layers; OSQP code-generates dependency-free C.
- **TinyMPC** — ADMM, division-free, static memory; targets microcontrollers; 8× over OSQP on Cortex-M7; runs on a 168 MHz STM32F405 Crazyflie (arXiv:2310.16985).
- **Crocoddyl / OCS2 / Aligator** — DDP/SLQ/SQP optimal control under contact, used for whole-body MPC; all build on Pinocchio.
- **MPPI on GPU** — cuRobo (NVIDIA), Hydrax (JAX/MJX), MPPI-Generic (CUDA); leverages the Nano's GPU.
- **cuMotion / cuRobo** — GPU collision-free trajectory optimization (L-BFGS + particle seeds), ships Python wheels for Jetson Orin and Thor; integrates into MoveIt 2 and uses nvblox SDFs for obstacle avoidance.

### 2. Self-Modeling for MPC

**Classical system identification (recommended as the backbone).** The arm's rigid-body dynamic parameters (link masses, inertias, COMs) are identified by exciting the robot along optimized Fourier-series trajectories and solving a linear least-squares problem on the minimal/base-parameter set (extracted via QR decomposition of the regressor). Kinematic calibration corrects geometric offsets. Friction is identified separately (Coulomb+viscous, optionally Stribeck with temperature dependence). This yields the deterministic plant model MPC needs, is cheap to compute, and transfers the _method_ across embodiments (the _parameters_ are per-robot).

**Learned dynamics models (recommended as a residual, not a replacement).** Neural ODEs, Gaussian Processes, and learned residual dynamics capture what rigid-body ID misses (cable forces, backlash, contact compliance, payload changes). The dominant, most embedded-friendly pattern is **nominal model + learned residual**: GP-MPC ("Cautious MPC," arXiv:1705.10702) propagates residual uncertainty into chance constraints; Real-time Neural-MPC (arXiv:2203.07747) integrates NN residuals with optimization times below 3 ms. GPs excel in the low-data regime and give uncertainty estimates (useful for tube sizing); NNs scale to more data but cost more. Online/adaptive updating (recursive sparse GP, set-membership) lets the model track wear, temperature, and new tools.

**Lipson-style self-models (recommended for the self-awareness/damage layer).** The Lipson-lab lineage — Bongard et al. (resilient machines through continuous self-modeling, _Science_ 2006), task-agnostic self-modeling (Kwiatkowski & Lipson, _Sci. Robotics_ 2019), full-body visual self-modeling (Chen et al., _Sci. Robotics_ 2022, arXiv:2111.06389), and egocentric visual self-modeling (Hu, Chen & Lipson, _npj Robotics_ 2025, arXiv:2207.03386) — learns a robot's morphology/kinematics from a single camera via self-supervised "motor babbling," then uses it for planning, **damage detection (predicted vs. observed motion divergence), and recovery**, with generalization validated "across robots with different configurations." For this cobot, a self-model integrates with MPC three ways: (a) supplies a learned signed-distance/reachability field for **self-collision avoidance** as MPC/CBF constraints; (b) provides **reachability** checks for the planner; (c) enables **damage adaptation** — when the self-model detects a changed body (bent link, weak joint), it triggers re-identification and the MPC re-plans against the updated model. This grounds the "self-awareness of reach, joint limits, kinematics, dynamics" requirement.

### 3. Architecture Comparison

|Criterion|Proposed: Learned cognition + MPC spine|End-to-end VLA / IL|Hybrid VLA + learned low-level (RoboDual, π0.5, diffusion+force residual)|Classical TAMP + planning|
|---|---|---|---|---|
|Real-time contact adaptation|**Strong** — MPC re-solves at 100 Hz–1 kHz with force feedback|Weak–moderate — open-loop chunks go stale; force often absent|Moderate — improves with force residual (ForceVLA2 +35–48%) but still policy-limited|Weak — replanning is slow, not reactive|
|Safety / constraint guarantees|**Strong** — hard constraints + CBFs, provable forward-invariance|**Weak** — no formal guarantees|Weak–moderate|Moderate (checks at plan time, not runtime)|
|Sample efficiency / data needs|**Strong** — model-based, little/no task data|**Weak** — data-hungry (demos/teleop)|Weak–moderate|Strong (no learning) but heavy engineering|
|Generalization (novel objects/tasks)|Moderate — cognition generalizes; control is task-agnostic|**Strong** within training distribution; brittle OOD|Strong|Weak — brittle to unmodeled situations|
|Interpretability / debuggability|**Strong** — every cost/constraint inspectable|**Weak** — black box|Weak–moderate|**Strong**|
|Compute cost|**Low** at control layer; cognition tunable|**High**|High|Moderate–high|
|Jetson-Nano deployability|**Strong** — MPC on CPU/GPU; distilled VLA or cloud for cognition|**Weak** — most don't fit or are too slow|Weak|Moderate|

**Verdict:** The proposed architecture is the only one simultaneously safe, contact-reactive, data-efficient, and Nano-deployable. Its weakness is open-world generalization at the cognitive layer — which is exactly what you delegate to a (possibly off-board or distilled) foundation model, and which need not run at control rate.

### 4. Two Ranked Lenses

Scoring is 0–10 (probability of working well under the stated lens). Methods span the prior-report set plus the new MPC-centric methods.

#### Lens A — Cross-System / Cross-Embodiment Generalization

|Rank|Method / Component|Score|Justification|
|---|---|---|---|
|1|NMPC w/ Pinocchio RBD model (acados/Crocoddyl)|9.5|Model-based; re-target to any arm by swapping URDF + re-ID. Method transfers cleanly.|
|2|CBF safety filters (OSCBF)|9.3|Geometry/kinematics-driven; embodiment-agnostic formulation.|
|3|Classical system-ID pipeline|9.0|Same procedure for any manipulator; only parameters change.|
|4|MPPI / sampling MPC (cuRobo, Hydrax)|8.8|Needs only a model/simulator of the new robot; no policy retraining.|
|5|Hybrid force-position MPC|8.5|Force/position decomposition is general across arms with FT sensing.|
|6|Lipson visual self-model|8.3|Demonstrated to generalize across morphologies; self-supervised.|
|7|Contact-implicit MPC|8.0|General formulation; tuning/solver robustness varies by platform.|
|8|Learned-residual MPC (GP/NN)|7.5|Nominal model transfers; residual must be re-learned per robot.|
|9|Gemini Robotics / GR00T / π0.5 (large VLAs)|7.0|Built for cross-embodiment but tied to training data (GR00T↔Fourier GR1, π0↔ALOHA).|
|10|SmolVLA / NanoVLA / SwiftVLA (small VLAs)|6.0|Inherit some generalization but weaker; need per-embodiment fine-tuning.|
|11|DextrAH-G / ClutterDexGrasp (sim-to-real RL)|5.5|Strong within trained hand/arm; re-training per embodiment costly.|
|12|OKAMI-style human-video retargeting|5.5|Retargeting concept generalizes; execution remains embodiment-specific.|
|13|End-to-end imitation (vanilla diffusion policy)|4.5|Overfits to the demonstration embodiment.|
|14|Classical TAMP|4.0|Heavy per-robot/per-domain engineering.|

#### Lens B — Optimization to Run on Jetson Nano (HARD CONSTRAINT)

_Nano context: Orin Nano 8 GB, 1024-core Ampere GPU, ~40 TOPS dense INT8 (the "67 TOPS" Super rating is a sparse/marketing figure), 8 GB LPDDR5 unified at 68 GB/s, ~5 GB usable VRAM after OS. Bottleneck for single-stream inference is memory bandwidth, not TOPS._

|Rank|Method / Component|Score|Justification|
|---|---|---|---|
|1|TinyMPC|9.8|Runs on 168 MHz MCUs; trivially fits Nano CPU; kHz capable.|
|2|acados NMPC (CPU)|9.5|ms-range solves on ARM (>150 Hz on Jetson TX2-class); fits CPU, frees GPU.|
|3|CBF QP filters (OSQP/ProxQP)|9.5|Tiny QPs; sub-ms; negligible footprint.|
|4|Classical system-ID|9.3|Offline/low-rate; negligible online cost.|
|5|cuRobo / cuMotion|8.8|Ships Jetson Orin wheels; 512 traj @ 500 Hz on Orin NX 8 GB; uses GPU.|
|6|MPPI on GPU (Hydrax/MPPI-Generic)|8.5|17.63 ms median on Orin Nano GPU; 0.629 ms for 512 samples (MPPI-Generic).|
|7|Learned-residual MPC (sparse GP / small NN)|7.5|Feasible if residual net is small; watch GPU/CPU contention.|
|8|Lipson self-model (small CNN)|7.0|Inference cheap; babbling/training can be offline.|
|9|LiteVLA-Edge (256M, 4-bit)|6.5|~150 ms / ~6.6 Hz on AGX Orin; fits Nano memory; cognition-rate only.|
|10|NanoVLA / SwiftVLA (sub-0.5B)|6.0|Fit 8 GB; SwiftVLA reports 18× faster / 12× less memory than π0; cognition-rate.|
|11|SmolVLA (~0.5B)|5.5|Fits with fp16; designed for edge but slow; action chunking needed.|
|12|DextrAH-G / sim-to-real RL student|5.0|Distilled student nets can run; full stack heavy.|
|13|π0 / π0.5 (3B class)|2.5|Borderline-to-no fit on 8 GB; ~19 Hz even on Thor.|
|14|GR00T N1.5 / Gemini Robotics on-device|1.5|GR00T spec requires ≥16 GB VRAM — does not load on Orin Nano.|

**Quantization note (enables the small-VLA tier):** Saliency-Aware Quantized Imitation Learning (arXiv:2505.15304) measured OpenVLA on a Jetson AGX Orin GPU at BF16 = 15.2 GB / 955 ms, INT8 = 7.9 GB / 574 ms (1.6×), INT4 = 4.0 GB / 375 ms (2.5×). INT4 is what brings a ~7B-class model into ~4 GB. **Caveat:** quantization only reduces latency/memory when truly low-precision kernels are used; naïve INT8 in a framework that dispatches FP32 kernels can give no speedup at all.

### 5. Recommended Research Path (Staged Milestones)

**Stage 0 — Plant model & infrastructure (weeks 0–6).** Build URDF; run classical system-ID (Fourier excitation → base-parameter LS) for inertial params; identify Coulomb+viscous(+Stribeck) friction. Stand up Pinocchio + acados on the Nano. _Success threshold: identified model predicts joint torques within ~10–15% RMS on validation trajectories; acados free-space NMPC tracking at ≥100 Hz on Nano CPU._

**Stage 1 — Safe free-space motion (weeks 6–12).** Add CBF self-collision + joint-limit + workspace constraints; integrate cuMotion/cuRobo for global collision-free seeds, acados for tracking. _Success: zero self-collisions over 1,000 randomized reach goals; planning <100 ms; reach success ≥95% in cluttered scenes._

**Stage 2 — Contact-rich control (weeks 12–24).** Add FT sensing; implement hybrid force-position MPC for drilling/screwing/insertion; add tube/robust MPC for unknown stiffness. _Success: peg-in-hole ≥90%; drilling axial-force regulation within target band; recover from unexpected resistance without tripping safety stops._

**Stage 3 — Self-model & adaptation (weeks 24–36).** Add online residual learning (sparse GP or small NN) feeding the MPC; add a Lipson-style self-model for reachability and damage detection. _Success: residual learning cuts tracking error ≥30% on a novel payload/material; self-model detects an induced "damage" (e.g., added link mass) and triggers re-ID within one task cycle._

**Stage 4 — Cognitive layer & integration (weeks 36–52).** Add the high-level layer: a distilled/quantized small VLA (SmolVLA/NanoVLA) or a cloud VLM producing goals/keypoints at 1–10 Hz; learn-from-single-human-video (OKAMI-style retargeting) yielding goals/keypoints that **parameterize the MPC cost**, not raw torques. Add a lightweight personality/mood layer (CPU or off-board). Implement automatic dual-effector/tool-changing as discrete task-graph transitions. _Success: one-shot video → executed task for ≥3 of {drill, screw, sort, draw} with cognition off-loadable; latency budget met (cognition ≤10 Hz, control ≥100 Hz)._

**Benchmarks that would change the plan:** if a sub-0.5B VLA reaches ≥30 Hz closed-loop on the Nano _and_ handles force, reconsider giving it more low-level authority. If contact-model mismatch cannot be driven below task-failure thresholds even with residual learning, escalate to CIMPC or richer tactile sensing rather than a bigger policy.

### 6. Explicit Discard List

- **Monolithic end-to-end VLA doing low-level control on the Nano.** GR00T won't load (≥16 GB spec); π0 too slow (~19 Hz on Thor, slower on Orin). Dead end for the control loop.
- **Running any 3B+ foundation model unquantized on the Nano.** Memory-infeasible in 8 GB.
- **Replacing the dynamics model entirely with a learned NN / Neural-ODE.** Costlier, less interpretable, no safety guarantees, more data — use residual learning instead.
- **Pure classical TAMP for contact-rich reactive tasks.** Too slow to react to contact; keep TAMP (if at all) only for high-level discrete sequencing.
- **Vision-only imitation for force-critical tasks** (drilling/screwing). Force-blind policies fail — ForceVLA2's 35–48% gains over π0/π0.5 by adding force prove the point.
- **Sim-to-real RL as the primary controller** for a cross-embodiment, resource-constrained build — heavy to retrain per embodiment; reserve distilled RL students for narrow grasping sub-skills only.
- **High-rate cloud dependence for the safety loop.** Never put the contact/safety loop behind a network; cloud is acceptable only for low-rate cognition.

---

## Recommendations

1. **Commit to the brain/spine split now.** Make MPC (acados on CPU + optional MPPI/cuRobo on GPU) the authoritative low-level controller with CBF safety filters; treat all learned cognition as advisory goal-setters that parameterize MPC costs/constraints, never as direct torque sources.
2. **Invest first in system-ID + force-position MPC**, because contact-model fidelity is the dominant risk for drilling/screwing/insertion.
3. **Keep the cognitive layer swappable and off-loadable.** Target a distilled small VLA for on-device autonomy but design so a cloud VLM can substitute; the system must degrade gracefully (continue safe MPC execution) when cognition is slow or unavailable.
4. **Add online residual learning + tube MPC** for unknown materials rather than scaling up the neural policy.
5. **Use the self-model for reach/self-collision/damage**, integrated as constraints/triggers, not as a standalone controller.

---

## Caveats / Honest Gaps

- **No published acados/HPIPM solve-time for a 6–7-DOF manipulator specifically on a Jetson Orin Nano was located.** The closest verified embedded datapoint is ACADO/qpOASES NMPC running ">150 Hz" with a ~25 ms first-iteration time on a Jetson TX2 (arXiv:2109.12886); a separately reported 6.6 ms acados+HPIPM figure could not be independently confirmed. Bench this on the target hardware early — manipulator NMPC with contact may be slower than free-flight quadrotor NMPC.
- **Several edge-VLA papers (LiteVLA-Edge, VLA-Perf, vla.cpp, and some NanoVLA speedup claims) are very recent / 2026-dated**; their exact Hz/latency numbers should be re-verified before being treated as established fact. The GR00T ≥16 GB requirement, cuRobo 500 Hz / Orin NX, MPPI 17.63 ms / Orin Nano, TinyMPC 8× / Cortex-M, ForceVLA2 35–48%, and OpenVLA INT4 figures are from verifiable primary sources.
- **The "67 TOPS" Orin Nano Super figure is a sparse/marketing rating;** dense INT8 is ~40 TOPS and the real single-stream bottleneck is the 68 GB/s memory bandwidth.
- **CIMPC robustness on real hardware remains finicky** (complementarity ill-conditioning); treat it as a Stage-2+ research item, not a guaranteed primitive.
- **Cross-embodiment "method transfer" is not "parameter transfer."** The MPC/ID/CBF _methods_ transfer; each new robot still needs its own identification and tuning.

---

## Citations (papers, models, solvers, hardware)

**MPC formulations & contact**

- Venkatesh, Bianchini, Aydinoglu, Yang, Posa. _Approximating Global Contact-Implicit MPC via Sampling and Local Complementarity._ arXiv:2505.13350.
- Kim, Kang, Kim, Hong, Park. _Contact-Implicit MPC: Controlling Diverse Quadruped Motions Without Pre-Planned Contact Modes._ arXiv:2312.08961 (IJRR 2025).
- _Fast Contact-Implicit Model-Predictive Control._ arXiv:2107.05616.
- _Online Multi-Contact Feedback MPC for Interactive Robotic Tasks._ arXiv:2403.08302.
- _Complementarity-Free Multi-Contact Modeling and Optimization for Dexterous Manipulation._ arXiv:2408.07855.
- _Implementation of Nonlinear Model Predictive Path-Following Control for an Industrial Robot_ (KUKA LWR IV, 1 kHz). arXiv:1506.09084.
- _Force-Position Hybrid Compensation Control for Path Deviation in Robot-Assisted Bone Drilling._ PMC10458884.
- ForceVLA2: Li et al. _Unleashing Hybrid Force-Position Control with Force Awareness for Contact-Rich Manipulation._ arXiv:2603.15169.
- _Real-Time Predictive Control for Precision Machining_ (acados/HPIPM MPCC). arXiv:1908.10609.

**Robust / tube / learned-residual MPC**

- _A Robust Tube-Based Smooth-MPC for Robot Manipulator Planning._ arXiv:2103.09693.
- _Robust Convex MPC with Collision Avoidance Guarantees for Robot Manipulators._ arXiv:2508.21677.
- _Differentiable Robust MPC._ RSS 2020 (roboticsproceedings.org/rss20/p003).
- Salzmann et al. _Real-time Neural MPC: Deep Learning MPC._ arXiv:2203.07747 (RA-L 2023).
- _Cautious Model Predictive Control using Gaussian Process Regression._ arXiv:1705.10702.
- _Gaussian Processes for Dynamics Learning in MPC._ arXiv:2502.02310.

**Safety / CBF**

- Khazoom et al. _Humanoid Self-Collision Avoidance Using Whole-Body Control with CBFs_ (MIT Humanoid). arXiv:2207.00692.
- Stanford ASL. _Operational Space Control Barrier Functions (OSCBF)._ stanfordasl.github.io/oscbf.
- _Flexible Active Safety Motion Control: A CBF-Guided MPC Approach._ IEEE RA-L 2025.

**Solvers / libraries**

- acados: _acados — a modular open-source framework for fast embedded optimal control._ arXiv:1910.13753; docs.acados.org; github.com/acados/acados (BLASFEO, HPIPM).
- TinyMPC: Nguyen, Schoedel, Alavilli, Plancher, Manchester. arXiv:2310.16985 (ICRA 2024); Conic-TinyMPC arXiv:2403.18149; tinympc.org.
- Pinocchio: github.com/stack-of-tasks/pinocchio (Carpentier et al., SII 2019).
- Crocoddyl: Mastalli et al., ICRA 2020; loco-3d/crocoddyl.
- OCS2: leggedrobotics/ocs2. Aligator: Simple-Robotics/aligator (arXiv:2405.09197).
- MPPI: _Sampling-Based MPC Leveraging Parallelizable Physics Simulations_ arXiv:2307.09105; Hydrax (vincekurtz/hydrax); MPPI-Generic arXiv:2409.07563; Feedback-MPPI arXiv:2506.14855.
- cuRobo/cuMotion: github.com/nvidia-isaac/cumotion; nvidia-isaac-ros.github.io; _Industrial Robot Motion Planning with GPUs_ arXiv:2508.04146; VaPr arXiv:2310.07854.

**Self-modeling & system-ID**

- Bongard, Zykov, Lipson. _Resilient Machines Through Continuous Self-Modeling._ Science 2006.
- Kwiatkowski & Lipson. _Task-Agnostic Self-Modeling Machines._ Sci. Robotics 2019.
- Chen, Kwiatkowski, Vondrick, Lipson. _Full-Body Visual Self-Modeling of Robot Morphologies._ arXiv:2111.06389 (Sci. Robotics 2022).
- Hu, Chen, Lipson. _Egocentric Visual Self-Modeling._ arXiv:2207.03386 (npj Robotics 2025).
- _A Two-Step Method for Dynamic Parameter Identification of Indy7 Collaborative Robot Manipulator._ MDPI Sensors 22(24):9708.
- _Dynamic Parameter Identification of Modular Robot Manipulators (GA + LS)._ Soft Computing 2024.

**VLA / foundation models & edge deployment**

- SmolVLA: Shukor et al. arXiv:2506.01844.
- NanoVLA: arXiv:2510.25122 (OpenReview yeHBrNVZoV).
- SwiftVLA: arXiv:2512.00903.
- π0 / π0.5: Physical Intelligence; π0.5 _A VLA with Open-World Generalization._
- GR00T N1/N1.5: NVIDIA, _GR00T N1: An Open Foundation Model for Generalist Humanoid Robots_; Isaac-GR00T GitHub (≥16 GB VRAM inference spec).
- Gemini Robotics On-Device: Google DeepMind (deepmind.google/models/gemini-robotics).
- DextrAH-G: arXiv:2407.02274. ClutterDexGrasp: arXiv:2506.14317.
- _Saliency-Aware Quantized Imitation Learning_ (OpenVLA INT8/INT4 on AGX Orin). arXiv:2505.15304.
- Hierarchical VLA studies: arXiv:2606.10267; VLA-OS arXiv:2506.17561; _Survey on Efficient VLA Models_ arXiv:2510.24795.

**Hardware**

- NVIDIA Jetson Orin Nano (Super) ~40 TOPS dense / 67 TOPS sparse, 8 GB LPDDR5 @ 68 GB/s; AGX Orin 275 TOPS / 64 GB; AGX Thor ~2070 FP4 TFLOPS / 128 GB (NVIDIA; Forecr; Acrosser comparisons).
- MPPI vs NMPC on Jetson Orin Nano: _Comparison of NMPC and GPU-Parallelized MPPI for Real-Time UAV Control on Embedded Hardware._ Applied Sciences 2025, 15(16):9114.
- acados NMPC on Jetson TX2 (>150 Hz): arXiv:2109.12886.
  
  
  
  
#Previous  
# Building a Self-Aware, Zero-Shot Collaborative Robot on Jetson: State of the Art and Recommended Architecture (June 2026)

## TL;DR

- **No single model delivers everything you want today.** The optimal build is a _layered hybrid stack_: a VLM/embodied-reasoning planner that parses a human demo video into an object-centric goal (OKAMI/RIGVid/ReKep-style), a 6D-pose-and-motion-retargeting layer with a kinematic self-model, a learned VLA or diffusion policy for general manipulation, and a dedicated force-adaptive controller (impedance/admittance + force-primitive library) for the contact-rich work (drilling/screwing), all orchestrated on a Jetson AGX Thor with a separate local LLM personality layer.
- **"Zero-shot from a single human video" is real but bounded:** object-centric / video-to-pose methods achieve genuine zero-shot task transfer for pick/place/pour/wipe — OKAMI's object-aware retargeting reaches **71.7%** average task success (and **79.2%** when its rollouts train a closed-loop policy, with no teleoperation), and RIGVid reaches **85.0%** on everyday tasks. But they degrade sharply on contact-rich, force-dominated tasks like drilling and screwing, which still need force-aware policies, residual RL, or sim-to-real. **"Zero-shot to new embodiments"** is best served by π0.5, GR00T N1.5/N1.7, and Gemini Robotics 1.5's Motion Transfer.
- **Recommended concrete stack:** Franka Research 3 (1 kHz joint-torque control) or UR5e + 6-axis F/T sensor as the arm; ATI/Schunk automatic tool changer with two end-effectors (tool holder + adaptive gripper); GelSight-class tactile + 6-axis F/T sensing; Jetson AGX Thor (Blackwell GPU, 128 GB memory, up to 2070 FP4 TFLOPS, 75–130 W) running π0.5 (openpi, TensorRT FP8+NVFP4) or GR00T N1.7 for manipulation, Isaac ROS (cuMotion + FoundationPose + nvblox) for planning/perception, and a quantized Llama-class LLM + NVIDIA Riva for the personality/voice layer.

## Key Findings

### 1. The landscape splits into four families

1. **VLA foundation models** (π0/π0.5, GR00T N1.5/N1.7, Gemini Robotics / On-Device, Figure Helix, OpenVLA, SmolVLA, RT-2, Octo). Best for cross-embodiment generalization and language-conditioned multi-task control; weak at single-video task transfer and at native force control.
2. **Learning-from-human-video / one-shot imitation** (OKAMI, RIGVid, Vid2Robot, EgoMimic, UniSkill, ScrewMimic, MimicFunc, HRT1, ReKep/VoxPoser). Best for sense-(a) zero-shot task transfer from a single demonstration; mostly vision/pose-centric and contact-poor.
3. **Force-adaptive / visuotactile manipulation** (ForceMimic/HybridIL, Reactive Diffusion Policy, FoAR, FILIC, TacDiffusion, ManiFeel, VISK; sim-to-real RL like DextrAH-G, ClutterDexGrasp). Essential for drilling/screwing/insertion; data-hungry, narrow generalization.
4. **Classical + hybrid TAMP/perception** (Isaac ROS cuMotion, FoundationPose, nvblox, MoveIt 2, behavior trees) + LLM/VLM planners (SayCan, Code-as-Policies, VoxPoser, ReKep). The reliable "skeleton" that makes the learned components safe and deployable.

### 2. Zero-shot from a single human video works — for the right tasks

- **OKAMI** (UT-Austin RPL, CoRL 2024, arXiv:2410.11792) generates a manipulation plan from a _single_ RGB-D human video using open-world vision (Grounded-SAM segmentation + Cutie tracking, SLAHMR/HaMeR hand reconstruction, CoTracker keypoints), then does object-aware retargeting via inverse kinematics. Its object-aware retargeting "achieves 71.7% task success rates averaged across all tasks," and OKAMI rollouts train closed-loop visuomotor policies to "an average success rate of 79.2%" — with no labor-intensive teleoperation.
- **RIGVid** (Patel/Mohan/Lazebnik, UIUC, arXiv:2507.00990) imitates _generated_ videos: a video diffusion model (Kling v1.6) produces a demonstration from a language prompt + scene image, a VLM (GPT o1) filters bad generations, FoundationPose extracts a 6D object-pose trajectory, retargeted embodiment-agnostically with backtracking when pose deviates >3 cm/20°. RIGVid "achieves a success rate of 85.0%," versus baselines Track2Act (7.5%), AVDC (32.5%), 4D-DPM (35.0%), and Gen2Act (67.5%).
- **ReKep / VoxPoser** (Stanford, arXiv:2409.01652) turn a VLM's output into relational keypoint constraints / 3D value maps solved in closed loop at real-time rates with no task-specific training. "ReKep (Auto) achieved a 44.3% overall success rate across tasks, significantly outperforming VoxPoser's 10.0%. The human-annotated ReKep baseline achieved 68.6%," evaluated on 7 multi-stage tasks (Pour Tea, Recycle Can, Stow Book, Tape Box, Fold Garment, Pack Shoes, Collaborative Folding).
- The common thread: these methods extract _object-centric goals/affordances_ and assume a graspable/rigid-transport model. They are weak exactly where your spec is hardest — **time-varying force application** (drilling, screwing, fastening).

### 3. Contact-rich force control is the genuine gap

- **ForceMimic / HybridIL** (SJTU, ICRA 2025, arXiv:2410.07554) shows both the problem and a fix: pure-vision imitation fails on peeling/contact tasks; adding force-centric demonstration capture + hybrid force-position control "increas[ed] the success rates by 54.5% relatively compared to state-of-the-art pure-vision-based imitation learning" on zucchini peeling (HybridIL: 100% motion success / 85% peel continuity vs 80%/55% for vision-only diffusion policy). But it needs force-annotated demos — not zero-shot.
- **Reactive Diffusion Policy** (arXiv:2503.02881), **FoAR**, **FILIC** (dual-loop impedance torque control), and **TacDiffusion** all confirm the same architecture: a _slow_ semantic/visual policy (low Hz) plus a _fast_ force/tactile residual loop (control-rate) for insertion/assembly/screwing.
- **Sim-to-real RL** (DextrAH-G geometric fabrics, arXiv:2407.02274; ClutterDexGrasp with 3D Diffusion Policy, arXiv:2506.14317; "Closing the Reality Gap," arXiv:2601.02778 — zero-shot sim-to-real force-based grasping with grip-force tracking and no fine-tuning) is the most credible path to _zero-shot-to-hardware_ contact skills, but each skill is trained in simulation, not learned from one human video.
- **Implication:** for drilling/screwing you should NOT expect zero-shot-from-video. Use a **force-primitive library** (guarded moves, spiral/peg-in-hole search, torque-thresholded fastening) parameterized by the video-extracted goal, executed under impedance/admittance control on a torque-controlled arm.

### 4. Self-modeling / kinematic self-awareness is mature enough to use

- Lipson lab (Columbia/Duke): **full-body visual self-modeling** (Chen, Kwiatkowski, Vondrick & Lipson, _Science Robotics_ 2022, 7(68):eabn1944) learns a query-driven occupancy self-model "accurate to about 1% of the workspace, enabling the robot to perform various motion planning and control tasks," plus damage detection/recovery. The 2025 npj Robotics paper (Hu, Chen & Lipson) extends this to egocentric single-camera dynamic self-models that generalize across robot configurations.
- Practically, "self-awareness" for your build = (a) an accurate kinematic/URDF self-model + reachability/joint-limit checking (FR3 exposes full forward kinematics, Jacobians, dynamics; Isaac cuMotion uses the URDF/XRDF), (b) human→robot motion retargeting (OKAMI object-aware retargeting; Gemini Robotics 1.5 Motion Transfer), and (c) external force/collision estimation (FR3 joint torque sensors at 1 kHz).

### 5. What actually runs locally on Jetson today (latency/rate)

- **π0.5 (openpi) on Jetson AGX Thor:** Jetson AI Lab's official tutorial measured PyTorch BF16 at "Total inference time: 162.64 ± 0.37 ms / Model inference time: 157.94 ± 0.35 ms," and TensorRT FP8+NVFP4 gave 1.71×/1.75× speedup (≈**94–96 ms total / ~90 ms model**) at cosine similarity 0.9956 (Jetson AGX Thor Dev Kit, JetPack 7.x, MAXN). The VLA-Perf paper measures π0 (2.7B, BF16) at **19.0 Hz** on Thor; the "~53 ms" figure circulating is a roofline ceiling, not measured. A third-party custom CUDA engine claims 44 ms (23 Hz) but is unverified forum content.
- **GR00T N1-2B:** **63.9 ms** for a 16-action chunk on an L40 (bf16); System-2 VLM ~10 Hz, System-1 DiT 120 Hz (arXiv:2503.14734). NVIDIA lists Jetson AGX Orin/Thor as supported but publishes no official Jetson latency; the current open model is N1.7 (Apache-2.0, with 20K hours of EgoScale human video in pretraining).
- **Gemini Robotics (flagship hybrid):** ~250 ms observation→action end-to-end, backbone <160 ms, ~50 Hz local decoder loop (arXiv:2503.20020). **Gemini Robotics On-Device** runs fully locally and is the first GR model offered for fine-tuning (as few as 50–100 demos), but Google publishes no official ms/Hz figure for the fully on-device variant; it has been demoed on Jetson-class controllers.
- **OpenVLA (7B) on Jetson AGX Orin:** ~955 ms BF16 → ~375 ms INT4 (~3 FPS) per peer-reviewed quantization studies (arXiv:2505.15304) — too slow for closed-loop force control; usable only as a slow planner.
- **Sub-1B edge VLAs:** **LiteVLA-Edge** (256M, SmolVLM backbone, 4-bit GGUF) hits **150.5 ms / 6.6 Hz** on Jetson AGX Orin (arXiv:2603.03380); SmolVLA (0.45B) uses asynchronous inference (~30% faster completion) and runs on a single consumer GPU; NanoVLA/SwiftVLA target Orin Nano.
- **Jetson AGX Thor** (Blackwell GPU, 128 GB, up to 2070 FP4 TFLOPS, 75–130 W) is the clear target: NVIDIA reports a **7× increase in generative-AI throughput** over AGX Orin after software updates, plus MIG partitioning to run perception + VLA + LLM concurrently, and it is NVIDIA's reference platform for GR00T.

### 6. Hardware ecosystem is ready

- **Arm:** Franka Research 3 (7-DoF, joint torque sensors, 1 kHz FCI torque control, ±0.1 mm repeatability, 3 kg payload, 855 mm reach, ROS 2/MoveIt/libfranka, from ~$35k) is the best research arm for force-adaptive learning; UR5e/UR10e + the Universal Robots AI Accelerator (NVIDIA-based toolkit) is the more industrial route. Bota Systems sells an FR3 6-axis F/T kit with ROS 2 impedance/admittance controllers.
- **Tool change + dual end-effectors:** ATI and Schunk automatic/quick tool changers (sub-second engagement, pass-through for pneumatics/electrical); OnRobot Quick Changer + dual grippers (RG2/RG6, VGC10 vacuum) plus a smart electric screwdriver; Robotiq 2F-85/2F-140 + FT 300 force-torque sensor.
- **Tactile:** GelSight Mini (vision-based), or low-cost magnetic skins (eFlesh, AnySkin/VISK) for fingertip contact sensing.
- **Perception/planning:** Isaac ROS cuMotion (collision-free trajectories in a fraction of a second on Thor), FoundationPose (6D pose of novel objects), nvblox (3D reconstruction), DNN stereo depth — all GPU-accelerated on Jetson and exposed through MoveIt 2.

## Details — Comparison Table

Scoring 1–5 (5 = best). "ZS-video" = zero-shot task from one human video (sense a). "ZS-embodiment" = zero-shot/low-shot transfer to new hardware/env (sense b).

|Approach / Model|ZS-video (a)|ZS-embodiment (b)|Data needs|Contact/force (drill/screw)|Closed-loop reactivity|Jetson edge deployability|Multi-task + tool change|Maturity (TRL)|Open source|Approx cost|
|---|---|---|---|---|---|---|---|---|---|---|
|**π0 / π0.5 (openpi)**|2 (zero-shot only for in-distribution tasks)|4 (cross-embodiment; LoRA fine-tune per robot)|1–20 h to fine-tune|2–3 (no native force; flow-matching 50 Hz)|4 (94–96 ms on Thor)|4 (Thor TRT FP8/NVFP4)|4 (language-conditioned)|4|Yes (Apache-2.0)|Free model|
|**NVIDIA GR00T N1.5/N1.7**|2–3 (EgoScale human-video pretraining helps)|4 (cross-embodiment, post-train per embodiment)|Post-train w/ demos+synthetic (Dreams/Mimic)|2|4 (DiT head fast; Thor reference)|5 (Thor reference platform)|4|4|Yes (Apache-2.0)|Free model|
|**Gemini Robotics 1.5 / On-Device**|3 (strong generalization, Motion Transfer)|4–5 (MT across ALOHA/Franka/Apollo)|50–100 demos to adapt|2|4 (~250 ms hybrid; on-device local)|3–4 (On-Device local; trusted-tester)|4|4|No (SDK/trusted tester)|Commercial|
|**Figure Helix**|2|3 (humanoid-focused)|~500 h teleop|2|5 (onboard GPU, 200 Hz upper body)|n/a (proprietary HW)|4|4|No|Proprietary|
|**OpenVLA (7B)**|1–2|3 (LoRA per robot)|~970k demos pretrain; LoRA to adapt|1|1–2 (~375 ms INT4 on Orin)|2 (too slow unquantized)|3|4|Yes|Free|
|**SmolVLA / LiteVLA-Edge / NanoVLA**|1–2|3|50–200 demos|1–2|3–4 (6.6 Hz Orin; async)|5 (runs on Orin/Orin Nano)|3|3|Yes|Free|
|**OKAMI (single-video imitation)**|5 (single RGB-D human video)|3 (object-aware retarget; needs IK)|1 video|2 (no force model)|3 (closed-loop policy 79.2%)|4 (vision pipeline)|3|3|Partial|Free|
|**RIGVid (generated-video imitation)**|5 (no human demo even needed)|4 (robot-agnostic 6D retarget)|0 (language + scene)|2|3 (real-time pose tracking)|3 (video diffusion heavy; offline gen)|3|Partial|Free||
|**ReKep / VoxPoser**|4 (VLM constraints, no training)|4 (keypoint constraints platform-agnostic)|0 (uses GPT-4o/VLM)|2 (rigidity assumption)|4 (real-time optimization loop)|3 (needs VLM; can be local)|3|Yes|Free||
|**ForceMimic/HybridIL, Reactive Diffusion Policy, FILIC**|1|2|Force-annotated demos|5 (purpose-built for contact)|5 (fast force residual loop)|4 (small policies)|2|3|Partial|Free|
|**Sim-to-real RL (DextrAH-G, ClutterDexGrasp)**|1|5 (zero-shot sim→real)|Sim only (no real demos)|4 (force-based grasping, grip-force tracking)|5|4 (distilled student policies)|2|3|Partial|Free (Isaac Lab)|
|**Classical TAMP + Isaac ROS (cuMotion/FoundationPose)**|n/a|5 (works on any modeled arm)|0 (model-based)|3 (with F/T + impedance)|5 (sub-second planning on Thor)|5|4 (skill library)|5|Yes|Free|

### Why a layered hybrid wins

Each row above is strong in 2–3 columns and weak elsewhere. The only way to score well across _all six_ of your requirements is to compose them, with the classical/Isaac layer guaranteeing safety and the learned layers providing generalization.

## Recommended Optimal Architecture

**Layer 0 — Compute & middleware.** Jetson AGX Thor (128 GB) running JetPack 7, ROS 2, and Isaac ROS. Use MIG to partition the Blackwell GPU: one partition for perception, one for the manipulation VLA, one for the LLM/voice. (Fall back to AGX Orin 64 GB only if budget-constrained — you will be limited to smaller VLAs and ~6–10 Hz.)

**Layer 1 — Demonstration parsing → goal/intent (sense-a zero-shot).** Record the human demo (RGB-D, ideally egocentric). Run an OKAMI-style pipeline: open-world detection (Grounded-SAM) + hand/pose reconstruction (HaMeR) + point tracking (CoTracker) to extract task-relevant objects, subgoals, and a 6D object-pose trajectory. Use a local VLM (Cosmos Reason / Qwen2.5-VL on Thor) or Gemini Robotics-ER 1.5 (if cloud is acceptable for planning only) to label the goal and produce a ReKep-style relational-keypoint constraint set. This is where the system "extracts the final goal directly from the video."

**Layer 2 — Self-model + motion retargeting (self-awareness).** Maintain a kinematic self-model (URDF/XRDF + reachability, joint limits, Jacobian/dynamics from libfranka). Retarget the human trajectory to viable robot end-effector poses (object-aware retargeting), checking feasibility against the self-model; optionally add a Lipson-style learned occupancy self-model for collision/damage awareness. Plan collision-free motions with **Isaac ROS cuMotion** (MoveIt 2 plugin) using **nvblox** scene reconstruction and **FoundationPose** for live 6D object tracking.

**Layer 3 — General manipulation policy (sense-b zero-shot).** Use **π0.5 (openpi, TensorRT FP8+NVFP4 on Thor, ~94–96 ms)** or **GR00T N1.7 (Apache-2.0)** as the language/goal-conditioned visuomotor policy for pick/place/sort/draw and tool acquisition. These give cross-embodiment generalization; LoRA fine-tune with a small number of demos for your specific arm + grippers if zero-shot success is marginal.

**Layer 4 — Force-adaptive controller (the contact-rich gap).** For drilling/screwing/insertion, do NOT rely on the VLA. Run a **force-primitive library** (guarded approach, spiral/peg-in-hole search, torque-thresholded fastening, constant-force pressing) under **impedance/admittance control** on the FR3's 1 kHz torque interface, fused with 6-axis F/T + GelSight tactile feedback. Parameterize each primitive by the goal from Layer 1. Where you need learned adaptation, add a **Reactive-Diffusion-Policy / FoAR-style** fast residual loop, or train the skill in **Isaac Lab** with domain randomization for zero-shot sim-to-real (DextrAH-G/ClutterDexGrasp pattern).

**Layer 5 — Multi-tool execution.** ATI or Schunk automatic tool changer with two parked end-effectors: (1) a tool holder (drill/driver/screwdriver) and (2) an adaptive gripper (Robotiq 2F-85 or OnRobot RG2) for object grasping. A behavior tree orchestrates tool-change → primitive selection → verification.

**Layer 6 — Personality / mood + situational awareness.** A quantized **Llama-class LLM** (8B-class, INT4) or gpt-oss-20B on Thor via vLLM/llama.cpp, with **NVIDIA Riva** ASR+TTS for voice, driving an affective state machine (mood conditioned on task success, human proximity, time). A separate local **VLM** (VILA/Qwen2.5-VL/Cosmos Reason) provides scene narration and safety monitoring (VSS-style). All fully on-device — no cloud dependency.

### Honest gaps & fallbacks

- **Single-video zero-shot for drilling/screwing is not reliable today.** Fallback ladder: (1) force-primitive library parameterized by the video goal; (2) few-shot fine-tune of a force-aware policy (ForceMimic/HybridIL) with a handful of force-annotated demos; (3) residual RL or sim-to-real (Isaac Lab) for the specific fastening skill.
- **VLA + force fusion is immature:** most VLAs are position/vision-centric and update too slowly for control-rate force reaction; the slow-VLA + fast-force-residual split is the current best practice.
- **Local frontier-VLM planning** (vs cloud Gemini Robotics-ER) costs accuracy; budget for the gap or allow cloud for _planning only_ while keeping control fully local.
- **Reproducibility caveat:** openpi GitHub issues report poor real-robot performance after π0.5 fine-tuning when data normalization is mishandled — budget integration time.

## Recommendations (staged)

**Stage 1 (Weeks 0–8) — Reliable skeleton.** Stand up FR3 (or UR5e) + Jetson AGX Thor + Isaac ROS (cuMotion, FoundationPose, nvblox) + MoveIt 2 + tool changer + F/T + tactile. Validate impedance/admittance control and a hand-coded force-primitive library on drilling and screwing into known fixtures. _Threshold to advance:_ >90% success on fixtured fastening with force monitoring.

**Stage 2 (Weeks 8–16) — Zero-shot task transfer.** Add the OKAMI/RIGVid + ReKep video-parsing layer for pick/place/sort/draw/pour. Measure single-video zero-shot success. _Threshold:_ >70% on non-contact tasks from one demo (matching OKAMI's published 71.7%).

**Stage 3 (Weeks 16–28) — General policy + cross-embodiment.** Integrate π0.5 (openpi, TRT) or GR00T N1.7 as the general visuomotor policy; LoRA fine-tune if zero-shot <60%. Benchmark control rate (target ≥10 Hz closed loop on Thor). _Threshold:_ π0.5 ≤ ~90 ms/inference sustained, ≥10 Hz with action chunking.

**Stage 4 (Weeks 28+) — Learned force adaptation + personality.** Add a reactive force-residual policy for the hardest contact tasks (or sim-to-real RL in Isaac Lab). Deploy the local LLM + Riva personality/voice layer and VLM situational awareness on a dedicated MIG partition.

**Benchmarks that change the plan:** If a future on-device VLA demonstrates native force/tactile fusion at ≥20 Hz with single-video task transfer (watch GR00T N-series, π-series, Gemini Robotics On-Device updates), collapse Layers 3–4 into it. If single-video contact-rich success exceeds ~70% in published benchmarks, drop the hand-coded primitive library.

## Caveats

- Several latency figures are vendor/third-party and precision-dependent: GR00T's 63.9 ms is an L40 (not Jetson) number; π0.5's "53 ms on Thor" is a theoretical roofline (measured best-case ~94–96 ms via Jetson AI Lab's TensorRT FP8+NVFP4 path); the 44 ms/23 Hz Thor figures are unverified forum content; OpenVLA Jetson numbers vary ~10–15% by toolchain (≈840/336 ms dusty-nv/nano_llm vs 955/375 ms peer-reviewed).
- Gemini Robotics On-Device, Figure Helix, and Covariant RFM-1 are proprietary; access, pricing, and exact on-device specs are restricted (trusted-tester/partnership).
- Many learning-from-video success rates are from lab benchmarks (tabletop, everyday objects) and will not directly transfer to industrial drilling/screwing tolerances.
- "Self-aware" here means engineering self-models (kinematic/occupancy/dynamics), not consciousness; the Lipson work is the credible reference.
- Costs are approximate and exclude integration labor, which for a stack this complex is the dominant cost.