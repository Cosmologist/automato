# Operation discovery and override resolution

Public operations are discovered through explicit package exports rather than scanning or decorators. `autocli` may read operations from both `automato` and an optional `autobridge`; when `autobridge` exposes the same operation identity, it overrides `automato` by default, with optional explicit mapping reserved for non-trivial cases, and unresolved operations fall back to `automato`.
