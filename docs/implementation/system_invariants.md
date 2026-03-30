# System Invariants

## Content

This document records the non-negotiable rules that must remain true as damspy-core evolves.

These invariants exist to prevent refactors, integrations, or feature work from breaking the core role of the repository.

damspy-core is an existing working system. These invariants are written to protect real measurement usefulness, not to enforce an idealized architecture.

---

## 1. Core Role Invariant

damspy-core must remain the core measurement execution and orchestration repository.

It must continue to be the part of the DAMspy system that:

- interprets measurement configuration
- coordinates equipment and runtime behaviour
- executes measurement workflows
- produces useful outputs and artifacts

Changes must not redefine damspy-core into a general GUI application, an unrelated services container, or a purely experimental sandbox.

---

## 2. Working Measurements Come First

Preserving working measurement behaviour is more important than architectural neatness.

A change that makes the code look cleaner but risks breaking useful real-world runs is not acceptable unless there is a strong, justified reason and validation proves the behaviour is preserved.

Successful real measurement runs are a primary source of truth.

---

## 3. Configuration-Driven Execution Must Remain True

damspy-core must remain configuration-driven.

Configuration must continue to determine the selected workflow, key run parameters, and important runtime behaviour.

New features should integrate into the configuration model rather than bypassing it with scattered hard-coded behaviour.

---

## 4. Orchestration Must Stay Central

The system must retain a clear orchestration layer or entry path that coordinates a run.

The run flow must continue to follow this basic pattern:

- initiate a run
- load and interpret configuration
- prepare runtime context
- initialize required equipment or services
- execute the selected workflow
- write outputs and artifacts

This sequence may be refined, but it must not become fragmented or ambiguous.

---

## 5. Hardware / Protocol Logic Must Stay Contained

Low-level hardware or protocol-specific logic must remain contained in appropriate drivers, adapters, or control layers.

Test workflows must not become a dumping ground for:

- raw SCPI calls
- raw serial protocols
- raw HTTP integration logic
- duplicated hardware-specific workarounds

---

## 6. External Service Integrations Must Be Explicit

External services must be integrated through explicit and contained boundaries.

For example:

- damspy-rpicontrol is an external service
- damspy-core consumes it
- damspy-core does not redefine its interface
- integration should happen through a clear adapter or integration layer

External integration logic must not be smeared across unrelated parts of the codebase.

---

## 7. Test Workflows Must Express Measurement Intent

Test method / workflow code must primarily describe the measurement procedure and sequencing.

It must not gradually absorb:

- unrelated UI logic
- unrelated service orchestration
- environment-specific hacks that belong in drivers or adapters
- broad repository control concerns

Workflow code should stay focused on measurement intent.

---

## 8. Useful Outputs Must Be Preserved

A successful run must continue to produce operator-useful outputs.

This includes preserving the practical value of:

- run-specific output folders
- measurement data
- logs
- artifacts needed for comparison, review, or post-processing

Output format and structure may evolve, but changes must not casually destroy comparison value or operator usefulness.

---

## 9. Data and Metadata Must Stay Aligned

Measurement data and the metadata needed to interpret it must remain aligned.

If a run produces data, it must remain possible to understand:

- what was run
- with what configuration
- under what important runtime conditions
- where the resulting artifacts belong

Changes must not produce “mystery output” that cannot be confidently interpreted later.

---

## 10. Simulation and Live Paths Must Not Drift Meaninglessly

If the repository supports both simulation and live execution paths, they must remain intentionally related.

Simulation must not become a fake side system that teaches the wrong execution model.

Live execution must not bypass the core structure in a way that makes simulation irrelevant.

Where both paths exist, they should preserve the same broad orchestration model.

---

## 11. Safety and Physical Constraints Must Be Respected

Any code that can influence real hardware motion, instrument state, or RF behaviour must continue to respect physical and operational constraints.

This includes things such as:

- motion limits
- sequencing requirements
- settle times / timing assumptions
- safe hardware initialization and shutdown behaviour

No refactor or convenience abstraction may silently remove or bypass these protections.

---

## 12. Boundaries Between Core and Future GUI Must Hold

damspy-core must not gradually become the long-term home for richer operator UI, dashboards, or visualization-heavy interaction.

A future system such as damspy-vc may consume or sit above damspy-core, but that does not change the role of damspy-core itself.

This boundary must remain explicit.

---

## 13. Documentation Must Not Outrank Working Truth

Documentation exists to reduce confusion, not to override working reality.

If documentation and working code disagree:

- treat the working code path as the current truth
- update the documentation
- do not force the code to match stale docs without understanding why the divergence exists

This protects the repository from documentation-driven breakage.

---

## 14. Changes Must Be Justified by Real Need

Large refactors, restructures, or interface changes should be driven by demonstrated need such as:

- repeated maintenance pain
- integration pressure
- reliability issues
- clear operator problems
- real architectural blockage

Aesthetic preference alone is not enough.

---

## 15. Invariants Override Convenience

If a proposed change is convenient but violates these invariants, the invariants win unless they are deliberately revised.

If an invariant needs to change, that change should be explicit and justified rather than accidental.

---

## Completeness Note

These invariants are intentionally practical rather than exhaustive.

They should be expanded only where additional precision helps protect the real working system from confusion or unsafe change.