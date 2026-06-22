# One-Hand Manipulation: Standard Process Flow

This document defines the strict, high-level operational workflow that governs all development phases in the One-Hand Manipulation project. This process ensures architectural consistency, scientific rigor, and clear progress tracking throughout the lifecycle of the project.

---

## 1. Review Phase Plan
**Objective:** Establish context and architectural boundaries before writing any code.
- **Action:** Read the specific phase's markdown plan (e.g., `phase-2-classical-skeleton.md`).
- **Architectural Alignment:** Consult the master document (`One-Hand Robot.md`) for deep technical guidance. This document acts as the ultimate source of truth for architectural and design decisions.
- **Continuous Research:** Proactively search the web for better, existing, or evolving ideas in the robotics field. **Supporting Amendment:** A web-research suggestion found during phase review does not get adopted inline. It's logged to a `research_backlog.md` entry; adoption requires a separate explicit `PROCEED` at the next phase-plan review, not a mid-sub-phase pivot.

## 2. Plan & Break Down (Sub-Phase Chunking)
**Objective:** Translate high-level phase goals into actionable, approximately uniform units of work.
- **Phase Breakdown:** Read the existing phase plan, understand it, and formulate an overall implementation strategy. Break the phase down into multiple concrete sub-phases and track them in `task.md`.
- **Uniform Sizing:** Ensure the initial breakdown is balanced. No single sub-phase should contain too much work. 
- **The Sub-Phase Loop:** Each defined sub-phase will then run through its own loop of this standard process flow (Review, Implement, Execute, Document, Update). However, a sub-phase will *not* be broken down any further. The initial breakdown into sub-phases is final.

## 3. Execute & Verify
**Objective:** Build the system and prove it works under rigorous testing.
- **Execution:** Complete the tasks defined in the task tracker sequentially.
- **Scientific Verification:** Ensure every step is scientifically sound. Nothing is considered "done" until it is thoroughly verified in the MuJoCo simulation. Edge cases, physics constraints, and robotic kinematics must be explicitly validated.
- **Regression Check (Supporting Amendment):** Before producing the Verification Summary, the agent re-runs the verification scripts of all *previously approved* sub-phases in the current phase. A regression failure here blocks the gate the same as a new failure would — it gets surfaced in the Verification Summary, not silently ignored.

## 4. Document Issues (Postmortems)
**Objective:** Maintain a strict knowledge base of failures and solutions to prevent recurring bugs.
- **Action:** Any MuJoCo crashes, physics quirks, or significant roadblocks encountered during execution must be documented *immediately*.
- **Location:** Log these issues in `mujoco_crash_postmortem.md`, including the root cause and the specific fix (e.g., ABI mismatches, inertials missing on freejoints, etc.).
- **Blocker (Supporting Amendment):** A sub-phase with an unresolved entry in `mujoco_crash_postmortem.md` cannot receive a plain `PROCEED`. The Verification Summary must flag this explicitly so the human knows an `OVERRIDE-COMPLETE` (not a regular `PROCEED`) would be required to skip it.

## 4.5 Human Verification & Satisfaction Gate (HVG)
**Objective:** No sub-phase is marked complete, and no new sub-phase begins, without an explicit human-issued command. Automated "tests passed" is necessary but never sufficient.
**Trigger:** Fires automatically once Step 3 execution finishes and Step 4 postmortem logging (if any) is complete for that run.
- **Required Artifact — "Verification Summary":** The agent must produce this as a Walkthrough/Verification artifact before stopping. It must contain:
  - Success metrics over N trials (not a single run) — success rate, failure modes observed
  - Regression results confirming prior sub-phases still pass
  - Any open `mujoco_crash_postmortem.md` entries from this run, explicitly flagged if unresolved
  - A browser/sim recording or screenshot sequence of the behavior, where applicable
  - The agent's own PASS/FAIL self-assessment with reasoning
- **Blocking Rule:** After producing the Verification Summary, the agent must stop and explicitly request a decision — it must not interpret silence, partial conversation, or its own confidence as approval. Sub-phase completion is always review-driven.
- **Loop escalation (stuck verification):** If the same sub-phase fails the gate's underlying checks 3 consecutive times, the agent does not keep retrying the same approach — it auto-flags this as a candidate for `ESCALATE` in the Verification Summary, with a summary of what's been tried, rather than burning further cycles.

**Command Vocabulary:**
- `PROCEED`: Approve. Mark sub-phase ✅ in `task.md`, run Step 5, unlock Step 1 of the next sub-phase.
- `REVISE: <notes>`: Do not advance. Re-enter Step 3 only, incorporating the notes. Re-run the full HVG loop when done.
- `ROLLBACK`: Revert code/state to the last `PROCEED`-approved checkpoint.
- `HOLD`: Pause. Take no further autonomous action until a new instruction arrives.
- `ESCALATE`: Return to Step 1 — issue is likely with the phase plan or architecture. Re-open `One-Hand Robot.md` / phase plan for revision before retrying.
- `OVERRIDE-COMPLETE: <reason>`: Manual override to mark complete despite open issues. Reason is logged in `project_status.md`.

## 5. Update Status
**Objective:** Maintain an accurate, up-to-date snapshot of the project's overall progress.
- **Action:** Once a phase (or a significant segment of a phase) is fully verified in simulation, officially update `project_status.md`.
- **Details:** Reflect exactly what was achieved, mark items as `✅ COMPLETE`, and update the roadmap for the next active phase.
