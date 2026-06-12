# Automato — Agent Guide
The project contains various useful scripts, semantically structured, with CRUDL-like input and JSON-like output.

## Language
Use **English** for all code, comments, commit messages, and documentation.

## Preferred programming language
Python only.

## Architecture

### Endpoint
An **endpoint** is a Python module at the end of a directory tree: `./[domain]/([subdomain]/)+<action>.py`. It must be executable and self-contained — the only allowed dependency is the base CLI class from `lib/cli.py`.

### Base class
Every endpoint inherits from `lib.cli.CLI`. The base class provides:
- Method-based command routing (each public method = one CLI command)
- Automatic argument parsing from method signatures (type hints, defaults)
- Help generation from docstrings (module → script help, method → command help)
- `_exec(cmd, **kwargs)` — wrapper around `subprocess.run` with error handling (raises `RuntimeError` on non-zero exit, default `capture_output=True, text=True`)

Use `self._exec(...)` instead of raw `subprocess.run(...)` to avoid duplicating error handling.

### Default command
A method marked with `@default` (or the only public method) runs when no arguments are given.

When multiple methods are marked `@default`, the base class picks the best match by comparing how many positional arguments the method signature can consume from `argv`. This allows transparent dispatch: `./script.py eth0` can resolve to `show(iface="eth0")` even though `show` is not explicitly named.

### Input
Arguments are parsed from the method signature:
- Parameters **without defaults** → positional CLI arguments
- Parameters **with defaults** → `--name` optional CLI options
- `*args` variadic parameter → collects remaining positional arguments after required ones
- Type hints → type conversion (`str`, `int`, `float`, `bool`)

### Output
Methods **return** data structures (dict, list, str, etc.) — they never print. The base class serialises the return value:

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

### `--tty` option
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
- Module docstring → script-level help text (banner description)
- Google-style `Args:` section → per-parameter descriptions in `--help`
- Single-command endpoint → `--help` shows banner + usage + ARGUMENTS + OPTIONS (no command name)
- Multi-command endpoint → `--help` shows banner + usage + COMMANDS + OPTIONS
- `--help` on explicit command (`show --help`) shows command-specific usage + ARGUMENTS + OPTIONS
- `--help` is called on partial args to show available commands
- `--help` and `--tty` descriptions use `_print_opt(name, desc)` for dynamic wrapping
- Multi-line descriptions in `_print_opt` use `\n` to separate segments; each segment wraps independently

### `_print_opt` helper
`_print_opt(name, desc)` prints a `--name` option with description aligned at column 16. Handles newline-separated segments (each on its own line) and dynamic `textwrap.wrap` per terminal width.

Example `--tty` output:
```
  --tty         - false — plain-values output for machines
                - true — decorated output for humans
                - unset — automatic selection
```

### `_arg_labels` class attribute
Override positional argument display in usage/help:

```python
class MyEndpoint(CLI):
    _arg_labels = {"name": "name|default", "fields": "fields"}
```

### Variadic args with Literal
Use `typing.Literal` to document valid values for variadic arguments. The base class extracts choices automatically for display and validation:

```python
from typing import Literal

def show(self, name: str, *fields: Literal["a", "b", "c"]) -> dict: ...
```

Usage shows `[<fields>...]`, help shows the choices in the FIELDS section.

### Versioning
- Use semantic versioning with non-annotated git tags: `git tag <name>-<version>` (no `-a`)
- Each subproject within automato has its own version tag: `system-network-interface-1.0.0`
- Set `_version` and `_name` class attributes in each endpoint
- Tag only before push

### Requirements
Не подключать внешние зависимости через импорт сторонних библиотек, кроме стандартной библиотеки Python. Если нужна сторонняя библиотека — использовать `uv run` и указывать зависимости в скрипте через inline-метаданные.

### Shebang and Executable Permissions
The script MUST have a correct shebang (`#!/usr/bin/env python3`) and the executable bit MUST be set (`chmod +x`). This allows running the script directly as `./script.py` without explicitly invoking an interpreter.

### Missing arguments → help
When required positional arguments are missing, the CLI shows the error followed by usage.

### Scope
An endpoint does exactly what its name implies — no extra features, commands, or modes beyond the stated purpose. Resist feature creep.

### Reuse
Don't duplicate code. Reuse existing endpoints by importing their module and calling functions directly. Check the list of existing endpoints in ./REGISTRY.md before starting.

Within an endpoint, extract shared logic into private (`_`) methods rather than duplicating commands or data-fetching between public methods.

### Registry
Maintain a list of existing endpoints in the REGISTRY.md file — add entries when creating new ones and changing existing ones. Format: one line — `name — short description`.
