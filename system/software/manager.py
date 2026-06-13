#!/usr/bin/env python3
"""Software package manager"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.cli import CLI
from lib.utils import exec_cmd, CommandError


_ARCHIVE_EXTS = (".tar.gz", ".tar.bz2", ".tar.xz", ".zip", ".tgz", ".tar")


def install_apt(name: str) -> bool:
    """Install via apt

    Args:
        name: APT package name
    """
    if not shutil.which("apt"):
        return False
    print(f"Installing via apt: {name}")
    exec_cmd(["apt", "install", "-y", name])
    return True


def _install_github_release(owner: str, repo: str) -> None:
    print(f"Fetching latest release for {owner}/{repo}...")

    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "automato/1.0")

    with urllib.request.urlopen(req) as resp:
        release = json.loads(resp.read().decode())

    assets = release.get("assets", [])
    if not assets:
        raise RuntimeError(f"No assets found in latest release of {owner}/{repo}")

    asset = _pick_github_asset(assets, repo)

    dest = Path.home() / ".local" / "bin"
    dest.mkdir(parents=True, exist_ok=True)
    dest_path = dest / repo

    print(f"Downloading {asset['name']}...")
    dl_req = urllib.request.Request(asset["browser_download_url"])
    dl_req.add_header("User-Agent", "automato/1.0")
    dl_req.add_header("Accept", "application/octet-stream")
    with urllib.request.urlopen(dl_req) as resp:
        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                f.write(chunk)

    dest_path.chmod(dest_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Installed {repo} to {dest_path}")


def _pick_github_asset(assets: list[dict], repo: str) -> dict:
    suitable = [
        a for a in assets
        if not any(a["name"].endswith(ext) for ext in _ARCHIVE_EXTS)
    ]
    if not suitable:
        raise RuntimeError("No suitable asset found \u2014 all assets are archives")

    if len(suitable) == 1:
        return suitable[0]

    for a in suitable:
        name = a["name"]
        if name == repo or name.startswith(f"{repo}_") or name.startswith(f"{repo}-"):
            return a
        if name.endswith((".pyz", ".phar")):
            return a

    return suitable[0]


def main():
    cli = CLI(version="1.0.0", prog=__file__, description="Software package manager")

    def install_github(name: str) -> bool:
        """Install from GitHub release by searching repo name

        Args:
            name: Tool name to search on GitHub
        """
        if shutil.which("gh") is None:
            try:
                exec_cmd(["apt", "install", "-y", "gh"])
            except CommandError:
                pass
            if shutil.which("gh") is None:
                return False

        result = cli.exec(["gh", "search", "repos", "--match", "name", name, "--json", "fullName", "--limit", "20"])
        repos = json.loads(result.stdout)

        exact = [
            r for r in repos
            if r["fullName"].split("/", 1)[1].lower() == name.lower()
        ]

        if not exact:
            return False

        if len(exact) > 1:
            raise RuntimeError(
                f"Multiple repos match '{name}': {[r['fullName'] for r in exact]}"
            )

        owner, repo = exact[0]["fullName"].split("/")
        _install_github_release(owner, repo)
        return True

    @cli.command(default=True)
    def require(name: str) -> str:
        """Require a software package \u2014 install if missing

        Args:
            name: Package name (apt name or tool name for GitHub search)
        """
        path = shutil.which(name)

        if path is not None:
            return path
        elif install_apt(name):
            pass
        elif install_github(name):
            pass

        path = shutil.which(name)
        if path is not None:
            return path

        raise RuntimeError(f"Unknown tool: {name}")

    cli.command(name="install-apt")(install_apt)
    cli.command(name="install-github")(install_github)

    cli.run()


if __name__ == "__main__":
    main()
