# Phase 3 — Zero-Shot Video-to-Goal Pipeline

> **Note:** If you have any technical query regarding the architecture, please go through the master document: [One-Hand Robot.md](One-Hand Robot.md).

## Goal

Given one human demonstration video, extract an object-centric goal and produce a robot trajectory that succeeds on a *new* instance of that task (different object position/orientation, possibly a different but similar object) — with no task-specific code written for that new instance. This is the core novel work of the whole project, and the phase most worth being honest about going in: it's research-grade engineering, not "install a library and call a function."

## Why this is the highest-risk phase in the plan, and why that's expected

Phases 1 and 2 are solved problems with mature tooling (ROS 2, MoveIt 2, MuJoCo bridges) — the work is integration, not invention. Phase 3 is different: OKAMI (CoRL 2024) and RIGVid (ICLR 2026) are recent peer-reviewed papers with real released code, but "real released code" for a research paper means something different from "production library." Expect rough edges, environment-specific assumptions baked in by the original authors, and genuine debugging where you can't just look up the answer. Budget for this honestly rather than assuming Phase 3 will move at Phase 1/2's pace.

---

## 3a. Two Real, Code-Available Approaches — and a Critical Difference Between Them

### OKAMI — humanoid-specific, not a drop-in fit for your single arm

OKAMI's public code (`UT-Austin-RPL/OKAMI` on GitHub) is real and runnable, but it's worth being precise about what it actually targets: the pipeline runs a plan-generation step, then a separate hand-processing step, then human motion reconstruction, then plan generation, using conda environments specifically named `okami` and `hamer`. More importantly, OKAMI's own paper describes itself as enabling a bimanual humanoid with two dexterous hands to imitate manipulation behaviors from a single RGB-D video demonstration, via a two-stage process where the first stage processes the video to generate a reference manipulation plan, using GPT-4V and large vision models, and the second stage retargets human motions onto the humanoid with object awareness.

This matters directly for you: **the released retargeting code assumes a bimanual humanoid target embodiment**, not a single 7-DOF Franka-class arm. The body-motion and hand-pose retargeting math, the example configs, and the evaluation tasks are built around a two-armed, dexterous-handed robot. Adapting OKAMI's *method* (object-aware retargeting from a single video) to a single-arm Franka is a real, nontrivial engineering task — you'll be reusing the perception front-end (object detection, hand tracking) largely as-is, but writing your own retargeting logic for a single-arm kinematic chain rather than reusing OKAMI's retargeting code directly.

### RIGVid — embodiment-agnostic by design, code is public, more directly applicable

RIGVid's code is publicly released at `github.com/shivanshpatel35/rigvid`, and unlike OKAMI, embodiment-agnosticism is a stated design goal that's been demonstrated on real hardware: RIGVid's approach for extracting an object's motion from a generated video, based on model-based six DoF object pose tracking, was shown working across multiple robots, and the authors note it "is embodiment-agnostic, meaning it's not tied to a single robot", with the project page confirming RIGVid execution demonstrated on both XArm7 and Aloha — two different, structurally different robots, run through the same pipeline. This is a much better structural fit for "I have a single Franka-class arm and want to retarget onto it" than OKAMI's humanoid-first design.

The tradeoff: RIGVid's pipeline doesn't require a human demonstration video at all in its primary mode — given a language command and an initial scene image, a video diffusion model generates potential demonstration videos, a vision-language model automatically filters out results that don't follow the command, a 6D pose tracker extracts object trajectories from the generated video, and the trajectories are retargeted to the robot in an embodiment-agnostic fashion. If your actual use case is "I filmed a real human doing this task, learn from that specific video," RIGVid's pipeline is built around *generated* videos as the primary path — using it with a real human video instead means you're using its 6D-pose-extraction-and-retargeting machinery while skipping its video-generation front-end, which is a smaller adaptation than OKAMI's retargeting mismatch, but still an adaptation, not a default supported mode.

### What this means for your plan

