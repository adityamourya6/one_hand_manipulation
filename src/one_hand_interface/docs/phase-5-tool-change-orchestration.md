# Phase 5 — Tool-Change Orchestration

> **Note:** If you have any technical query regarding the architecture, please go through the master document: [One-Hand Robot.md](One-Hand Robot.md).

## Goal

The manual end-effector swap mechanism built in Phase 2 becomes a real, automatic, verifiable action: given a task that requires a different tool than what's currently attached (e.g. finishing a nailing operation and needing to hammer the nail down next), the system detects this, executes the swap, verifies it succeeded, and proceeds — without a person manually triggering each step.

## Why this phase comes here, and not earlier or later

This phase deliberately sits after Phase 3 (video-to-goal) and Phase 4 (force control), not alongside the Phase 2 groundwork, for a concrete reason: orchestration only makes sense once there's something real to orchestrate *between*. Before Phase 3, there's no task pipeline producing "this is what needs to happen next." Before Phase 4, "hammer the nail" isn't a real executable action — it's just a vague idea, since force-controlled primitives are what make contact-rich actions like hammering or fastening actually work. Building the orchestration logic earlier would mean building it against placeholders, which is wasted motion you'd have to redo once the real pieces existed. This is also explicitly the gap we identified back when we scoped the swappable end-effector — Phase 2 built the mechanism, this phase builds the judgment around it.

---

## 5a. The Architectural Pattern: Behavior Trees, Not Ad-Hoc Scripts

### Why a behavior tree specifically, rather than a sequence of if-statements

Tool-change orchestration needs to handle things going wrong — a swap that fails partway, a verification check that comes back negative, a primitive that doesn't complete — and a hand-rolled sequence of conditionals tends to become unmanageable fast once you're handling failure paths for every step. Behavior trees are the standard robotics answer to exactly this problem, and they're not a niche choice: `BehaviorTree.CPP` is described by its own maintainers as the most widely used robot deliberation library in the ROS 2 ecosystem, and it's the same library underlying Nav2 (ROS 2's navigation stack) and PickNik's MoveIt Pro. This isn't an obscure tool you'd be taking a risk on — it's infrastructure other serious ROS 2 systems already depend on.

### The recommended system architecture

The official ROS 2 integration guidance for BehaviorTree.CPP is specific and worth following directly rather than reinventing: maintain a single centralized "Task Planner" coordinator node, implemented with the behavior tree, that's responsible for the execution of the overall behavior, while every other part of the system is a service-oriented component that delegates business logic and decision-making to that Task Planner rather than making its own decisions. Map this onto your system directly: your behavior tree is the Task Planner; your MoveIt 2 planning, your Phase 3 perception pipeline, your Phase 4 force primitives, and your tool-change mechanism are all service-oriented components the tree calls into and gets `SUCCESS`/`FAILURE`/`RUNNING` results back from — they don't decide anything themselves, they just execute when told to and report what happened.

### Node types you'll actually use

- **`BT::ActionNode`** — the workhorse; performs an actual task (e.g. "execute tool swap," "run guarded-approach primitive") and returns `SUCCESS`, `FAILURE`, or `RUNNING`.
- **`BT::ConditionNode`** — a simplified check with no `RUNNING` state (e.g. "is the current end-effector the one this task needs?").
- **Control nodes** (Sequence, Fallback) — Sequence is logical AND (do this, then this, then this, fail if any step fails); Fallback is logical OR (try this, if it fails try this instead) — this is your natural mechanism for retry/recovery logic around a failed swap.
- **`BehaviorTree.ROS2`** — the official wrapper package providing standard implementations for wiring tree nodes to ROS 2 actions, services, topic publishers, and subscribers, so you're not writing raw `rclcpp_action` boilerplate yourself for every tree node.

---

## 5b. What the Tree Actually Needs to Decide and Do

### Trigger condition: does the current task need a different tool than what's attached

This is a `ConditionNode` consuming two pieces of state: which task/primitive Phase 3's dispatch is about to execute, and which end-effector is currently attached (tracked from Phase 2's manual swap mechanism, now made queryable rather than something only a human knows). If they don't match, the tree needs to insert a swap before proceeding.

### The swap sequence itself, as a Sequence node

This is literally your Phase 2 manual procedure, now wrapped as tree-executable steps rather than something you trigger by hand: detach current tool (MoveIt collision-object detach + MuJoCo weld disable) → move to dock position for the needed tool → attach new tool (MoveIt collision-object attach + MuJoCo weld enable) → verify.

### Verification — the part that didn't exist in Phase 2's scope

Phase 2 deliberately stopped at "verify via `isStateValid()` that the resulting model is collision-consistent" — a basic check, not real failure handling. This phase needs to go further:

