# Library-first layered architecture

Automato is a library-first Python project. Its domain logic lives in `automato`, remains unaware of CLI and other delivery adapters, and exposes public operations as domain-level functions. `autocli` is a separate generic CLI adapter engine, and `autobridge` is an optional project-specific layer between them when CLI-facing composition or overrides are needed.
