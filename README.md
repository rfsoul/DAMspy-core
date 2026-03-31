# README.md

## Content
# damspy-core

## Overview

damspy-core is the operational core repository for DAMspy measurement execution.

It runs configured RF / EMC / chamber-style measurement workflows by coordinating instruments, motion systems, test logic, and output generation. The repository is already in active use and produces useful measurement results.

This repository predates the current ProjectX documentation structure. The active documentation is being backfilled to describe the working system and support safe future development. Not every template document is fully populated yet.

## What this repo does

damspy-core is responsible for the core execution path of a measurement run.

At a high level it:

- loads configuration for a selected test or test group
- initializes the required equipment and runtime context
- executes the configured measurement workflow
- records outputs, logs, and other run artifacts
- supports analysis or post-processing steps where applicable

The repo is intended to remain focused on measurement orchestration and execution.

## Typical flow

A typical use of damspy-core is:

1. select or prepare the required configuration using the yaml files.
2. run the measurement entrypoint using run.py
3. DAMspy loads the required equipment and test settings
4. the selected workflow executes
5. outputs are written to the run folder for later inspection and comparison

Exact run shapes vary depending on the configured test group, equipment, and measurement purpose.

## Repository structure

The exact code layout may continue to evolve, but the main areas of the repository are:

- `src/` — operational codebase, including the current execution path and supporting modules
- `config/` — runtime and test configuration
- `reference/` — high-authority reference material, interface notes, and external guidance
- `docs/` — ProjectX-style backfilled documentation for the current repo

Where older project files have been moved to fit the current repository structure, the code should be treated as the current truth.

## Configuration

damspy-core is configuration-driven.

Configuration determines things such as:

- which test or test group to run
- equipment/runtime settings
- measurement parameters
- output behaviour

Configuration should be kept aligned with the real lab environment and current operating practice.

## Running damspy-core

damspy-core is intended to be run using the repository’s current configured execution path.

Use the real repo entrypoints and current configuration files rather than assuming old examples or template flows are still authoritative.

If the documentation and code disagree, treat the code path currently used in successful runs as authoritative and update the docs.

## Outputs

A successful run produces operator-useful measurement outputs and supporting artifacts such as logs, data files, and run-specific output folders.

The exact output structure depends on the workflow being run, but preserving useful run outputs and comparison value is more important than cosmetic refactoring.

## DAMSpy ecosystem

DAMspy-core is the measurement execution/orchestration repository within the wider DAMspy ecosystem.

Related repositories are expected to include:

- **damspy-core** — runs configured measurement workflows, coordinates equipment, and produces run outputs
- **damspy-rpicontrol** — provides LAN-accessible HTTP/JSON control for RXCC-related hardware hosted outside the main NUC process
- **damspy-vc** — consumes runtime state from damspy-core and presents operator-focused visualisation views such as an internal desk view and a phone-friendly view
- **damspy.com** — may later provide a simple external-facing view of selected published DAMspy status artefacts

Within this ecosystem, damspy-core remains focused on measurement execution and run truth.

Where runtime monitoring or operator visualisation is needed, damspy-core is expected to expose its current state in a machine-readable form (for example WOYM-style JSON), while presentation concerns live in adjacent repositories rather than growing permanently inside damspy-core.

## Boundaries

damspy-core is the core execution/orchestration repo.

It should not gradually become the long-term home for every UI or operator-control concern.

Near-term development may integrate damspy-rpicontrol for external RXCC-related control.

Longer-term richer operator GUI/control concerns are expected to live outside this repo, likely in damspy-vc, while damspy-core remains focused on measurement execution.



## Related material

- `reference/` contains technical truth and interface guidance that may strongly influence implementation
- future or adjacent repos such as `damspy-rpicontrol` and `damspy-vc` should be treated as separate concerns unless explicitly integrated

## Documentation note

These docs are intended to prevent misunderstanding of the current working repo.

They do not attempt to present damspy-core as a greenfield design, and they should not be read as proof that every part of the system has already been restructured into its final form.


---

## Editing Guidelines (Do Not Modify Below This Line)

This document describes the project from the perspective of a **user, operator, or first-time repository reader**.

It should explain:

- what the system is
- what it broadly does
- why it exists
- who it is for, if that is known
- the general workflow of use, if that is known

Keep the README:

- clear
- practical
- easy to scan
- aligned with `docs/setup/short_description.md`

Use the README as a **usability and interpretation check** for the project idea.

It should help confirm that the intended project has been understood correctly before implementation moves too far.

Avoid including:

- low-level architecture
- detailed implementation decisions
- deep engineering discussion
- speculative future features
- internal planning detail better suited to implementation docs

The README should describe the project in a way that is useful to someone opening the repository for the first time.
