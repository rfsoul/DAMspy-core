# Documentation Map

## Purpose

This document provides a navigation guide for the damspy-core repository.

It is intended for both humans and AI agents to understand:

- what documentation exists
- which documents are active
- how to interpret the repository structure

---

## Repository Status

damspy-core is an existing, working repository.

It predates the ProjectX documentation structure.

The current documentation is being **backfilled** to describe the working system and guide safe future development.

Not all template documents are active or complete.

If documentation conflicts with working code, treat the code as current truth.

---

## How to Use This Map

When working in this repository:

1. Start with:
   - `README.md`
   - `docs/setup/project_definition.md`
   - `docs/implementation/implementation_strategy.md`

2. Then consult additional documents only if relevant.

3. Do not assume that all template documents exist or are fully populated.

---

## Root Files

### README.md

High-level description of the repository and how it is used.

Use this to understand what the system does and how it is run.

---

### doc_map.md

This document.

Use this to determine which documentation is relevant.

---

### reference/

Contains authoritative reference material such as:

- external interface definitions
- protocol notes
- historical or supporting material

Reference documents may strongly influence implementation.

They should not be duplicated elsewhere.

---

## docs/setup/

### short_description.md

Brief orientation for the repository.

Provides a quick understanding of what damspy-core is.

---

### project_definition.md

Defines the role and boundaries of damspy-core.

Use this to understand:

- what belongs in this repo
- what does not
- how it relates to other components

---

## docs/implementation/

Only a subset of Phase2+ documents are currently active.

---

### implementation_strategy.md

Defines how the repository should evolve from its current working state.

Use this when making changes to the system.

---

### external_interfaces.md

Describes how damspy-core interacts with external systems.

Points to authoritative interface definitions in `reference/`.

Use this when implementing integrations (e.g. rpicontrol).

---

### (Other Phase2+ Documents)

Additional Phase2+ documents may exist or be introduced over time, including:

- architecture.md
- system_invariants.md
- runbook.md
- decisions.md
- test_strategy.md

These are not required to be complete at this stage.

Only consult them if they exist and are relevant.

---

## Important Rules

- This repository is not a greenfield design.
- Do not assume all documentation is complete.
- Do not invent missing structure based on templates.
- Prefer existing working code paths over inferred architecture.
- Add documentation only when it helps prevent confusion or unsafe changes.

---

## Summary

Start with:

- README.md  
- project_definition.md  
- implementation_strategy.md  

Then expand only as needed.

This repository prioritizes **working behaviour over documentation completeness**.