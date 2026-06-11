# Automato — Agent Guide
The project contains various useful scripts, semantically structured, with CRUDL-like input and JSON-like output.

## Language
Use **English** for all code, comments, commit messages, and documentation.

## Preferred programming language
Bash for simple tasks and Python for complex. 

## Endpoints

### Repository
- **`system`** - system tools (default system is Linux like Ubuntu or Debian). 
- **`any domain`** - domain tools, like tools for specific app, web resource etc.
- **`configure/`**, **`tools/`**, **`ec
- **`examples`**- tails of legacy system. 

### Filesyste. structure
An **endpoint** is a leaf executable file in the project tree — the SINGLE script at the end of a branch that performs the actual work: `./[domain]/([subdomain]/)+<action>`.

### Naming
The endpoint script name MUST match its parent directory name (`system` do. ai. excluded from naming).
If the directory name starts with an OS prefix (e.g. `linux-`, `debian-`, `ubuntu-`),
that prefix is dropped from the script name. (`gnome-` is not an OS prefix.)

### Requirements 
Каждый endpoint — это один самостоятельный файл. 
Для скриптов на python не подключать
внешние зависимости через импорт сторонних библиотек, кроме стандартной библиотеки Python. Если нужна сторонняя библиотека — использовать `uv run` и указывать зависимости в скрипте через inline-метаданные. 

### Shebang and Executable Permissions
The script MUST have a correct shebang (`#!/bin/bash`, `#!/usr/bin/env python3`, etc.) and the executable bit MUST be set (`chmod +x`). This allows running the script directly as `./script.sh` without explicitly invoking an interpreter.

### Input 
Always match input arguments against the endpoint signature - throw an error if there is a mismatch.

### Output
Should be structured to json, except primitives responses like number, data, dtring etc. 

### Reuse
Don't duplicate code—reuse existing and appropriate endpoints. Check the list of existing endpoints in ./REGISTRY.md before starting.

### Registry
Maintain a list of existing endpoints in the REGISTRY.md file - add entries to it when creating new ones and changing existing ones. The format is one line - "name - short description". 
