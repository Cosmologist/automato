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
