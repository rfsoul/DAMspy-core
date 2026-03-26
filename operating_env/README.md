# Operating Environment

## 
## TLDR

If `operating_env/.localenv` exists and contains the exact line:

DAMSPY_RUNTIME_MODE=real

then DAMspy-core is allowed to connect to real equipment.

Otherwise, it resolves to virtual mode.

## Purpose

This folder documents how DAMspy-core decides whether it is allowed to run against real equipment.

The goal is:

- safe default behavior for all normal checkouts
- no accidental real-hardware access in sandbox or developer environments
- explicit local opt-in on the rfcontrol NUC (or any other machine that is intentionally allowed to use real equipment)

This mechanism is intentionally simple.

---

## Default Behavior

DAMspy-core defaults to **virtual** mode unless a local machine override explicitly enables **real** mode.

This means that on a normal checkout, including sandbox environments, the repository should resolve to virtual mode automatically.

At the current first implementation stage:

- `real` mode is allowed to continue normally
- `virtual` mode is detected and reported


---

## Local Override File

The local machine override file is:

.localenv  
The exact contents for the real mode is

DAMSPY_RUNTIME_MODE=real