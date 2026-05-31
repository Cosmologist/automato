# Automato — Agent Guide

## Language

Use **English** for all code, comments, commit messages, and documentation.

## Repository Purpose

- **`configure/`** — Self-contained scripts that apply system/application configuration tweaks (remove packages, disable services, change settings, etc.). Usually idempotent.
- **`command/`** — General-purpose utility scripts (tools, workflows, automation) that go beyond simple config tweaks.

## Implementation Placement

| Task type | Place in |
|---|---|
| System/application config tweak (remove package, disable service, set gsetting, reg patch) | `configure/` |
| General utility, tool, multi-step workflow, anything with complex arguments | `command/` |

## Language Choice

| Script size/complexity | Language |
|---|---|
| Small (few shell commands, simple conditionals) | **bash** |
| Complex logic, data processing, portability needed | **Python** (or any language that fits the task) |

## Directory Naming Convention

### `configure/` — kebab-case

Format: `[os_or_app_]component_action`

- `os_or_app_` — OS prefix when OS-specific (`linux-`, `windows-`, `macos-`) or DE/app prefix when DE-specific (`gnome-`, `kde-`). Omit when cross-platform or when the component name already implies the platform.
- `component` — system component, package, or app being configured.
- `action` — what is being done (`remove`, `disable`, `purge`, `increase`, etc.).

Examples:
- `linux-avahi-daemon-remove/` — remove avahi-daemon on Linux
- `gnome-terminal-f10/` — disable F10 menu in GNOME Terminal
- `snap-remove/` — remove snap (works on any Linux distro with snap)
- `windows-background-apps/` — disable background apps on Windows
- `apt-without-suggestions/` — configure apt to skip recommends/suggests

### `command/` — snake_case

Format: `[os_]purpose_name`

- `os_` — optional OS prefix (`linux_`, `windows_`, `macos_`). Omit when cross-platform.
- `purpose_name` — short descriptive name of what the utility does.

Examples:
- `linux_vpn_bypass/` — bypass VPN for a specific app on Linux
- `watermask/` — extract watermark from photos (cross-platform)

## Script Naming

- **`configure/`** — Always `apply.sh` (or `apply.ext` for non-bash). For Windows: `apply.reg` + optional `open.bat` + `query.bat`.
- **`command/`** — A short name (preferably one word, at most two), matching the directory purpose: `vpnbypass.sh`, `watermask.py`.

## Script Requirements

Every script MUST implement all of the following:

### 1. Summary Output (every run)

Print a brief summary of what the script does and why, plus 1–3 typical usage examples. Display this on **every invocation**, even when arguments are provided.

### 2. Interactive Argument Prompt

If the script requires arguments and none are provided, prompt the user **interactively** for the missing values before proceeding.

### 3. Input Validation

Validate all arguments before execution. Fail early with a clear message if arguments are invalid.

### 4. Pre-flight Checks

Before making any changes, verify:
- Required tools/commands exist (`which`, `command -v`, etc.)
- Prerequisite conditions are met (service is running, config exists, package is installed, etc.)
- The change is actually needed (e.g., the setting is not already applied)
- The environment supports the operation (e.g., kernel support, driver present)
- **Root/sudo rights** — check and request if needed, don't assume

If checks are complex or ambiguous, ask the user rather than guessing.

### 5. Result Summary (after execution)

Print a clear summary of what was done, including:
- What changed (or didn't change)
- Success/failure status
- Any next steps the user should take (restart, log out, etc.)