Given your use case (learning from a real filmed human demo, onto a single Franka-class arm), the realistic path is a hybrid: **use RIGVid's 6D-pose-tracking-and-embodiment-agnostic-retargeting approach as your core retargeting method** (since it's structurally the right fit for a single arm), while **borrowing OKAMI's object-aware goal-extraction concepts and perception front-end ideas** (open-world detection, hand-pose understanding) for the "parse what the human actually did" stage. You are not going to clone either repo and have it work end-to-end on your robot without modification — plan for an adaptation layer between "their released code" and "your Franka-in-MuJoCo setup," and budget real time for it.

---

## 3b. Build It Standalone First — No ROS, No MuJoCo Dependency

This is the single most important process decision for this phase: develop the entire perception-to-goal pipeline as plain Python, validated against video files sitting on disk, completely decoupled from ROS 2 and MuJoCo at first.

The reason this matters more here than it did in Phases 1-2: this pipeline has several independent failure points (detection, tracking, hand-pose, retargeting math), and if you're also running it inside a live simulation loop, every bug becomes ambiguous — is the perception wrong, or is the sim/ROS plumbing wrong? Decoupling lets you debug perception bugs purely by looking at extracted trajectories overlaid on the source video, with zero simulation noise in the picture. Only once the pipeline reliably produces sane goals/trajectories on recorded video should you wire its output into the MuJoCo scene (directly first, then via the Phase 1 ROS 2 bridge once that's stable).

---

## 3c. Pipeline Components

### Object detection and segmentation

Identify task-relevant objects in the video frames (Grounded-SAM or a lighter open alternative, given your 6GB VRAM constraint — check current memory footprint before committing, and prefer a smaller model variant if one exists). This needs to run per-frame or per-keyframe across the whole demo video.

### Object tracking across frames

Once objects are detected/segmented in a keyframe, track them across the rest of the video (Cutie or similar) so you have a consistent identity for "the cup" across the whole clip, not just per-frame detections that might flicker or misidentify.

### Hand pose / reconstruction

Understand what the human hand is doing — grasp type, approach trajectory, release point (HaMeR or similar). This is most directly useful for understanding *how* something was grasped/manipulated, which matters for retargeting onto your gripper.

### 6D object pose tracking (the RIGVid-style core)

Extract the actual 6D pose trajectory of the manipulated object(s) over time — this is the structurally important piece for single-arm retargeting, since "where does the object go, in 6D, over time" is embodiment-agnostic in a way that "where does the human hand/arm go" is not.

### Goal extraction

Turn the tracked object+hand trajectories into an object-centric goal description — a sequence of relative poses or keypoint constraints (ReKep-style), rather than a literal joint-by-joint copy of human motion. This abstraction is what makes "zero-shot to a new object position" possible: you're extracting *what changed about the object's state*, not literally replaying recorded motion.

---

## 3d. Retargeting — Your Own Code, Informed by Both Papers

Since neither paper's retargeting code is a direct drop-in (OKAMI: wrong embodiment; RIGVid: built around its own generation pipeline), this is genuinely your team's code to write, using both papers' published methodology as the reference design rather than as a library to import.

### What it needs to do

Map the extracted object-centric goal onto a feasible Franka end-effector + gripper trajectory, respecting the kinematic self-model from Phase 2 — check every retargeted waypoint against `isStateValid()`/`isPathValid()` before trusting it. This is exactly why Phase 2's self-model work had to come first: this step doesn't work without it.

### Account for whichever end-effector is active

If your swappable end-effector groundwork from Phase 2 is in play, the retargeting step needs to know which tool's TCP offset to plan around — the goal extracted from the video doesn't know or care about your tool-changer, but your retargeting code does.

---

## 3e. Closing the Loop in Sim — and the Actual Zero-Shot Test

Feed the retargeted trajectory into your MuJoCo scene and execute it on a **new** object instance — different position, different orientation, ideally a visually distinct but functionally similar object — than whatever appeared in the source demo video. This is the part that's easy to accidentally cheat without meaning to: replaying a trajectory on the *same* scene configuration as the demo proves almost nothing. The real test is generalization.

### Honest evaluation

