# Short Description

## Content


damspy-core is the operational core repository for DAMspy measurement execution.

It runs configured RF / EMC / chamber-style test workflows by coordinating lab equipment, motion systems, test methods, and output generation. The repository is already functional and produces useful measurement results in real lab use.

This repository predates the ProjectX documentation structure. The current documentation is being backfilled to describe the working system and guide safe future development. It should not be interpreted as a greenfield design or a fully re-architected system.

Near-term development includes integration with damspy-rpicontrol for external RXCC-related control. Longer-term, richer GUI and operator-control concerns are expected to live outside this repo (e.g. damspy-vc), while damspy-core remains focused on measurement orchestration and execution.

Current guidance:

- prefer incremental improvement over full rewrites
- preserve existing working measurement behaviour
- keep hardware and external service integrations explicit and contained
- do not assume all ProjectX template documents are active or complete
- if documentation conflicts with working code, treat the code as current truth and update the docs accordingly

---

## Editing Guidelines (Do Not Modify Below This Line)

This document contains the **original idea for the project**.

Capture the intended project in a concise but specific form.

This should clearly describe:
- what the project is
- what it does
- why it exists
- any major constraints or fixed choices already known at project start

Include specific implementation or interface choices when they are already intentional and important to the project shape.

If proof-of-concept scripts or loose experimental code already exist, extract any durable behavioural or protocol knowledge from them into markdown guides in `reference/`. Remove temporary executable POC code from the repo unless it is intentionally being promoted into production-owned implementation.