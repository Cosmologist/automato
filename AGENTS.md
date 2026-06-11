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
- JSON output of return values (pretty-printed with indentation)
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
Methods **return** data structures (dict, list, str, etc.) — they never print. The base class serialises the return value as pretty-printed JSON.

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