Measure success rate per task type (pour, wipe, stack, open), the same way OKAMI and RIGVid report their numbers, so you have a real, comparable benchmark of where your adapted pipeline stands relative to the published 71.7%/79.2% (OKAMI) and 85.0% (RIGVid) figures. Don't expect to match these numbers immediately — they're the result of mature, well-resourced research pipelines on their own evaluated tasks and embodiments. Your honest number, even if lower, is far more useful than an inflated one for deciding what to fix next.

---

## Risks and Watch-Outs

- **Don't expect either repo to run end-to-end on your setup without real adaptation work.** OKAMI's retargeting is humanoid-specific; RIGVid's primary mode assumes generated rather than real demo video. Budget for an adaptation layer, not a clone-and-run.
- **Build visualization/debugging tooling early, before chasing pipeline accuracy.** Overlay extracted object trajectories and hand poses directly on the source video frames. Without this, a failure could be in detection, tracking, hand-pose, or retargeting, and you'll have no fast way to tell which.
- **VRAM is a real constraint here, not a theoretical one.** Running detection + tracking + hand-pose models in the same process will likely exceed 6GB if loaded simultaneously. Plan to run stages sequentially, cache intermediate outputs (detections, tracks, poses) to disk between stages, and treat cloud GPU rental as the answer if you want to batch-process many demo videos or run at higher resolution.
- **Camera framing consistency matters more than it seems.** Phase 2's perception scaffolding validated your MuJoCo camera's intrinsics/extrinsics — make sure your real demo videos are filmed from a roughly comparable viewpoint (tabletop, similar height/angle), since a wildly different camera geometry between "demo video" and "sim execution camera" adds an extra confound on top of everything else.
- **Don't quietly cheat the zero-shot test by reusing the demo's exact scene.** It's tempting once something finally works to declare victory — make the new-instance test a hard requirement before calling any task "done."
- **This phase will likely take meaningfully longer than your other phases.** That's not a sign of doing it wrong; OKAMI and RIGVid each represent a research team's months of focused work even with strong existing tooling. Set expectations (with your co-founder too) accordingly.

## What "Done" Looks Like

- A standalone Python pipeline (no ROS/MuJoCo dependency) takes a recorded human demo video file and produces a visualized, sane-looking object-centric goal/trajectory you can inspect frame-by-frame.
- You can articulate clearly, in your own words, why OKAMI's released retargeting code doesn't transfer directly to a single arm, and why RIGVid's structural approach (6D object pose tracking, embodiment-agnostic retargeting) is the better core method for your case, even though its primary pipeline mode assumes generated rather than real video.
- Your own retargeting code takes the extracted goal and produces a Franka end-effector trajectory that passes Phase 2's `isStateValid()`/`isPathValid()` checks.
- The retargeted trajectory executes successfully in MuJoCo on a genuinely new object configuration (not the demo's exact scene) for at least one task type.
- You have an honest, measured success rate across your kitchen task types (pour, wipe, stack, open), understood in context relative to (not expected to match) OKAMI's and RIGVid's published numbers.

---

## Scope Note: Deviations From `One-Hand_Robot.md`

Continuing the tracking from Phases 1-2:

- **The source document presents OKAMI and RIGVid as largely interchangeable members of the same "learning-from-human-video" family**, scored side-by-side in its comparison table. Our research surfaced an important practical distinction the doc doesn't dwell on: OKAMI's released code specifically targets bimanual humanoid retargeting, while RIGVid's is genuinely embodiment-agnostic and demonstrated across multiple real robot types. This changes which one we lean on for retargeting specifically (RIGVid-style) versus which we draw concepts from more loosely (OKAMI-style object-aware goal extraction).
- **We are not using RIGVid's video-generation front-end as designed.** The doc and RIGVid's own paper center the pipeline around AI-generated demonstration videos, not real filmed human video. We're adapting its pose-tracking-and-retargeting machinery to work from real human demo footage instead, which is a deviation from RIGVid's primary supported use case.
- **MuJoCo instead of Isaac Sim / Isaac ROS** — unchanged from prior phases.
- **No Jetson hardware / edge latency targets yet** — unchanged from prior phases; this phase's compute is being planned around a 6GB VRAM laptop plus on-demand cloud rental, not the doc's Thor-based deployment target.
