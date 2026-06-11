# Automato — Agent Guide
The project contains various useful scripts.

## Language
Use **English** for all code, comments, commit messages, and documentation.

## Императивы (обязательные правила)

### Язык по умолчанию — Python
Скрипты писать на Python, если только задача не тривиальна (одна-две команды оболочки).
Исключение: configure-скрипты, которые работают с системными конфигами — для них bash допустим.

### Один файл = один скрипт
Каждый endpoint — это один самостоятельный файл. Внешние зависимости не подключать через импорт сторонних библиотек, кроме стандартной библиотеки Python. Если нужна сторонняя библиотека — использовать `uv run` (см. ниже).

### Управление зависимостями через `uv run`
Если скрипту нужна сторонняя библиотека (`requests`, `pyyaml` и т.п.):
- Не устанавливать её глобально.
- Не создавать `requirements.txt` / `pyproject.toml`.
- Использовать `uv run` с аргументом `--with`: `#!/usr/bin/env uv run --with requests --with pyyaml`
  Это позволяет выполнить скрипт с временно установленными зависимостями без изменения системы.

### `lib/infrastructure.py` — переиспользуемые утилиты
В корне проекта существует `lib/infrastructure.py`. Перед написанием любого вспомогательного кода внутри скрипта агент ОБЯЗАН:
1. Проверить, нет ли в `lib/infrastructure.py` уже готового функционала для задачи.
2. Если функционал есть — использовать его.
3. Если функционала нет, но он явно **переиспользуемый** (понадобится в других скриптах) — предлагать добавить его в `lib/infrastructure.py` (и только после согласования с пользователем).
4. Если функционал уникален для конкретного скрипта — писать inline внутри скрипта.

## Repository
- **`configure/`** — system/application config tweaks (remove packages, disable services, settings).
- **`tools/`** — general-purpose utility scripts.

## Endpoint
An **endpoint** is a leaf executable file in the project tree — the script at the
end of a branch that performs the actual work: `./[category]/[purpose_name]/<script_name>`.

# Naming
Naming: `./[configure|tools]/[os_]<purpose_name>/<script_short_name>` (kebab-case)

## Endpoint naming
The endpoint script name MUST match its parent directory name.
If the directory name starts with an OS prefix (e.g. `linux-`, `debian-`, `ubuntu-`),
that prefix is dropped from the script name. (`gnome-` is not an OS prefix.)

## Preferred programming language
Language: Python (см. императивы выше).

## Script Requirements
Every script MUST implement all of the following:

### 0. Shebang and Executable Permissions
The script MUST have a correct shebang (`#!/bin/bash`, `#!/usr/bin/env python3`, etc.) and the executable bit MUST be set (`chmod +x`). This allows running the script directly as `./script.sh` without explicitly invoking an interpreter.

### 1. Summary Output (every run)
Print a brief summary of what the script does and why, plus 1–3 typical usage examples. Display on every invocation, even when arguments are provided.

### 2. Interactive Argument Prompt
If the script requires arguments and none are provided, prompt interactively for missing values.
Present a numbered list of options and ask the user to enter the corresponding number(s), not free-form text.

### 3. Input Validation
Validate all arguments before execution. Fail early with a clear message.

### 4. Pre-flight Checks
Before making changes, verify: required tools exist, prerequisites are met, change is actually needed, root/sudo rights. Ask the user if checks are ambiguous.
Pre-flight checks MUST run **before** any interactive prompts — users should not waste time answering questions only to fail on sudo or missing tools.

### 5. In-process output
- The output should look like a step-by-step instruction if the user were to ask for one.
- Each action performed by the script to implement the main functionality should be duplicated on the screen with the actual values ​​substituted.
- Each action should have a description (as if it were an instruction) (brief) describing what it does in the context of the values ​​used.
- During execution, every change must be printed with a human-readable description of what is being done, followed by the exact files/keys changed:

#### 5.1 In-process output changes format
- `${GREEN}+${NC} path → value` — for additions (files created, entries added, rules inserted)
- `${RED}-${NC} path → value` — for removals
- `${GREEN}→${NC} key  old → new` — for modifications (sysctl, config values)
- `${YELLOW}skip${NC} reason` — when skipping an operation
- `${GREEN}+${NC}` / `${RED}-${NC}` use ONLY for actual file diffs (contents added/removed from a file). Do NOT use for commands or descriptions.
- `${GREEN}→${NC}` use ONLY for value change lines (key: old → new).

### 6. Do not suggest manual commands — implement instead
Never output commands for the user to copy-paste. If a follow-up action might be needed (making config persistent, restoring defaults, verifying), implement it as a script argument (`--persist`, `--restore`, `--verify`, etc.) or offer to do it interactively. The script should be self-contained.