- **Geometric verification**: does the planning scene's collision model agree with MuJoCo's physical state (the tool is welded where the model thinks it is, not floating or in a strange configuration)? This is exactly the synchronization concern flagged back in Phase 2 — now it needs an automated check, not just developer vigilance.
- **Task-readiness verification**: given the now-attached tool's TCP offset (also from Phase 2), can the upcoming task's target pose actually be reached and is it collision-free? This re-runs the same `isStateValid()`/`isPathValid()` check from Phase 2, but now as a tree node returning `FAILURE` (triggering a Fallback/retry path) rather than something a developer eyeballs.
- **What to do on verification failure**: a Fallback node wrapping a small number of retry attempts (re-attempt the swap sequence) before escalating to a genuine failure state the rest of the system needs to handle — for now, that can simply mean halting and surfacing a clear error rather than attempting open-ended automatic recovery, which is a reasonable place to stop for this phase.

### Primitive selection after a successful swap

Once verification passes, the tree proceeds to whichever Phase 3/Phase 4 primitive the task actually needs (e.g., now that the hammer is attached and verified, execute Phase 4's torque-thresholded fastening primitive with parameters from Phase 3's extracted goal). The tree's job is sequencing and failure-handling, not reimplementing what Phase 3/4 already built.

---

## 5c. Scope Boundary: What's Explicitly Not in This Phase

- **No LLM involvement yet.** The tree's trigger condition (does the task need a different tool) is driven by structured task metadata from Phase 3's dispatch, not by an LLM deciding anything in real time. The LLM front-end (Phase 6) sits *above* this tree, deciding which task to run next in natural-language terms — this phase's tree doesn't care how a task was selected, only whether the currently selected task's tool requirement matches what's attached.
- **No real tool-changer hardware mechanics.** As noted since Phase 2, the physical coupling here is a MuJoCo weld constraint, not an ATI/Schunk-style automatic coupler. That hardware decision remains deferred to a post-sim stage.
- **No sophisticated automatic recovery beyond a bounded retry.** If a swap fails repeatedly, halting with a clear error is the right scope for now — building genuinely intelligent failure recovery (e.g. diagnosing *why* a swap failed and adapting) is a meaningfully harder problem than what this phase needs to solve to prove the architecture works.

---

## Risks and Watch-Outs

- **Don't let the behavior tree quietly become where business logic lives that should live in Phase 3/4's actual implementations.** Per the official architecture guidance, the tree coordinates and decides sequencing/retries; it shouldn't contain, say, the actual math of a force primitive. Keep that separation deliberate as the tree grows.
- **The geometric/physical sync check (5b) is the most important new piece of this phase, and the easiest to skip under time pressure.** Phase 2 flagged this risk and stopped short of solving it; this phase's entire value-add is solving it for real. Don't let it stay a manual "I'll just check by eye" step.
- **Test failure paths deliberately, not just the happy path.** It's easy to build a tree that works when everything goes right and discover the Fallback/retry logic is broken only when something actually fails for the first time in front of you. Deliberately inject a failure (e.g. manually misalign the dock position) during development to confirm the tree actually catches and handles it.
- **Keep the trigger condition's task-metadata format simple and explicit for now.** It's tempting to over-design a rich task-description schema in anticipation of the Phase 6 LLM layer. Resist — build the minimum structured format Phase 3 can produce and this phase's tree can consume, and let Phase 6's actual requirements (once you're there) tell you what needs to change, rather than guessing now.

## What "Done" Looks Like

- A `BehaviorTree.CPP` tree, wired via `BehaviorTree.ROS2`, automatically detects when an upcoming task's required end-effector doesn't match what's currently attached.
- The tree executes the full swap sequence (detach → dock → attach) as tree-driven action nodes, not a manually-run script.
- Verification after a swap checks both geometric/physical consistency (MoveIt model vs. MuJoCo physical state) and task-readiness (is the upcoming task's target reachable and collision-free with the new tool's TCP offset).
- A deliberately-injected failure during development is caught by the tree's Fallback/retry logic rather than silently succeeding or crashing.
- After a successful, verified swap, the tree correctly hands off to the appropriate Phase 3/Phase 4 primitive for the actual task.
- You can demonstrate, end to end in sim, your originally stated example: the arm finishes a nailing-related operation, the tree detects a tool mismatch, executes and verifies a swap to the hammer, and proceeds to a Phase 4 force-controlled hammering primitive — with no manual triggering at any step.

---

## Scope Note: Deviations From `One-Hand_Robot.md`

Continuing the tracking from Phases 1-4:

- **The source document's Layer 5 ("multi-tool execution... a behavior tree orchestrates tool-change → primitive selection → verification") is being implemented essentially as described** — this is one of the few places our plan tracks the doc's own language closely, since the doc's phrasing here already matches the BehaviorTree.CPP-based pattern that's standard ROS 2 practice.
- **What's still deferred relative to the doc**: real automatic tool-changer hardware (ATI/Schunk), and any LLM involvement in the trigger/decision logic — both remain out of scope until later phases/post-sim hardware work, as tracked since Phase 2.
- **MuJoCo instead of Isaac Sim / Isaac ROS** — unchanged from prior phases.
- **The 6-phase build order remains ours, not the doc's**, as noted previously. Phase 6 (LLM front-end + integration) is next.
