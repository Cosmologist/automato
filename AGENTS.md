# Automato — Agent Guide
The project contains various useful, semantically structured and ready to embed (via pipes or code) tools.

## Common rules
**Language** - use **English** for all code, comments, commit messages, and documentation.

## Project rules

### Filesystem Structure
- `<applicable-domain>/<tool>` - if applicable domain contains only this one tool, example `amneziawg\client`.
- `<applicable-domain>/<applicable-subdomin>/<tool>` - if applicable domain contains only this one tool, example `system/network/interface`.

**Exclusions**:
* `app/` is a sandbox for application prototypes (specialized application tasks).
* `configure/`, `examples/`, `tools/` - legacy, ignore them.
* `lib/` - for internal use, for boilerplate's, utils, wrappers etc.

### Tool Rules
- **Name** - prefer *entity name* of applicable domain/subdomain.  
- **Programming Language** - Python only, excluding `app/` (for applications, any suitable language is allowed)
- The tool is a ordinary module written in Python, sharpened for reusing - this is its main and most important purpose, therefore:
- the code should be according to the best practices, clean, understandable and contain nothing superfluous
- follow dry, single responsibility, Kiss, don't produce extra entities, don't do premature optimization
- write code according to my assignment, first discuss your options and ideas with me - the code should be commented on, especially the functions, accepted values and return results
- the code should look like written Senior developer
- code should not be aware of the environment such as the operating system where it is started (cli, gui - comments should be concise, simple and revealing the functions, its parameters and return result must have type-hints
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

### Requirements
Не подключать внешние зависимости через импорт сторонних библиотек, кроме стандартной библиотеки Python. Если нужна сторонняя библиотека — использовать `uv run` и указывать зависимости в скрипте через inline-метаданные.

### Shebang and Executable Permissions
The script MUST have a correct shebang (`#!/usr/bin/env python3`) and the executable bit MUST be set (`chmod +x`). 
This allows running the script directly as `./script.py` without explicitly invoking an interpreter.

### Scope
An endpoint does exactly what its name implies — no extra features, commands, or modes beyond the stated purpose. Resist feature creep.

### Registry
Maintain a list of existing endpoints in the REGISTRY.md file — add entries when creating new ones and changing existing ones. Format: one line — `name — short description`.
