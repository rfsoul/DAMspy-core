# Project Definition

## Content
# Project Definition

## Content

damspy-core is the core measurement execution and orchestration repository within the DAMspy system.

It is responsible for running configured RF / EMC / chamber-style measurement workflows by coordinating lab equipment, motion systems, and test logic, and producing useful output data for analysis and comparison.

This repository is already functional and in active use.  
This document reflects the current role of the system and its intended boundaries as it continues to evolve.

---

## Current Role

damspy-core provides:

- the execution path for measurement runs
- coordination of equipment and runtime behaviour
- implementation of test workflows
- generation of measurement outputs and artifacts

It is the system that turns configuration and test intent into actual measurement execution.

---

## System Context

damspy-core exists as part of a broader system of related components.

At present, relevant components include:

- damspy-core — execution and orchestration
- damspy-rpicontrol — external control service for RXCC-related behaviour
- future: damspy-vc — potential GUI / operator-facing control and visualization layer

These components are expected to interact but remain logically separate.

---

## Boundaries

damspy-core should remain focused on:

- measurement orchestration
- equipment coordination
- test execution
- output generation

It should not evolve into:

- a full GUI or operator-facing application
- a general-purpose control interface
- a container for unrelated services or features

External services and UI concerns should be integrated through clear interfaces rather than absorbed into the core.

---

## Relationship to rpicontrol

damspy-core will integrate with damspy-rpicontrol as an external service.

This integration should:

- use the defined external interface (see reference/)
- remain contained within a clear adapter or integration layer
- avoid spreading service-specific logic throughout test methods

damspy-core consumes this service and does not define its interface.

---

## Relationship to Future GUI (damspy-vc)

Future operator-facing control, visualization, or interactive workflows are expected to live outside this repository.

damspy-core should provide:

- reliable execution
- clear outputs
- predictable behaviour

Other components may build on top of this.

---

## Evolution Direction

The repository will continue to evolve based on real usage and requirements.

Near-term focus:

- safe integration of external control (rpicontrol)
- maintaining and improving reliability of measurement workflows
- clarifying structure without breaking working behaviour

Longer-term direction may include:

- clearer separation of concerns between core execution and user-facing systems
- improved modularity where justified by real needs

Large architectural changes should be driven by demonstrated limitations, not aesthetic preference.

---

## Non-Goals (for now)

The following are not current goals for damspy-core:

- complete architectural redesign
- full system generalization
- replacing working patterns solely for consistency or style
- embedding GUI or rich user interaction directly into core

---

## Completeness Note

This document reflects the current understanding of damspy-core as an operational system.

It is not a complete or final specification.  
It should be updated as the system evolves and as boundaries become clearer through use.


---

## Editing Guidelines (Do Not Modify Below This Line)

This document describes the problem the system solves.

It intentionally avoids implementation details.

Architecture and technology choices are described elsewhere.

---

# Problem

Describe the real-world problem the system solves.

Focus on the user's perspective.

---

# Target User

Describe who the system is for.

Examples:

• contractors  
• developers  
• Etsy sellers  
• RF engineers  

---

# Core Capability

Describe the primary capability of the system.

The system should ideally do **one thing extremely well**.

---

# System Scope

Define the **boundary of responsibility** for the system.

This section clarifies what the system **includes** and what it **intentionally excludes**.

### Included

Describe the responsibilities the system **does perform**.

Examples:

• generating invoices from user input  
• storing collected data  
• triggering notifications  

### Excluded

Describe capabilities that are **explicitly outside the scope** of the system.

Examples:

• enterprise billing systems  
• full accounting software  
• user account management  
• large-scale analytics  

Items listed here may appear in `futuredirections.md` but are not part of the current system.

---

# Inputs

What information enters the system?

Examples:

• emails  
• API requests  
• files  
• sensor readings  

---

# Outputs

What does the system produce?

Examples:

• invoices  
• reports  
• alerts  
• stored data  

---

# Non-Goals

What the system explicitly does **not** attempt to do.

This prevents scope creep.

---

# Success Criteria

How we know the system is working.

Examples:

• an invoice is generated within 10 seconds  
• data is stored reliably  
• users receive expected output  

---

# Constraints

Known limitations.

Examples:

• must run on Vercel  
• must use Gmail API  
• must run on Raspberry Pi  
• must operate without user accounts
