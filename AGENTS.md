# Automato — Agent Guide
The project contains various useful scripts, semantically structured, with CRUDL-like input and JSON-like output.

## Language
Use **English** for all code, comments, commit messages, and documentation.

## Preferred programming language
Bash for simple tasks and Python for complex. 

## Important Rules 

### Repository
- **`system`** - system tools (default system is Linux like Ubuntu or Debian). 
- **`any domain`** - domain tools, like tools for specific app, web resource etc.
- **`configure/`**, **`tools/`**, **`ec
- **`examples`**- tails of legacy system. 

### Endpoint
An **endpoint** is a leaf executable file in the project tree — the SINGLE script at the end of a branch that performs the actual work: `./[domain]/([subdomain]/)+<action>`.

### Endpoint naming
The endpoint script name MUST match its parent directory name (`system` do. ai. excluded from naming).
If the directory name starts with an OS prefix (e.g. `linux-`, `debian-`, `ubuntu-`),
that prefix is dropped from the script name. (`gnome-` is not an OS prefix.)

### Endpoint requirements 
Каждый endpoint — это один самостоятельный файл. 
Для скриптов на python не подключать
внешние зависимости через импорт сторонних библиотек, кроме стандартной библиотеки Python. Если нужна сторонняя библиотека — использовать `uv run` и указывать зависимости в скрипте через inline-метаданные. 

## Endpoint Shebang and Executable Permissions
The script MUST have a correct shebang (`#!/bin/bash`, `#!/usr/bin/env python3`, etc.) and the executable bit MUST be set (`chmod +x`). This allows running the script directly as `./script.sh` without explicitly invoking an interpreter.

### Endpoint Output
Should be structured to json, except primitives responses like number, data, dtring etc. 

### Reuse endpoint 
Don't duplicate code—reuse existing and appropriate endpoints. Check the list of existing endpoints in ./REGISTRY.md before starting.
