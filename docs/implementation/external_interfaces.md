# External Interfaces

## Content


This document describes how damspy-core interacts with external systems.

It records **what external interfaces exist and how damspy-core relates to them**.  
It does not redefine those interfaces.

Authoritative interface definitions, where available, live in the `reference/` folder.

---

## Overview

damspy-core interacts with a combination of:

- laboratory equipment (via drivers or control layers)
- external control services (e.g. rpicontrol)
- file system outputs and artifacts

These interactions are part of normal measurement execution.

---

## rpicontrol (RXCC Control Service)

damspy-core will integrate with damspy-rpicontrol as an external HTTP-based control service.

This service is used to control RXCC-related behaviour during measurement workflows.

### Interface definition

The authoritative API contract for `damspy-rpicontrol` lives in `reference/`, alongside the service-specific quickstart and behaviour notes. `damspy-core` consumes that contract and must not redefine or partially duplicate it here.


### Usage within damspy-core

Integration should follow these rules:

- external calls should be made through a clearly defined adapter or integration layer
- test methods should not directly issue raw HTTP requests
- sequencing and timing requirements must be respected
- integration must be validated against real measurement runs

### Current status

Integration is planned / in progress.

This document records intended usage and constraints.  
Implementation details may evolve as integration proceeds.

---

## Laboratory Equipment

damspy-core interacts with lab equipment through its existing codebase.

This includes instruments, motion systems, and other hardware required for measurement workflows.

### Interface definition

These interfaces are defined implicitly by:

- existing driver implementations
- instrument communication protocols (e.g. SCPI or vendor-specific APIs)
- working code paths in the repository

Where additional reference material exists, it should be placed in `reference/`.

### Usage within damspy-core

- equipment interaction should remain encapsulated in appropriate layers
- test logic should not become tightly coupled to low-level communication details
- changes should preserve working behaviour and known-good measurement flows

---

## File System Outputs

damspy-core produces outputs as part of normal operation.

These include:

- measurement data
- logs
- run-specific output folders
- derived or post-processed artifacts

### Interface definition

The file system structure is defined by the current working implementation.

There is no fully formalized specification at this time.

### Usage within damspy-core

- output structure should remain stable unless there is a clear reason to change it
- outputs should remain useful for operators and comparison workflows
- changes to output behaviour should be validated against real usage

---

## Future Interfaces

Additional interfaces may be introduced as the system evolves.

Examples may include:

- integration with visualization or control layers (e.g. damspy-vc)
- additional external services
- expanded automation or scheduling systems

These should be:

- explicitly documented here when they become relevant
- integrated through clear boundaries
- not introduced implicitly or scattered throughout the codebase

---

## Completeness Note

This document records the current understanding of external interactions.

It is not a complete specification of all interfaces.  
It should be expanded only where it helps guide safe development and integration.






