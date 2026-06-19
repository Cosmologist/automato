# CLI component
`./lib/cli.py` is an automatic configurable adapter between CLI and modules.

## CLI to Method Scheme
- Methods translated to command modes/operations.
- Method parameters translated to mode/operation argument or options.
- Method and parameters comments, type-hints, default-values translated to corresponding methods/options.
- Errors and exceptions translated to stderr and exit code.

## CLI Input Arguments

### Input
Arguments are parsed from the command function signature:
- Parameters **without defaults** → positional CLI arguments
- Parameters **with defaults** → `--name` optional CLI options
- `*args` variadic parameter → collects remaining positional arguments after required ones
- If method argument require structure (list or dist) - CLI occurs this structure in json format then convert it from string to native structure. also, for convenience root parentheses in json may be ommited (example - "1,2,3" === ["1", "2", "3"], if method_arg[type]==list then input_value="[" + input_value + "]", same for dict)

### Default command
- You can pass methods names to use by defaults command mode to lib.CLI constructor.
- When multiple commands are marked as default, the CLI picks the best match by comparing how many positional arguments each function signature can consume from `argv`.
This allows transparent dispatch: `./script.py eth0` can resolve to `show(iface="eth0")` even though `show` is not explicitly named.

##### Output
Command functions **return** data structures (dict, list, str, etc.) — they never print. The CLI serializes the return value:
- **Dict** → aligned `key: value` (bold keys)
- **List of dicts** as table with border=1
- **Errors** → plain text to stderr (no JSON)

Data lines contain only whitespace between values — no ANSI, no borders.

Example output:
```
name lo
mtu  65536
...
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
| Module description | `\033[36m` (cyan) | `# Show network info` |
| Command name in listing | `\033[1;36m` (bold cyan) | `#   show    Description` |
| Argument placeholder | `\033[32m` (green) | `<name>`, `[<fields>...]` |
| Option flag in usage | `\033[33m` (yellow) | `--help`, `--tty` |
| Full usage line | `\033[2m` (dim) | `#   interface show <iface> [--args]` |
| Data keys/output | `\033[1m` (bold) | `name     eno1` |
| Error message | `\033[31m` (red) | `Interface not found` |
| Banner title | `\033[1m` (bold) | `[▸] interface — desc` |

Example:
```
[<any suitable icon 1 char>] <name> — <desc>
───────────────────────────────────────────────────
Usage: <prog> <command1> [args...] [--help] [--tty]
.      <prog> <command2> [args...] [--help] [--tty]
───────────────────────────────────────────────────

  <cmd>    <description>
           <prog> <cmd> [<args>...]
```
