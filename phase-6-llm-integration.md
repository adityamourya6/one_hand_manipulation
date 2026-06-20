# Phase 6 — LLM Front-End and Full Integration

## Goal

Natural-language task descriptions ("pour the water into the bowl," "the nail is in, now hammer it down") get reliably translated into the right sequence of calls into everything built in Phases 1-5 — the behavior tree from Phase 5 actually executing, the right Phase 3 goal-extraction or Phase 4 force-primitive getting selected, the right tool-change being triggered when needed — with no per-task code written by you. This is the layer that turns five phases of separate infrastructure into the single coherent system the original document actually envisioned.

## Why this phase is mostly integration, not new invention

Unlike Phase 3 (genuinely open research) or Phase 4 (careful control engineering you build largely from scratch), this phase has a real, current, directly-applicable open-source framework purpose-built for almost exactly this problem. The job here is adopting and adapting it correctly, not inventing the architecture yourself.

---

## 6a. The Right Foundation: ROS-LLM

### What it is, and why it's a strong fit rather than just "an LLM wrapper"

ROS-LLM is an open-source framework, published in *Nature Machine Intelligence* (2026) by researchers at Huawei Noah's Ark Lab, TU Darmstadt, and ETH Zurich, designed specifically for intuitive robot programming by non-experts, leveraging natural language prompts and contextual information from ROS — letting people articulate task requirements through a chat interface rather than writing robot-specific code. Its own stated key features map almost one-to-one onto what this phase needs: integration of ROS with an AI agent connected to many open-source and commercial LLMs, automatic extraction of a behavior from the LLM's output and execution of the corresponding ROS actions/services, support for three behavior execution modes — sequence, behavior tree, and state machine — and a mechanism for LLM reflection via human and environment feedback (i.e., the system can notice something didn't work and adjust, rather than blindly trusting its first plan).

The behavior tree execution mode is the one that matters most for you directly: it means ROS-LLM is designed to sit on top of a `BehaviorTree.CPP`-based system exactly like the one built in Phase 5, rather than requiring you to throw that work away and adopt some other execution paradigm. The code is public and current, at `github.com/huawei-noah/HEBO/tree/master/ROSLLM`.

### What this buys you versus building it yourself

The hard, easy-to-get-wrong parts of this layer — reliably parsing free-form natural language into structured, executable robot actions, handling the case where the LLM's first attempt doesn't quite work and needs adjustment, and connecting that pipeline cleanly into ROS's action/service model — are exactly what ROS-LLM's authors spent the effort solving and validating, including on long-horizon tasks and tabletop rearrangement scenarios in their own evaluation. Re-deriving this from scratch would mean redoing real research-engineering work that's already been done and published.

---

## 6b. Local-First LLM Inference: `llama_ros`

### Matching your stated hardware constraints

Consistent with your local-first-with-cloud-for-training policy established earlier in this project, the LLM inference itself doesn't need to be a cloud API call. `llama_ros` is a tool specifically built to integrate quantized LLMs into ROS 2 systems, leveraging `llama.cpp` (a highly optimized runtime engine) to run quantized models efficiently within the real-time constraints and resource limitations of robotics systems — explicitly framed by its authors as solving the computational-efficiency and memory-limitation challenges of edge AI in robotics.

This is a direct match for the ceiling identified back in Phase 1's hardware discussion — a quantized 7-8B model (INT4) was established as roughly the realistic local limit for your 6GB VRAM laptop. `llama_ros` is built around exactly this use case: running a quantized model as a ROS 2 node, not requiring a cloud round-trip for every dispatched instruction.

### Where cloud still makes sense

For development and testing — iterating quickly on prompt design, debugging why a particular instruction got parsed incorrectly — a cloud API call (Claude, GPT, etc.) is faster to iterate with and removes local-inference debugging from the loop while you're tuning the dispatch logic itself. Treat local quantized inference via `llama_ros` as the target for the actual integrated system, and cloud API calls as a development convenience you can fall back to when iterating on logic, consistent with the local-first-but-cloud-when-it-genuinely-helps approach already established for this project.

---

## 6c. What the Dispatch Layer Actually Needs to Map

### Inputs it needs to understand

- A natural language instruction from a person.
- Current scene state (what objects are present, where — likely fed from your Phase 2/3 perception scaffolding).
- Current end-effector state (what's attached right now, from Phase 5's tracked state).

### Outputs it needs to produce

- Which task template/pipeline applies (pour, wipe, stack, open, hammer/fasten, etc. — your established kitchen task families plus the contact-rich ones from Phase 4).
- Which objects in the current scene the instruction refers to (binding "the bowl" in the instruction to an actual tracked object in the scene).
- Whether the required end-effector matches what's attached, which feeds directly into Phase 5's tree (the LLM doesn't decide *how* to swap tools — it decides *that* the task implies a particular tool requirement, and hands that off to the Phase 5 tree, which already knows how to check and act on a mismatch).

### What it explicitly should not try to do

It should not be reimplementing Phase 3's goal extraction, Phase 4's force control, or Phase 5's swap logic in natural-language reasoning. Its entire job is selection and parameter-binding — picking which already-built capability applies and filling in the specifics (which object, which target) — not re-deriving robot behavior through language-model reasoning. This boundary matters: the further the LLM strays from "structured dispatch" toward "freeform robot behavior planning," the less reliable and more dangerous the system becomes, since none of Phases 1-5's safety nets (collision checking, verification, force thresholds) apply to something the LLM invents on the fly outside those established pipelines.

---

## 6d. Reflection and Feedback — Closing the Loop Properly

ROS-LLM's "LLM reflection via human and environment feedback" feature is worth taking seriously rather than treating as a nice-to-have, because it's what keeps this layer honest over time: if a dispatched task fails (Phase 5's verification catches a bad tool swap, or a Phase 3 retargeted trajectory fails `isStateValid()`, or a Phase 4 force primitive hits an unexpected resistance), that failure should flow back to the LLM layer as feedback it can reason about and potentially retry differently — not silently swallowed, and not surfaced only as a raw error a person has to interpret themselves.

Practically: wire the failure/success signals already being produced by Phases 2-5 (collision check results, verification outcomes, force-threshold trips) into ROS-LLM's feedback mechanism, rather than building a separate, redundant feedback channel. Those signals already exist; this phase's job is making sure they reach the place that can act on them.

---

## 6e. Personality, Voice, and Situational Awareness — Reinstated as Real Scope

### Why this is back, and why it's a separate sub-phase rather than folded into dispatch

Earlier in this project, the personality/mood/voice layer from the source document's Layer 6 was deliberately narrowed out of scope, on the reasoning that it added nothing toward proving reliable task execution. On reflection — and now that there's no pitch deadline forcing a minimum-viable-demo mindset — that narrowing was made without explicitly asking whether you wanted it as real capability, not just polish. It's being reinstated here as genuine scope, but kept as its own sub-phase rather than merged into 6a-6d, because the two have different correctness criteria: dispatch reliability is measured by "did the right action execute," while personality/voice is measured by "did the interaction feel natural and aware" — conflating them risks a bug in one being masked by, or mistaken for, the other.

### Voice I/O: NVIDIA Riva

Riva is a GPU-accelerated SDK for real-time speech and translation pipelines, delivering automatic speech recognition (ASR) and text-to-speech (TTS), deployable at the edge or embedded, not just in the cloud — directly matching your local-first hardware approach. It's not a theoretical fit: there are multiple real, working ROS 2 integrations already built and documented, including `ros2_jetbot_voice`, a set of ROS 2 nodes wrapping Riva's ASR/TTS services with explicit handling for the practical wrinkles of voice-driven robotics (e.g. muting the microphone during TTS playback to prevent the robot hearing and reacting to its own speech, an echo-feedback problem you'd otherwise hit and have to debug yourself). Riva's own integration guidance is similarly concrete: their out-of-the-box Python ASR client script needs only minor modification to route transcribed text onto a ROS topic instead of printing to a terminal, which is the natural entry point for piping recognized speech into Phase 6's dispatch layer (6a-6c) as the source of natural-language instructions, replacing or supplementing typed text input.

### A concrete, important hardware-budget lesson from a real deployment

One documented real-world deployment (LuxAI's QTrobot, pairing Riva ASR with a locally-run 13B conversational LLM for an "offline conversation" / personality-driven interaction mode) reports that 13B model alone consuming 28 GB of GPU memory. This is worth treating as a hard, concrete warning rather than an abstract concern: 28 GB is roughly 4-5x your entire 6GB VRAM budget. The direct implication is that your personality/conversational LLM and your task-dispatch LLM (6a-6c) cannot both be sizable local models running simultaneously — you'll want either a meaningfully smaller quantized model for the personality layer specifically, a shared single model serving both roles rather than two separate models, or cloud API calls for the conversational/personality layer specifically (treating dispatch as the thing that must work reliably and locally per your stated priorities, while personality chat is more tolerant of an occasional cloud round-trip).

### Situational awareness — what it concretely means here, scoped honestly

The source document's framing includes a separate local VLM providing scene narration and safety monitoring, with mood conditioned on task success, human proximity, and time. For an honest v1 scope: start with task-success-conditioned reactions (the robot's TTS responses reflect whether the last dispatched action from 6f succeeded, failed, or is in progress — this is "free," since 6d's reflection/feedback signals already carry exactly this information) before attempting human-proximity-based mood or a separate scene-narration VLM running concurrently, which would compete for the same limited VRAM budget as everything else already running (dispatch LLM, perception models from Phase 3, the impedance/MPC control loop from Phase 4). Treat proximity-aware mood and continuous scene narration as a further stretch beyond basic task-success-reactive voice output, not as part of the same initial milestone.

### Where this plugs into the existing architecture

This sub-phase is additive, not a fork: Riva's ASR output becomes another input path into 6a-6c's dispatch layer (alongside or instead of typed text), and Riva's TTS becomes an output consumer of 6d's existing reflection/feedback signals (success, failure, in-progress states) plus whatever additional personality-layer text generation you add on top. Nothing in 6a-6d needs to change structurally to support this — the dispatch layer doesn't need to know whether its input came from text or voice, and the reflection mechanism doesn't need to know whether its output is being spoken or just logged.

---

## 6f. Full Integration — What "Wiring It All Together" Actually Means

This is the point where the project stops being five separate, independently-validated pieces and becomes one system. Concretely:

1. **Phase 6's dispatch layer** receives a natural-language instruction (typed, or now spoken via 6e's Riva ASR).
2. It identifies the task type and binds it to objects in the current scene (using Phase 2/3's perception scaffolding for scene state).
3. It hands off to **Phase 5's behavior tree**, which checks whether the required end-effector is attached, swaps and verifies if not, then proceeds to execute.
4. The tree calls into **Phase 3's** retargeted trajectory (for non-contact tasks) or **Phase 4's** force-primitive library (for contact-rich tasks), using **Phase 2's** self-model for feasibility checks throughout.
5. Success/failure flows back up through the tree to Phase 6's reflection mechanism, closing the loop — and now, optionally, out through 6e's TTS as spoken feedback.

### Don't attempt this all at once

Integrate one task family at a time, starting with whichever has been most thoroughly validated in isolation (likely a non-contact kitchen task from Phase 3, since it has the fewest moving parts). Get one natural-language instruction reliably working end-to-end before adding the second task family, and only attempt a task requiring a tool swap (exercising Phase 5 fully) once at least one non-swap task is solid — this mirrors the same "prove the simple case before the complex one" discipline used throughout the earlier phases.

---

## Risks and Watch-Outs

- **Resist letting the LLM do more than structured dispatch.** The temptation to let it "just figure out" something Phases 1-5 don't already handle is exactly how the system's safety guarantees (collision checking, force thresholds, verification) get silently bypassed. If a capability doesn't exist in Phases 1-5, the right fix is building it there, not asking the LLM to improvise around the gap.
- **Don't build a redundant feedback/reflection mechanism alongside ROS-LLM's existing one.** Phases 2-5 already produce the signals this phase needs (collision results, verification outcomes, force trips); the integration work is plumbing those into ROS-LLM's mechanism, not inventing a parallel system.
- **Local quantized inference will be slower and occasionally less reliable than a cloud API call** — this is an expected, known tradeoff of the local-first approach, not a sign something is configured wrong. Budget for this directly in how you set expectations for response latency in the integrated demo.
- **Integrate incrementally, one task family at a time**, per the discipline above — attempting full integration in one pass makes it nearly impossible to localize which phase's boundary is actually broken when something fails.
- **Test the failure-reflection path deliberately**, the same way Phase 5 called for deliberately injecting a tool-swap failure — induce a Phase 3 trajectory failure or a Phase 4 force-threshold trip on purpose during development and confirm the failure correctly reaches and is handled by Phase 6's reflection mechanism, rather than only ever testing the happy path.

## What "Done" Looks Like

- A natural-language instruction reliably dispatches to the correct task family and binds correctly to objects in the current scene.
- At least one full task executes end-to-end purely from a natural-language instruction, with no manual triggering of any individual phase's mechanism.
- At least one task requiring a tool swap executes end-to-end, correctly exercising Phase 5's full tree (mismatch detection → swap → verification → primitive execution).
- A deliberately-induced failure at some point in the pipeline correctly surfaces through ROS-LLM's reflection mechanism rather than failing silently or crashing the system.
- The LLM inference runs locally via `llama_ros` with a quantized model fitting your hardware constraints, with cloud API calls understood as a development-time convenience rather than a permanent dependency.
- You can clearly articulate the boundary between "what the LLM decides" (task selection, parameter binding) and "what the underlying phases decide" (how to actually execute safely), and why that boundary is where it is.
- (Personality/voice layer) Riva ASR successfully feeds a spoken instruction into the same dispatch path a typed instruction would use, and Riva TTS produces spoken output reflecting at least task-success/failure state from the reflection mechanism — confirmed not to exceed your VRAM budget when running alongside the dispatch LLM (per the 28GB/13B cautionary finding above, validate actual combined memory usage rather than assuming it fits).

---

## Scope Note: Deviations From `One-Hand_Robot.md`

Closing out the tracking from Phases 1-5:

- **The source document's Layer 6 ("personality/mood + situational awareness... quantized Llama-class LLM... driving an affective state machine") was initially narrowed to dispatch-only, then reinstated as real scope (6e) once you confirmed you wanted it.** The initial narrowing reflected an assumption (useful for an investor-pitch deadline) that personality added nothing toward proving execution reliability — true as far as it goes, but that tradeoff was made without explicitly checking it against your actual goals once the pitch deadline was dropped. It's now real scope, kept deliberately separate from the dispatch layer (6a-6d) so the two aren't measured by the same correctness bar, with situational awareness honestly scoped down from the doc's full vision (proximity-aware mood, continuous scene narration) to a more tractable first milestone (task-success-reactive voice) given shared VRAM constraints with the rest of the running system.
- **ROS-LLM and `llama_ros` were not named in the source document at all** — they're current, real frameworks our research surfaced as a strong match for this phase's needs, not something carried over from the doc.
- **MuJoCo instead of Isaac Sim / Isaac ROS** — unchanged from all prior phases; this phase's integration work assumes the MuJoCo-based stack built throughout.
- **This closes the 6-phase build order established across this project** (Foundations → Classical Skeleton + EE Groundwork → Video-to-Goal → Force Control → Tool-Change Orchestration → LLM Front-End/Integration), which remains a sequencing decision made together over the course of this conversation, not something prescribed by the source document.
