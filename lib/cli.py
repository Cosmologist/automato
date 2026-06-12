#!/usr/bin/env python3
from __future__ import annotations

import inspect
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import textwrap
from typing import Any, Literal, get_args, get_origin, get_type_hints


def _literal_choices(hint):
    if hint is None:
        return None
    origin = get_origin(hint)
    if origin is Literal:
        return get_args(hint)
    return None


def _ansi():
    if not sys.stderr.isatty() or os.environ.get("NO_COLOR"):
        return {"dim": "", "bold": "", "cyan": "", "green": "", "yellow": "", "red": "", "reset": ""}
    return {
        "dim": "\033[2m",
        "bold": "\033[1m",
        "cyan": "\033[36m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "red": "\033[31m",
        "reset": "\033[0m",
    }


_S = _ansi()


def default(func):
    func._cli_default = True
    return func



class CLI:
    _arg_labels: dict[str, str] = {}
    _version: str = ""
    _name: str = ""
    _icon: str = "▸"

    def __init__(self):
        self._tty: bool | None = None

    @classmethod
    def run(cls):
        instance = cls()
        argv = sys.argv[1:]

        for i, a in enumerate(argv):
            if a.startswith("--tty"):
                if "=" in a:
                    val = a.split("=", 1)[1].lower()
                    instance._tty = val in ("true", "yes", "1")
                elif i + 1 < len(argv) and argv[i + 1].lower() in ("true", "false", "yes", "no", "1", "0"):
                    val = argv.pop(i + 1).lower()
                    instance._tty = val in ("true", "yes", "1")
                else:
                    instance._tty = True
                argv = [x for x in argv if not x.startswith("--tty")]
                break

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
                    if p.name != "self" and p.default is inspect.Parameter.empty and p.kind != inspect.Parameter.VAR_POSITIONAL
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

    def _usage_args(self, method):
        labels = getattr(self.__class__, "_arg_labels", {})
        hints = get_type_hints(method)
        parts = []
        for p in inspect.signature(method).parameters.values():
            if p.name == "self":
                continue
            label = labels.get(p.name, p.name)
            choices = _literal_choices(hints.get(p.name))
            if choices:
                label = "|".join(str(c) for c in choices)
            if p.kind == inspect.Parameter.VAR_POSITIONAL:
                parts.append(f"[{_S['green']}{label}{_S['reset']}]")
            elif p.default is inspect.Parameter.empty:
                parts.append(f"<{_S['green']}{label}{_S['reset']}>")
            elif isinstance(p.default, bool):
                parts.append(f"[{_S['yellow']}--{p.name.replace('_', '-')}{_S['reset']}]")
            else:
                parts.append(f"[{_S['yellow']}--{p.name.replace('_', '-')}{_S['reset']}={p.default}]")
        return " ".join(parts)

    def _cli_opts(self):
        return f"[{_S['yellow']}--help{_S['reset']}] [{_S['yellow']}--tty{_S['reset']}]"

    def _prog_name(self):
        module = sys.modules.get(self.__class__.__module__)
        return Path(module.__file__).name if module else sys.argv[0]

    @staticmethod
    def _doc_first(method):
        return method.__doc__.strip().split("\n")[0].rstrip(".") if method.__doc__ else ""

    @staticmethod
    def _visible_len(s: str) -> int:
        return len(re.sub(r'\033\[[0-9;]*m', '', s))

    def _print_banner(self):
        module = sys.modules.get(self.__class__.__module__)
        desc = module.__doc__.strip().rstrip(".") if module and module.__doc__ else ""
        name = self._name or self._prog_name()
        icon = self._icon
        ver = self._version

        cols = shutil.get_terminal_size().columns
        ver_text = f" {_S['dim']}{ver}{_S['reset']}" if ver else ""
        ver_visible = len(f" {ver}") if ver else 0

        prefix = f"{_S['bold']}[{icon}] {name}{_S['reset']}"
        desc_bold = f"{_S['bold']}{desc}{_S['reset']}"

        full = f"{prefix} — {desc_bold}{ver_text}"
        full_visible = self._visible_len(full)

        if full_visible <= cols:
            print(full, file=sys.stderr)
            print("─" * min(cols, 80), file=sys.stderr)
            return

        full_no_ver = f"{prefix} — {desc_bold}"
        full_no_ver_visible = self._visible_len(full_no_ver)
        if full_no_ver_visible <= cols:
            print(full_no_ver, file=sys.stderr)
            print("─" * min(cols, 80), file=sys.stderr)
            return

        print(prefix, file=sys.stderr)

        remain = f"{desc_bold}{ver_text}"
        remain_visible = self._visible_len(remain)
        if remain_visible <= cols:
            print(remain, file=sys.stderr)
        else:
            remain_no_ver = f"{desc_bold}"
            remain_no_ver_visible = self._visible_len(remain_no_ver)
            if remain_no_ver_visible <= cols:
                print(remain_no_ver, file=sys.stderr)
            else:
                wrapped = textwrap.fill(desc, width=cols, break_long_words=False, break_on_hyphens=False)
                for line in wrapped.split("\n"):
                    print(f"{_S['bold']}{line}{_S['reset']}", file=sys.stderr)

        print("─" * min(cols, 80), file=sys.stderr)

    def _print_header(self):
        if self._tty is False:
            return
        self._print_banner()

    def _print_usage(self):
        if self._tty is False:
            return
        cols = shutil.get_terminal_size().columns
        prog = self._prog_name()
        commands = self._get_commands()

        if len(commands) == 1:
            _, method = commands[0]
            usage_args = self._usage_args(method)
            print(f"Usage: {_S['bold']}{_S['cyan']}{prog}{_S['reset']} {usage_args} {self._cli_opts()}", file=sys.stderr)
        else:
            print(f"Usage: {_S['bold']}{_S['cyan']}{prog}{_S['reset']} <{_S['bold']}{_S['cyan']}command{_S['reset']}> [args...] {self._cli_opts()}", file=sys.stderr)
            for name, method in commands:
                usage = f"{prog} {name} {self._usage_args(method)}".rstrip()
                print(f"  {_S['bold']}{_S['cyan']}{name:<12}{_S['reset']}{self._doc_first(method)}", file=sys.stderr)
                print(f"    {_S["dim"]}{usage}{_S["reset"]}", file=sys.stderr)
        print("─" * min(cols, 80), file=sys.stderr)


    def _execute(self, method, argv):
        sig = inspect.signature(method)
        hints = get_type_hints(method)
        params = [p for p in sig.parameters.values() if p.name != "self"]

        var_param = None
        positional = []
        optional = []
        for p in params:
            if p.kind == inspect.Parameter.VAR_POSITIONAL:
                var_param = p
            elif p.default is inspect.Parameter.empty:
                positional.append(p)
            else:
                optional.append(p)

        if self._tty is not False:
            self._print_header()

        if argv and argv[0] in ("--help", "-h"):
            self._command_help(method, positional, optional, var_param)
            return

        pos_values = []
        i = 0
        while i < len(argv) and not argv[i].startswith("--"):
            pos_values.append(argv[i])
            i += 1

        if not var_param and len(pos_values) > len(positional) + len(optional):
            self._error(f"Too many arguments for '{method.__name__}'", show_usage=True)

        kwargs = {}
        while i < len(argv):
            arg = argv[i]
            if arg.startswith("--"):
                raw = arg[2:]
                if "=" in raw:
                    name, val = raw.split("=", 1)
                    name = name.replace("-", "_")
                    matching = [p for p in optional if p.name == name]
                    if not matching:
                        self._error(f"Unknown option: --{name}", show_usage=True)
                    p = matching[0]
                    t = hints.get(p.name, str)
                    kwargs[name] = self._convert(val, t)
                else:
                    name = raw.replace("-", "_")
                    matching = [p for p in optional if p.name == name]
                    if not matching:
                        self._error(f"Unknown option: {arg}", show_usage=True)
                    p = matching[0]
                    t = hints.get(p.name, str)
                    if t == bool:
                        kwargs[name] = True
                    else:
                        if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                            self._error(f"Option '{arg}' requires a value", show_usage=True)
                        i += 1
                        kwargs[name] = self._convert(argv[i], t)
            i += 1

        pos_args = []
        for idx, p in enumerate(positional):
            if idx < len(pos_values):
                pos_args.append(self._convert(
                    pos_values[idx], hints.get(p.name, str)
                ))
            else:
                self._error(f"Missing required argument: '{p.name}'", show_usage=True)

        overflow = pos_values[len(positional):]
        h_var = hints.get(var_param.name, str) if var_param else None
        if var_param:
            choices = _literal_choices(h_var)
            for v in overflow:
                if choices and v not in choices:
                    self._error(f"Unknown field: '{v}'", show_usage=True)
                pos_args.append(self._convert(v, h_var))
        else:
            kw_args = {}
            for idx, p in enumerate(optional):
                if idx < len(overflow):
                    kw_args[p.name] = self._convert(
                        overflow[idx], hints.get(p.name, str)
                    )
                elif p.name in kwargs:
                    kw_args[p.name] = kwargs[p.name]
                else:
                    kw_args[p.name] = p.default

        try:
            if var_param:
                result = method(*pos_args, **kwargs)
            else:
                result = method(*pos_args, **kw_args)
        except Exception as e:
            self._error(str(e), show_usage=True)
            return

        if result is not None:
            self._output(result, method)

    def _output(self, result, method):
        plain = self._tty is False or (self._tty is None and not sys.stdout.isatty())

        if plain:
            if isinstance(result, dict):
                print(" ".join(str(v) if v is not None else "" for v in result.values()))
            elif isinstance(result, list):
                if result and isinstance(result[0], dict):
                    for d in result:
                        print(" ".join(
                            str(d.get(k, "")) if d.get(k) is not None else ""
                            for k in d
                        ))
                else:
                    for item in result:
                        print(item)
            elif not isinstance(result, str):
                print(result)
            return

        if isinstance(result, str):
            print(result)
            return

        self._output_tsv(result)

    def _output_tsv(self, result):
        if isinstance(result, str):
            print(result)
            return

        if isinstance(result, dict):
            pad = max(len(k) for k in result) + 2
            for k, v in result.items():
                print(f"{_S['bold']}{k}{_S['reset']}{' ' * (pad - len(k))}{v}")
            return

        if isinstance(result, list):
            if not result:
                return
            if isinstance(result[0], dict):
                keys = list(dict.fromkeys(k for d in result for k in d))
                rows = [
                    [str(d.get(k, "")) if d.get(k) is not None else "" for k in keys]
                    for d in result
                ]
                widths = [
                    max(len(k), *(len(r[i]) for r in rows))
                    for i, k in enumerate(keys)
                ]
                print(" ".join(f"{_S['bold']}{k}{_S['reset']}{' ' * (w - len(k))}" for k, w in zip(keys, widths)))
                for row in rows:
                    print(" ".join(v.ljust(w) for v, w in zip(row, widths)))
            else:
                for item in result:
                    print(item)
            return

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

    def _error(self, msg: str, show_usage: bool = False):
        if show_usage:
            self._print_usage()
        print(f"{_S['red']}{msg}{_S['reset']}", file=sys.stderr)
        sys.exit(1)

    # -- help --

    def _help(self, commands):
        if self._tty is False:
            sys.exit(0)
        self._print_header()
        self._print_usage()
        print(file=sys.stderr)

        module = sys.modules.get(self.__class__.__module__)
        prog = module.__file__ if module else sys.argv[0]

        if len(commands) == 1:
            _, method = commands[0]
            labels = getattr(self.__class__, "_arg_labels", {})
            hints = get_type_hints(method)

            sig = inspect.signature(method)
            positional = [p for p in sig.parameters.values() if p.name != "self" and p.default is inspect.Parameter.empty and p.kind != inspect.Parameter.VAR_POSITIONAL]
            var_param = next((p for p in sig.parameters.values() if p.kind == inspect.Parameter.VAR_POSITIONAL), None)
            optional = [p for p in sig.parameters.values() if p.name != "self" and p.default is not inspect.Parameter.empty and p.kind != inspect.Parameter.VAR_POSITIONAL]

            if positional:
                print("ARGUMENTS:", file=sys.stderr)
                for p in positional:
                    d = self._param_doc(method, p.name)
                    label = labels.get(p.name, p.name)
                    choices = _literal_choices(hints.get(p.name))
                    if choices:
                        label = "|".join(str(c) for c in choices)
                    print(f"  {_S['green']}{label}{_S['reset']}{'  ' + d if d else ''}", file=sys.stderr)
                print(file=sys.stderr)
            if var_param:
                print("FIELDS:", file=sys.stderr)
                d = self._param_doc(method, var_param.name)
                label = labels.get(var_param.name, var_param.name)
                choices = _literal_choices(hints.get(var_param.name))
                if choices:
                    label = "|".join(str(c) for c in choices)
                print(f"  {_S['green']}{label}{_S['reset']}  {d}", file=sys.stderr)
                print(file=sys.stderr)
        else:
            print("COMMANDS:", file=sys.stderr)
            for name, method in commands:
                doc = method.__doc__
                d = doc.strip().split("\n")[0] if doc else ""
                args = self._usage_args(method)
                print(f"  {_S['bold']}{_S['cyan']}{name:<12}{_S['reset']}{d} {_S['dim']}({prog} {name} {args}){_S['reset']}", file=sys.stderr)
            print(file=sys.stderr)

        print("OPTIONS:", file=sys.stderr)
        print(f"  {_S['yellow']}--help{_S['reset']}\tShow this help or command help", file=sys.stderr)
        print(f"  {_S['yellow']}--tty{_S['reset']}\t\tControl output formatting", file=sys.stderr)
        if len(commands) == 1:
            _, method = commands[0]
            sig = inspect.signature(method)
            optional = [p for p in sig.parameters.values() if p.name != "self" and p.default is not inspect.Parameter.empty and p.kind != inspect.Parameter.VAR_POSITIONAL]
            for p in optional:
                d = self._param_doc(method, p.name)
                desc = f"  {d}" if d else ""
                dflt = f" (default: {p.default})"
                print(f"  {_S['yellow']}--{p.name.replace('_', '-')}{_S['reset']}\t{desc}{dflt}", file=sys.stderr)
        print(file=sys.stderr)

        sys.exit(0)

    def _command_help(self, method, positional, optional, var_param=None, error: str = ""):
        if self._tty is False:
            sys.exit(0)

        labels = getattr(self.__class__, "_arg_labels", {})
        hints = get_type_hints(method)
        prog = self._prog_name()
        args = []
        for p in positional:
            label = labels.get(p.name, p.name)
            choices = _literal_choices(hints.get(p.name))
            if choices:
                label = "|".join(str(c) for c in choices)
            args.append(f"<{_S['green']}{label}{_S['reset']}>")
        if var_param:
            label = labels.get(var_param.name, var_param.name)
            choices = _literal_choices(hints.get(var_param.name))
            if choices:
                label = "|".join(str(c) for c in choices)
            args.append(f"[{_S['green']}{label}{_S['reset']}]")
        for p in optional:
            args.append(f"[--{p.name.replace('_', '-')}]")
        commands = self._get_commands()
        if len(commands) > 1:
            print(f"Usage: {_S['bold']}{_S['cyan']}{prog}{_S['reset']} {_S['bold']}{_S['cyan']}{method.__name__}{_S['reset']} {' '.join(args)} {self._cli_opts()}", file=sys.stderr)
            cols = shutil.get_terminal_size().columns
            print("─" * min(cols, 80), file=sys.stderr)
            print(file=sys.stderr)

        if error:
            print(f"{_S['red']}{error}{_S['reset']}", file=sys.stderr)
            print(file=sys.stderr)

        if positional:
            print("ARGUMENTS:", file=sys.stderr)
            for p in positional:
                d = self._param_doc(method, p.name)
                label = labels.get(p.name, p.name)
                choices = _literal_choices(hints.get(p.name))
                if choices:
                    label = "|".join(str(c) for c in choices)
                print(f"  {_S['green']}{label}{_S['reset']}{'  ' + d if d else ''}", file=sys.stderr)
            print(file=sys.stderr)
        if var_param:
            print("FIELDS:", file=sys.stderr)
            d = self._param_doc(method, var_param.name)
            label = labels.get(var_param.name, var_param.name)
            choices = _literal_choices(hints.get(var_param.name))
            if choices:
                label = "|".join(str(c) for c in choices)
            print(f"  {_S['green']}{label}{_S['reset']}  {d}", file=sys.stderr)
            print(file=sys.stderr)

        print("OPTIONS:", file=sys.stderr)
        print(f"  {_S['yellow']}--help{_S['reset']}\tShow this help or command help", file=sys.stderr)
        print(f"  {_S['yellow']}--tty{_S['reset']}\t\tControl output formatting", file=sys.stderr)
        for p in optional:
            d = self._param_doc(method, p.name)
            desc = f"  {d}" if d else ""
            dflt = f" (default: {p.default})"
            print(f"  {_S['yellow']}--{p.name.replace('_', '-')}{_S['reset']}\t{desc}{dflt}", file=sys.stderr)
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
