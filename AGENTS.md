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

### Tools
**Tool naming** - prefer *entity name* of applicable domain/subdomain.  
**Programming Language** - Python only, excluding `app/` (for applications, any suitable language is allowed).

#### Implementation common requirements
- Tool is ordinary python module, you can import it and use from python. 
- Module divides on multiple single-responsibility methods.
- Methods are environment-agnostic.
- Methods must have a comment with a short, precise and concise description.
- Methods parameters should be type-hinted and have description.
- DontRepeatYourself - avoid to code duplication across modules - reuse already logic from existed modules if possible.
- To achieve effective reusing - read and manage REGISTRY.md - enumeration existed modules and method with short description.
- The script MUST have a correct shebang (`#!/usr/bin/env python3`) and the executable bit MUST be set (`chmod +x`).

#### CLI Integration
- Tool can be used from terminal by-default.
- To keep environment-agnostic requirement satisfaction the CLI integration possible ONLY inside `def main`.
- Ordinary integration achieved with single-line `CLI(<Short single-line description>, <reference to this module>).run()`.
- Methods to expose to CLI should be visible scope and decorated as `@cli.command()`.

### CLI component
`./lib/cli.py` is an adapter between CLI and modules.

#### Methods to CLI translation scheme
- Expose only methods decorated as `@lib.cli.command()`.
- Methods translated to command modes/operations.
- Method parameters translated to mode/operation argument or options.
- Method and parameters comments, type-hints, default-values translated to corresponding methods/options.
- Errors and exceptions translated to stderr and exit code.

##### Default command
Method decorated with `@lib.cli.command(default=True)` not required explicit passing of corresponded mode/operation name.
When multiple commands are marked `default=True`, the CLI picks the best match by comparing how many positional arguments each function signature can consume from `argv`.
This allows transparent dispatch: `./script.py eth0` can resolve to `show(iface="eth0")` even though `show` is not explicitly named.

============================================================
!!!! ОСТАНОВИЛСЯ НА РУЧНОЙ ПЕРЕРАБОТКЕ ДОКУМЕНТА ЗДЕСЬ !!!!!
============================================================

##### Input
Arguments are parsed from the command function signature:
- Parameters **without defaults** → positional CLI arguments
- Parameters **with defaults** → `--name` optional CLI options
- `*args` variadic parameter → collects remaining positional arguments after required ones

##### Output
Command functions **return** data structures (dict, list, str, etc.) — they never print. The CLI serializes the return value:
- **Dict** → aligned `key: value` (bold keys)
- **List of dicts** → aligned table (bold headers)
- **Errors** → plain text to stderr (no JSON)

Data lines contain only whitespace between values — no ANSI, no borders.

Example output:
```
name     lo
status   UP
mtu      65536
ip       127.0.0.1/8
gateway  None
```

#####  `--tty` option
Control output formatting:

- `--tty` or `--tty=true` → force formatted output (table with ANSI)
- `--tty=false` or `--tty false` → force plain output (values only)
- Not specified → auto-detect: formatted in terminal, plain when piped

In plain mode (`--tty=false`), dict values are space-separated on one line.

Examples:

```bash
./script.py eth0 --tty           # force formatted even when piped
./script.py eth0 --tty=false     # force plain in terminal
./script.py eth0                 # auto: plain when piped, formatted in terminal
```

### Styling (stderr header)
Header with banner title is shown on every invocation (except `--tty=false`). Usage line only shown on error or `--help`. On success, header goes to stderr and data to stdout.

ANSI colors when terminal supports it (respects `NO_COLOR`):

| Element | ANSI | Example |
|---|---|---|---|
| Module description | `\033[36m` (cyan) | `# Show network interface info` |
| Command name in listing | `\033[1;36m` (bold cyan) | `#   show    Description` |
| Argument placeholder | `\033[32m` (green) | `<name>`, `[<fields>...]` |
| Option flag in usage | `\033[33m` (yellow) | `--help`, `--tty` |
| Full usage line | `\033[2m` (dim) | `#   interface show <iface> [--args]` |
| Data keys/output | `\033[1m` (bold) | `name     eno1` |
| Error message | `\033[31m` (red) | `Interface not found` |
| Banner title | `\033[1m` (bold) | `[▸] interface — desc 1.0.0` |

