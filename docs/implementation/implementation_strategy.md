# implementation_strategy.md

## Content



## DO NOT MODIFY BELOW THIS LINE

### Purpose of This Document

`implementation_strategy.md` defines **how the system will be built** during its initial implementation phase.

It translates the intent described in:

- `docs/setup/short_description.md`
- `README.md`
- relevant guide documents in `reference/`

into a **practical construction plan** for the repository.

This document is used by both humans and automated agents to understand:

- the selected technical approach
- the intended runtime structure
- the first implementation shape
- validation expectations
- constraints that must not be violated

---

### Relationship to Other Documents

Default Phase 1 flow:

`short_description → reference/ → README → implementation_strategy → liveplan → code`

Each stage becomes progressively more concrete.

`implementation_strategy.md` bridges **project intent and implementation**.

`project_definition.md` is not part of the default Phase 1 path. If it exists later, it may provide additional structure, but this document must remain valid without it.

---

### What Belongs in the Content Section

The content section should include:

- chosen technology stack
- intended runtime architecture approach
- first implementation shape
- validation strategy
- important constraints or forbidden shortcuts
- any implementation guidance taken from relevant `reference/` documents

The goal is to make the **first coding pass clear and well-directed**.

---

### First Implementation Expectations

The strategy should explicitly define, where applicable:

- what files or components should be created first
- what libraries or frameworks may be used
- the minimal required behaviour
- what runtime pattern is intended
- what shortcuts are not acceptable

This ensures the **initial code establishes the correct foundation**.

Later refactoring may improve structure, but should not drift away from the intended approach without the document being updated.

---

### Use of Reference Material

Relevant documents in `reference/` may contain:

- prior scripts
- operating notes
- protocol details
- examples of known-good behaviour
- constraints from existing systems

These documents may strongly inform the implementation strategy.

However:

- `short_description.md` remains the source of truth for project intent
- `README.md` remains the user-facing interpretation
- `reference/` should guide implementation, not silently redefine the project

If a reference guide conflicts with the active setup documents, the conflict should be resolved explicitly in the Content section.

---

### Relationship to Liveplan

`liveplan.md` breaks the strategy into concrete implementation steps.

Each active liveplan step should remain aligned with the strategy.

If the strategy changes significantly, the liveplan should be updated to match.

---

### Editing Rules

When editing the **Content section**:

- keep it concise and directive
- avoid speculation or brainstorming
- avoid historical notes unless they directly affect implementation
- avoid vague future-roadmap language
- avoid deep architecture discussion beyond what is needed for the first implementation

The document should describe **what will be built first and how**.

---

### Important Constraint

The strategy should **prevent architectural drift** during early coding.

If an implementation rule is important, it should be written explicitly in the strategy.

Examples:

- runtime code must live in a specific location
- reference materials must not be executed directly
- the service must remain LAN-local
- interfaces must remain stable during the first implementation

---

### Phase 1 Scope Reminder

For involved projects, the strategy should describe a **minimum working first implementation**.

This does not need to solve everything.

It should define a practical first build that proves the core concept and provides a clean foundation for later expansion.
