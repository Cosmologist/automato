# Automato

Automato is a Python utility platform for user-environment automation. It is organized by subject domains so its capabilities remain discoverable both as a library and through external adapters.

## Language

**Automato**:
The project and primary domain library for user-environment automation on Linux.
_Avoid_: toolbox, script dump, CLI app

**Domain**:
A top-level subject area that groups related public operations.
_Avoid_: category, folder, feature set

**Operation**:
A public library capability exposed from a domain as a function.
_Avoid_: command, endpoint, handler

**Query**:
An operation that inspects state without changing the environment.
_Avoid_: getter, read command

**Command**:
An operation that changes the environment or requests a state change.
_Avoid_: action, mutation script

**Autocli**:
A generic CLI adapter engine that exposes public operations from a provider library.
_Avoid_: the library, project-specific CLI glue

**Autobridge**:
An optional project-specific provider layer that can override or extend the public operation surface exposed to Autocli.
_Avoid_: ELT, autowire, autoroute
