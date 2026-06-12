#!/usr/bin/env python3
from __future__ import annotations

import inspect
import json
from pathlib import Path
import re
import subprocess
import sys
import textwrap
from typing import Any, get_type_hints


def default(func):
    func._cli_default = True
    return func


def template(pattern=None):
    if callable(pattern):
        pattern._cli_template = True
        return pattern

    def decorator(func):
        func._cli_template = pattern if pattern else True
        return func

    return decorator


class CLI:
    @classmethod
    def run(cls):
        instance = cls()
        argv = sys.argv[1:]

        instance._raw_mode = "--raw" in argv
        argv = [a for a in argv if a != "--raw"]

        instance._print_header()

        commands = instance._get_commands()

        if argv and argv[0] in ("--help", "-h"):
            instance._help(commands)
            return

        if not argv:
            instance._run_best_default(commands, argv)
            return

        cmd = argv[0]
        method = getattr(instance, cmd, None)
        cmd_names = [n for n, _ in commands]

        if method and cmd in cmd_names:
            instance._execute(method, argv[1:])
        else:
            instance._run_best_default(commands, argv)

    # -- introspection --

    def _get_commands(self):
        return [
            (n, m)
            for n, m in inspect.getmembers(self, inspect.ismethod)
            if not n.startswith("_")
            and m.__func__.__qualname__.startswith(self.__class__.__qualname__)
        ]

    def _get_default(self, commands):
        for name, method in commands:
            if getattr(method.__func__, "_cli_default", False):
                return name, method
        return commands[0] if commands else None

    def _run_best_default(self, commands, argv):
        defaults = [
            (n, m)
            for n, m in commands
            if getattr(m.__func__, "_cli_default", False)
        ] or commands[:1]

        best = None
        best_score = -1
        for name, method in defaults:
            sig = inspect.signature(method)
            pos_count = len(
                [
                    p
                    for p in sig.parameters.values()
                    if p.name != "self" and p.default is inspect.Parameter.empty
                ]
            )
            score = min(len(argv), pos_count)
            if score > best_score:
                best_score = score
                best = (name, method)

        if best:
            self._execute(best[1], argv)
        else:
            self._help(commands)

    # -- execution --

    def _print_header(self):
        module = sys.modules.get(self.__class__.__module__)
        prog = Path(module.__file__).name if module else sys.argv[0]
        desc = module.__doc__.strip() if module and module.__doc__ else ""

        print(f"# {desc}", file=sys.stderr)

        commands = self._get_commands()

        if len(commands) == 1:
            name, method = commands[0]
            args = " ".join(
                f"<{p.name}>" if p.default is inspect.Parameter.empty else f"[--{p.name.replace('_', '-')}]"
                for p in inspect.signature(method).parameters.values()
                if p.name != "self"
            )
            print(f"# Usage: {prog} {name} {args}".rstrip(), file=sys.stderr)
        else:
            print("#", file=sys.stderr)
            for name, method in commands:
                doc = method.__doc__.strip().split("\n")[0] if method.__doc__ else ""
                args = " ".join(
                    f"<{p.name}>" if p.default is inspect.Parameter.empty else f"[--{p.name.replace('_', '-')}]"
                    for p in inspect.signature(method).parameters.values()
                    if p.name != "self"
                )
                usage = f"{prog} {name} {args}".rstrip()
                print(f"# {name} — {doc}", file=sys.stderr)
                print(
                    textwrap.fill(usage, width=72, initial_indent="#     ", subsequent_indent="#     "),
                    file=sys.stderr,
                )

    def _execute(self, method, argv):
        sig = inspect.signature(method)
        hints = get_type_hints(method)
        params = [p for p in sig.parameters.values() if p.name != "self"]

        positional = [p for p in params if p.default is inspect.Parameter.empty]
        optional = [p for p in params if p.default is not inspect.Parameter.empty]

        if argv and argv[0] in ("--help", "-h"):
            self._command_help(method, positional, optional)
            return

        pos_values = []
        i = 0
        while i < len(argv) and not argv[i].startswith("--"):
            pos_values.append(argv[i])
            i += 1

        if len(pos_values) > len(positional) + len(optional):
            self._error(f"Too many arguments for '{method.__name__}'")

        kwargs = {}
        while i < len(argv):
            arg = argv[i]
            if arg.startswith("--"):
                name = arg[2:].replace("-", "_")
                matching = [p for p in optional if p.name == name]
                if not matching:
                    self._error(f"Unknown option: {arg}")
                p = matching[0]
                t = hints.get(p.name, str)
                if t == bool:
                    kwargs[name] = True
                else:
                    if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                        self._error(f"Option '{arg}' requires a value")
                    i += 1
                    kwargs[name] = self._convert(argv[i], t)
            i += 1

        call_args = {}
        for idx, p in enumerate(positional):
            if idx < len(pos_values):
                call_args[p.name] = self._convert(
                    pos_values[idx], hints.get(p.name, str)
                )
            else:
                self._error(f"Missing required argument: '{p.name}'")

        overflow = pos_values[len(positional):]
        for idx, p in enumerate(optional):
            if idx < len(overflow):
                call_args[p.name] = self._convert(
                    overflow[idx], hints.get(p.name, str)
                )
            elif p.name in kwargs:
                call_args[p.name] = kwargs[p.name]
            else:
                call_args[p.name] = p.default

        try:
            result = method(**call_args)
        except Exception as e:
            self._error(str(e))
            return

        if result is not None:
            self._output(result, method)

    def _output(self, result, method):
        if self._raw_mode:
            print(json.dumps(result, indent=2, default=str))
            return

        tmpl = getattr(method.__func__, "_cli_template", None)
        if not tmpl:
            print(json.dumps(result, indent=2, default=str))
            return

        if isinstance(result, str):
            print(result)
            return

        class _Missing(dict):
            def __missing__(self, k):
                return ""

        if isinstance(result, dict):
            if tmpl is True:
                if result:
                    pad = max(len(k) for k in result) + 2
                    for k, v in result.items():
                        print(f"{k:{pad}}{v}")
            else:
                print(tmpl.format_map(_Missing(result)))
        elif isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and tmpl is not True:
                    print(tmpl.format_map(_Missing(item)))
                else:
                    print(item)
        else:
            print(result)

    def _convert(self, value: str, target: type) -> Any:
        if target == bool:
            return True
        if target == int:
            return int(value)
        if target == float:
            return float(value)
        return value

    def _exec(self, cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        kwargs.setdefault("capture_output", True)
        kwargs.setdefault("text", True)
        result = subprocess.run(cmd, **kwargs)
        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(stderr or f"Command failed: {' '.join(cmd)}")
        return result

    def _error(self, msg: str):
        print(json.dumps({"error": msg}))
        sys.exit(1)

    # -- help --

    def _help(self, commands):
        module = sys.modules.get(self.__class__.__module__)
        prog = module.__file__ if module else sys.argv[0]

        desc_parts = []
        if module and module.__doc__:
            desc_parts.append(module.__doc__.strip())
        if self.__class__.__doc__:
            desc_parts.append(self.__class__.__doc__.strip())

        default_names = {
            n
            for n, m in commands
            if getattr(m.__func__, "_cli_default", False)
        }

        print(f"Usage: {prog} [--raw] [command] [args...]", file=sys.stderr)
        if desc_parts:
            print(file=sys.stderr)
            for d in desc_parts:
                print(d, file=sys.stderr)
        if commands:
            print(file=sys.stderr)
            print("Commands:", file=sys.stderr)
            for name, method in commands:
                doc = method.__doc__
                line = doc.strip().split("\n")[0] if doc else ""
                mark = " (default)" if name in default_names else ""
                print(f"  {name}{mark}", file=sys.stderr)
                if line:
                    print(f"    {line}", file=sys.stderr)
            print(file=sys.stderr)
            print(
                f"Run '{prog} <command> --help' for details.", file=sys.stderr
            )
            print(file=sys.stderr)
            print("Global options:", file=sys.stderr)
            print("  --raw    Output raw JSON instead of template format", file=sys.stderr)
        sys.exit(0)

    def _command_help(self, method, positional, optional):
        module = sys.modules.get(self.__class__.__module__)
        prog = module.__file__ if module else sys.argv[0]

        parts = [method.__name__]
        for p in positional:
            parts.append(f"<{p.name}>")
        for p in optional:
            parts.append(f"[--{p.name.replace('_', '-')}]")

        print(f"Usage: {prog} [--raw] {' '.join(parts)}", file=sys.stderr)
        print(file=sys.stderr)
        if method.__doc__:
            print(method.__doc__.strip(), file=sys.stderr)
            print(file=sys.stderr)

        if positional:
            print("Arguments:", file=sys.stderr)
            for p in positional:
                desc = self._param_doc(method, p.name)
                t = get_type_hints(method).get(p.name, str).__name__
                print(f"  {p.name} ({t})    {desc}", file=sys.stderr)
            print(file=sys.stderr)
        if optional:
            print("Options:", file=sys.stderr)
            for p in optional:
                desc = self._param_doc(method, p.name)
                t = get_type_hints(method).get(p.name, str).__name__
                dflt = f" (default: {p.default})"
                print(
                    f"  --{p.name.replace('_', '-')} ({t})    {desc}{dflt}",
                    file=sys.stderr,
                )
            print(file=sys.stderr)
        print("Global options:", file=sys.stderr)
        print("  --raw    Output raw JSON instead of template format", file=sys.stderr)
        print(file=sys.stderr)
        sys.exit(0)

    @staticmethod
    def _param_doc(method, name: str) -> str:
        doc = method.__doc__
        if not doc:
            return ""
        m = re.search(
            rf"Args:\s*(.*?)(?:\n\s*\n|\Z)", doc, re.DOTALL
        )
        if not m:
            return ""
        args_text = m.group(1)
        pm = re.search(rf"^\s+{name}\s*:\s*(.*)", args_text, re.MULTILINE)
        return pm.group(1).strip() if pm else ""
