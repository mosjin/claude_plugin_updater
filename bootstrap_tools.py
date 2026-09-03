"""Install the standalone CLI tools ~/.claude's hooks/skills expect, on a
fresh Linux dev machine.

These are NOT Claude Code plugins (those are handled by `claude plugin
install` / plugin_manager.py in this repo, and auto-reinstall on the next
Claude Code restart via the marketplace git-clone mechanism). This script
covers the separately-installed binaries that CLAUDE.md's global rules
assume are on PATH: rtk, gh-asset, plus the node/uv runtimes several
hooks and MCP servers need to run at all.

Idempotent: skips anything already on PATH. Installs everything under
~/.local (node under ~/.local/node, symlinked into ~/.local/bin; uv's own
installer already targets ~/.local/bin) -- no sudo required.

Usage:
    python bootstrap_tools.py          # install what's missing
    python bootstrap_tools.py --check  # report status only, install nothing
"""

import argparse
import json
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

LOCAL_BIN = Path.home() / ".local" / "bin"
NODE_DIR = Path.home() / ".local" / "node"

# gh-asset dropped Linux release assets after v0.1.5 (checked against the
# GitHub releases API on 2026-09-03 -- latest v0.1.6 ships macOS only).
# Pinned rather than "latest" so this script doesn't silently regress the
# same way the upstream project did.
GH_ASSET_VERSION = "v0.1.5"


def _http_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "bootstrap_tools"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "bootstrap_tools"})
    with urllib.request.urlopen(req, timeout=90) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)


def _extract_single_binary(archive: Path, binary_name: str, dest: Path) -> None:
    """Extract one named file from a .tar.gz to dest, made executable."""
    with tarfile.open(archive) as tf:
        member = next(
            (m for m in tf.getmembers() if m.name == binary_name or m.name.endswith(f"/{binary_name}")),
            None,
        )
        if member is None:
            sys.exit(f"Error: '{binary_name}' not found inside {archive.name}")
        member.name = dest.name
        tf.extract(member, path=dest.parent)
    dest.chmod(0o755)


def check_node() -> bool:
    return shutil.which("node") is not None


def install_node() -> None:
    """Prebuilt linux-x64 tarball -> ~/.local/node, symlinked into ~/.local/bin.

    Not via nvm: nvm's installer clones a git repo as its first step, which
    hung for 2+ minutes on this network (see TECH_LOG). A direct tarball
    download is faster and has no such failure mode.
    """
    if platform.machine() != "x86_64":
        sys.exit(f"Error: no prebuilt node tarball logic for arch '{platform.machine()}' -- extend this function")

    index = _http_json("https://nodejs.org/dist/latest-v22.x/index.json")
    version = index[0]["version"]  # e.g. "v22.23.2"
    asset = f"node-{version}-linux-x64"
    url = f"https://nodejs.org/dist/latest-v22.x/{asset}.tar.xz"

    tmp = Path("/tmp") / f"{asset}.tar.xz"
    print(f"  downloading {url}")
    _download(url, tmp)

    if NODE_DIR.exists():
        shutil.rmtree(NODE_DIR)
    subprocess.run(["tar", "-xJf", str(tmp), "-C", "/tmp"], check=True)
    shutil.move(str(Path("/tmp") / asset), str(NODE_DIR))
    tmp.unlink()

    LOCAL_BIN.mkdir(parents=True, exist_ok=True)
    for name in ("node", "npm", "npx"):
        link = LOCAL_BIN / name
        link.unlink(missing_ok=True)
        link.symlink_to(NODE_DIR / "bin" / name)


def check_uv() -> bool:
    return shutil.which("uv") is not None


def install_uv() -> None:
    subprocess.run(
        "curl -LsSf https://astral.sh/uv/install.sh | sh",
        shell=True, check=True,
    )


def check_rtk() -> bool:
    return shutil.which("rtk") is not None