Single command (no name mentioned anywhere):
```
[▸] <name> — <desc> <version>
───────────────────────────────────────────────────
Usage: <prog> <name> [<args>...] [--help] [--tty]
───────────────────────────────────────────────────
```

Multi-command:
```
[▸] <name> — <desc> <version>
───────────────────────────────────────────────────
Usage: <prog> <command> [args...] [--help] [--tty]
───────────────────────────────────────────────────

  <cmd>    <description>
           <prog> <cmd> [<args>...]
```

### Help
- `description` parameter in CLI constructor → banner title
- Google-style `Args:` section → per-parameter descriptions in `--help`
- Single-command endpoint → `--help` shows banner + usage + ARGUMENTS + OPTIONS (no command name)
- Multi-command endpoint → `--help` shows banner + usage + COMMANDS + OPTIONS
- `--help` on explicit command (`show --help`) shows command-specific usage + ARGUMENTS + OPTIONS
- `--help` is called on partial args to show available commands
- `--help` and `--tty` descriptions use `print_opt(name, desc)` for dynamic wrapping
- Multi-line descriptions in `print_opt` use `\n` to separate segments; each segment wraps independently

### `print_opt` helper
`print_opt(name, desc)` prints a `--name` option with description aligned at column 16. Handles newline-separated segments (each on its own line) and dynamic `textwrap.wrap` per terminal width.

Example `--tty` output:
```
  --tty         - false — plain-values output for machines
                - true — decorated output for humans
                - unset — automatic selection
```

### `arg_labels` parameter
Override positional argument display in usage/help by passing `arg_labels` to CLI:

```python
cli = CLI(arg_labels={"name": "name|default", "fields": "fields"})
```

### Variadic args with Literal
Use `typing.Literal` to document valid values for variadic arguments. The CLI extracts choices automatically for display and validation:

```python
from typing import Literal

def show(name: str, *fields: Literal["a", "b", "c"]) -> dict: ...
```

Usage shows `[<fields>...]`, help shows the choices in the FIELDS section. Derive the default set from the Literal at runtime to avoid duplication:

```python
from typing import Literal, get_type_hints
from lib.cli import _literal_choices

def show(name: str, *fields: Literal["a", "b", "c"]) -> dict:
    hints = get_type_hints(show)
    choices = _literal_choices(hints.get("fields"))
    requested = set(fields) if fields else set(choices)
```

### Versioning
- Use semantic versioning with non-annotated git tags: `git tag <name>-<version>` (no `-a`)
- Each subproject within automato has its own version tag: `system-network-interface-1.0.0`
- Pass `version` to the CLI constructor in `main()`
- Tag only before push
- Push workflow:
  1. Update `version` in the endpoint's `main()`
  2. Commit the change
  3. Tag non-annotated: `git tag <module>-<version>` and `git tag automato-<version>`
  4. Push: `git push origin master --tags`

### Requirements
Не подключать внешние зависимости через импорт сторонних библиотек, кроме стандартной библиотеки Python. Если нужна сторонняя библиотека — использовать `uv run` и указывать зависимости в скрипте через inline-метаданные.

### Shebang and Executable Permissions
The script MUST have a correct shebang (`#!/usr/bin/env python3`) and the executable bit MUST be set (`chmod +x`). 
This allows running the script directly as `./script.py` without explicitly invoking an interpreter.

### Missing arguments → help
When required positional arguments are missing, the CLI shows the error followed by usage.

### Scope
An endpoint does exactly what its name implies — no extra features, commands, or modes beyond the stated purpose. Resist feature creep.

### Registry
Maintain a list of existing endpoints in the REGISTRY.md file — add entries when creating new ones and changing existing ones. Format: one line — `name — short description`.
