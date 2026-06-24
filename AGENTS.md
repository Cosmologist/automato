# Automato — Agent Guide
The project is a collection of semanically structured Python modules.

## Common
Use **English** for literals.
Use **Python** by default.

## Python
Inline dependencies for use `uv run`.

## Code Styling
- the code should be according to the
best practices, clean, understandable and contain nothing superfluous
- follow DRY, Single Responsibility, KISS, YAGNI, don't produce extra entities
- write code according to my assignment, first discuss your options and ideas with me - the code should be commented on, especially the functions, accepted values and return results
- the code should look like written Senior developer
- code should be environment-agnostic
- clients should be concise, simple and revealing the functions, its parameters and return result must have type-hints

## Project 
- , therefore: 
- To achieve effective reusing - read and manage REGISTRY.md - enumeration existed modules and method with short description.
- The script MUST have a correct shebang (`#!/usr/bin/env python3`) and the executable bit MUST be set (`chmod +x`).

#### Tool as CLI application
If the user hasn't explicitly specified any requirements for the cli, then just do this:
```
def main():
.   CLI(<Short single-line description>, <reference to this module>).run()
```
Else read and follow CLI.md for details.

- The second, additional purpose of the tool is to use it as an application in the terminal console. The second, additional purpose of the tool is to use it as an application in the terminal console.
- To keep environment-agnostic requirement satisfaction the CLI integration possible ONLY inside `def main`.
- Using tool from cli should not affect the module code (except for def main)

### Shebang and Executable Permissions
The script MUST have a correct shebang (`#!/usr/bin/env python3`) and the executable bit MUST be set (`chmod +x`). 
This allows running the script directly as `./script.py` without explicitly invoking an interpreter.

### Scope
An endpoint does exactly what its name implies — no extra features, commands, or modes beyond the stated purpose. Resist feature creep.

### Registry
Maintain a list of existing endpoints in the REGISTRY.md file — add entries when creating new ones and changing existing ones. Format: one line — `name — short description`.