def install_rtk() -> None:
    """Public repo (rtk-ai/rtk, MIT) -- not one of mosjin's own forks."""
    if platform.machine() != "x86_64":
        sys.exit(f"Error: no prebuilt rtk asset logic for arch '{platform.machine()}' -- extend this function")

    release = _http_json("https://api.github.com/repos/rtk-ai/rtk/releases/latest")
    asset_name = "rtk-x86_64-unknown-linux-musl.tar.gz"
    asset = next((a for a in release["assets"] if a["name"] == asset_name), None)
    if asset is None:
        sys.exit(f"Error: {asset_name} not found in rtk-ai/rtk {release['tag_name']}")

    tmp = Path("/tmp") / asset_name
    print(f"  downloading {asset['browser_download_url']}")
    _download(asset["browser_download_url"], tmp)

    LOCAL_BIN.mkdir(parents=True, exist_ok=True)
    _extract_single_binary(tmp, "rtk", LOCAL_BIN / "rtk")
    tmp.unlink()


def check_gh_asset() -> bool:
    return shutil.which("gh-asset") is not None


def install_gh_asset() -> None:
    """mosjin/gh-asset fork exists too, but upstream YuitoSato/gh-asset is
    the maintained source. Pinned to GH_ASSET_VERSION -- see its docstring.
    """
    if platform.machine() != "x86_64":
        sys.exit(f"Error: no prebuilt gh-asset asset logic for arch '{platform.machine()}' -- extend this function")

    asset_name = "gh-asset-x86_64-unknown-linux-gnu.tar.gz"
    url = f"https://github.com/YuitoSato/gh-asset/releases/download/{GH_ASSET_VERSION}/{asset_name}"

    tmp = Path("/tmp") / asset_name
    print(f"  downloading {url}")
    _download(url, tmp)

    LOCAL_BIN.mkdir(parents=True, exist_ok=True)
    _extract_single_binary(tmp, "gh-asset", LOCAL_BIN / "gh-asset")
    tmp.unlink()


# Each tool: (display name, check fn, install fn, note shown when missing/skipped)
TOOLS = [
    ("node/npm/npx", check_node, install_node, None),
    ("uv/uvx", check_uv, install_uv, None),
    ("rtk", check_rtk, install_rtk, None),
    ("gh-asset", check_gh_asset, install_gh_asset, None),
]

# Not installable by this script -- documented so `--check` gives a full
# picture instead of silently omitting a tool CLAUDE.md's rules reference.
KNOWN_UNAVAILABLE = [
    ("sqz", "upstream repo (ojuschugh1/sqz) has been deleted from GitHub -- "
            "the install.sh script, npm package, and PyPI wrapper all point at "
            "release assets that now 404. mosjin/sqz fork has the source but no "
            "releases/tags. Building from source needs `build-essential` (sudo, "
            "no passwordless sudo on record) plus a Rust toolchain. No path "
            "forward found as of 2026-09-03; skip."),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="Report status only, install nothing")
    args = parser.parse_args()

    print(f"{'Tool':<16} {'Status'}")
    print("-" * 40)

    missing = []
    for name, check, install, _note in TOOLS:
        present = check()
        print(f"{name:<16} {'already installed' if present else 'missing'}")
        if not present:
            missing.append((name, install))

    for name, note in KNOWN_UNAVAILABLE:
        print(f"{name:<16} unavailable -- {note}")

    if args.check:
        return

    if not missing:
        print("\nNothing to install.")
        return

    print(f"\nInstalling {len(missing)} tool(s)...")
    for name, install in missing:
        print(f"\n[{name}]")
        install()
        print(f"  {name} installed")

    print("\nDone. Make sure ~/.local/bin is on PATH (Claude Code's ~/.claude/settings.json "
          "env.PATH already includes it after restore.py; a plain shell may need "
          "`export PATH=\"$HOME/.local/bin:$PATH\"` in ~/.bashrc).")


if __name__ == "__main__":
    main()
