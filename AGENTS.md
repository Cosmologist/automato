# Automato — Agent Guide
The project contains various useful scripts.

## Language
Use **English** for all code, comments, commit messages, and documentation.

## Repository
- **`configure/`** — system/application config tweaks (remove packages, disable services, settings).
- **`tools/`** — general-purpose utility scripts.

# Naming
Naming: `./[configure|tools]/[os_]<purpose_name>/<script_short_name>` (snake_case)

## Preferred programming language
Language: bash for small scripts, Python for complex logic/portability.

## Script Requirements
Every script MUST implement all of the following:

### 1. Summary Output (every run)
Print a brief summary of what the script does and why, plus 1–3 typical usage examples. Display on every invocation, even when arguments are provided.

### 2. Interactive Argument Prompt
If the script requires arguments and none are provided, prompt interactively for missing values.

### 3. Input Validation
Validate all arguments before execution. Fail early with a clear message.

### 4. Pre-flight Checks
Before making changes, verify: required tools exist, prerequisites are met, change is actually needed, root/sudo rights. Ask the user if checks are ambiguous.

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

