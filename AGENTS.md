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
- Type hints → type conversion (`str`, `int`, `float`, `bool`)

### Output
Methods **return** data structures (dict, list, str, etc.) — they never print. The base class serialises the return value:

- **With `@template` decorator** — formatted output (bare → aligned `key: value`, pattern → custom format)
- **Without `@template`** — aligned table (TSV-style with bold headers)
- Errors → plain text to stderr (no JSON)

### Styling (stderr header)
Every invocation prints a header to stderr with ANSI colors (when terminal supports it, respects `NO_COLOR`):

| Element | ANSI | Example |
|---|---|---|
| Module description | `\033[36m` (cyan) | `# Show interface details` |
| Command name in listing | `\033[1m` (bold) | `#   show    Description` |
| Full usage line | `\033[2m` (dim) | `#   interface.py show <iface> [--args]` |
| Data keys/output | `\033[1m` (bold) | `name     eno1` |

Single-command format:
```
# <module desc>
#   <prog> <cmd> [args]
```

Multi-command format:
```
# <module desc>
#
#   <cmd>    <description>
#            <prog> <cmd> [args]
#   <cmd>    <description>
#            <prog> <cmd> [args]
```

The current command's description is printed again before the output:
```
# <current command description>
<data>
```

### `@template` decorator
Format method output with a custom template:

```python
@template                              # aligned key: value
@template("{ifname:<16} {status}")     # custom format string
```

A method without `@template` gets aligned table output. Missing template keys render as empty string (no crash).

### `_arg_labels` class attribute
Override positional argument display in usage/help:

```python
class MyEndpoint(CLI):
    _arg_labels = {"iface": "iface|default"}
```

### Help
- Module docstring → script-level help text
- Class docstring → additional description
- Method docstring → command help text
- Google-style `Args:` section → per-parameter descriptions in `--help`

### Requirements
Не подключать внешние зависимости через импорт сторонних библиотек, кроме стандартной библиотеки Python. Если нужна сторонняя библиотека — использовать `uv run` и указывать зависимости в скрипте через inline-метаданные.

### Shebang and Executable Permissions
The script MUST have a correct shebang (`#!/usr/bin/env python3`) and the executable bit MUST be set (`chmod +x`). This allows running the script directly as `./script.py` without explicitly invoking an interpreter.

### Scope
An endpoint does exactly what its name implies — no extra features, commands, or modes beyond the stated purpose. Resist feature creep.

### Reuse
Don't duplicate code. Reuse existing endpoints by importing their module and calling functions directly. Check the list of existing endpoints in ./REGISTRY.md before starting.

Within an endpoint, extract shared logic into private (`_`) methods rather than duplicating commands or data-fetching between public methods.

### Registry
Maintain a list of existing endpoints in the REGISTRY.md file — add entries when creating new ones and changing existing ones. Format: one line — `name — short description`.
