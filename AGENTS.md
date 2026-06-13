# Automato — Agent Guide
The project contains various useful scripts, semantically structured, with CRUDL-like input and JSON-like output.

## Language
Use **English** for all code, comments, commit messages, and documentation.

## Preferred programming language
Python only.

## Architecture

### Endpoint
An **endpoint** is a Python module at the end of a directory tree: `./[domain]/([subdomain]/)+<action>.py`. It must be executable and self-contained — the only allowed dependency is `lib.cli.CLI`.

### CLI component (composition)
Endpoints use `CLI` as a **component**, not a base class. Each endpoint defines a `main()` function that:
1. Creates a `CLI(...)` instance with metadata (`version`, `description`, `prog`)
2. Registers command functions via `@cli.command(default=True)` (decorator)
3. Calls `cli.run()` to parse argv, dispatch, and format output

```python
def main():
    cli = CLI(version="1.0.0", prog=__file__, description="What I do")

    @cli.command(default=True)
    def show(name: str, *fields: Literal["a", "b"]) -> dict:
        result = cli.exec(["some", "command"])
        return {"key": "value"}

    cli.run()

if __name__ == "__main__":
    main()
```

The `CLI` instance provides:
- `exec(cmd, **kwargs)` — wrapper around `subprocess.run` (raises `RuntimeError` on non-zero exit, default `capture_output=True, text=True`)
- `require_output(cmd, **kwargs)` — like `exec` but also checks stdout is non-empty, returns stripped string
- `error(msg, show_usage=False)` — prints error and exits
- `print_opt(name, desc)` — prints `--name` with description aligned at column 16 (handles `\n` multipart descriptions and per-terminal-width wrapping)

Use these instead of raw `subprocess.run(...)` or manual `print` to avoid duplicating error handling and formatting logic.

### Default command
A command registered with `default=True` (or the only registered command) runs when no arguments are given.

When multiple commands are marked `default=True`, the CLI picks the best match by comparing how many positional arguments each function signature can consume from `argv`. This allows transparent dispatch: `./script.py eth0` can resolve to `show(iface="eth0")` even though `show` is not explicitly named.

### Input
Arguments are parsed from the command function signature:
- Parameters **without defaults** → positional CLI arguments
- Parameters **with defaults** → `--name` optional CLI options
- `*args` variadic parameter → collects remaining positional arguments after required ones
- Type hints → type conversion (`str`, `int`, `float`, `bool`)

### Output
Command functions **return** data structures (dict, list, str, etc.) — they never print. The CLI serialises the return value:

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
The script MUST have a correct shebang (`#!/usr/bin/env python3`) and the executable bit MUST be set (`chmod +x`). This allows running the script directly as `./script.py` without explicitly invoking an interpreter.

### Missing arguments → help
When required positional arguments are missing, the CLI shows the error followed by usage.

### Scope
An endpoint does exactly what its name implies — no extra features, commands, or modes beyond the stated purpose. Resist feature creep.

### Reuse
Don't duplicate code. Reuse existing endpoints by importing their module and calling functions directly. Check the list of existing endpoints in ./REGISTRY.md before starting.

Within an endpoint, extract shared logic into private (`_`) functions rather than duplicating code between commands.

### Registry
Maintain a list of existing endpoints in the REGISTRY.md file — add entries when creating new ones and changing existing ones. Format: one line — `name — short description`.
