"""Claude plugin manager — list and batch-update plugins.

Usage:
    python plugin_manager.py list
    python plugin_manager.py update caveman
    python plugin_manager.py update caveman ecc eduforge
    python plugin_manager.py update --all
    python plugin_manager.py update --all --parallel
"""

import argparse
import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_claude(args: list) -> tuple:
    """Thin subprocess seam — mockable in tests.

    Returns (returncode, stdout, stderr).
    Cross-platform: shutil.which locates claude/claude.cmd/claude.exe.
    """
    exe = shutil.which("claude")
    if not exe:
        sys.exit("Error: 'claude' not found in PATH. Is Claude Code installed?")
    result = subprocess.run(
        [exe] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.returncode, result.stdout, result.stderr


def list_plugins() -> list:
    """Return parsed plugin list from `claude plugin list --json`."""
    code, out, err = run_claude(["plugin", "list", "--json"])
    if code != 0:
        sys.exit(f"Error listing plugins: {err.strip()}")
    return json.loads(out)


def resolve_plugins(names: list, all_plugins: list) -> list:
    """Match plugin names (partial or full id) to plugin records.

    Accepts both full id ("caveman@caveman") and short name ("caveman").
    """
    if not names:
        return []
    index = {p["id"]: p for p in all_plugins}
    resolved = []
    for name in names:
        if name in index:
            resolved.append(index[name])
            continue
        matches = [p for p in all_plugins if p["id"].split("@")[0] == name]
        if len(matches) == 1:
            resolved.append(matches[0])
        elif len(matches) > 1:
            options = ", ".join(p["id"] for p in matches)
            sys.exit(f"Ambiguous plugin '{name}'. Options: {options}")
        else:
            sys.exit(f"Plugin '{name}' not found. Run 'list' to see installed plugins.")
    return resolved


def update_one(plugin: dict) -> dict:
    """Update a single plugin. Returns result dict with status key."""
    pid = plugin["id"]
    code, out, err = run_claude(["plugin", "update", pid])
    message = (out + err).strip()
    if code != 0:
        return {"id": pid, "status": "failed", "message": message}
    already = any(kw in message.lower() for kw in ("already", "up to date", "up-to-date"))
    return {"id": pid, "status": "current" if already else "updated", "message": message}


def _print_table(plugins: list) -> None:
    name_w = max(len(p["id"].split("@")[0]) for p in plugins) + 2
    src_w = max(len(p["id"].split("@", 1)[1]) for p in plugins) + 2
    ver_w = max(len(p["version"]) for p in plugins) + 2

    header = f"{'Plugin':<{name_w}} {'Source':<{src_w}} {'Version':<{ver_w}} {'Scope':<8} Status"
    print(header)
    print("─" * len(header))
    for p in plugins:
        name, source = p["id"].split("@", 1)
        status = "✔" if p["enabled"] else "✗"
        print(f"{name:<{name_w}} {source:<{src_w}} {p['version']:<{ver_w}} {p['scope']:<8} {status}")
    print(f"\n{len(plugins)} plugin{'s' if len(plugins) != 1 else ''} installed")


def cmd_list(_args) -> None:
    _print_table(list_plugins())


def cmd_update(args) -> None:
    all_plugins = list_plugins()

    if args.all:
        targets = all_plugins
    elif args.plugins:
        targets = resolve_plugins(args.plugins, all_plugins)
    else:
        sys.exit("Error: specify plugin name(s) or --all")

    total = len(targets)
    print(f"Updating {total} plugin{'s' if total != 1 else ''}...\n")

    results = []
    icons = {"updated": "✔", "current": "─", "failed": "✗"}

    if args.parallel and total > 1:
        order = {p["id"]: i for i, p in enumerate(targets)}
        done = [None] * total
        with ThreadPoolExecutor(max_workers=min(8, total)) as ex:
            futures = {ex.submit(update_one, p): p for p in targets}
            for fut in as_completed(futures):
                r = fut.result()
                done[order[r["id"]]] = r
                print(f"  {icons[r['status']]} {r['id']}")
        results = done
    else:
        for i, p in enumerate(targets, 1):
            print(f"[{i}/{total}] {p['id']}...", end=" ", flush=True)
            r = update_one(p)
            print(icons[r["status"]])
            results.append(r)

    updated = sum(1 for r in results if r["status"] == "updated")
    current = sum(1 for r in results if r["status"] == "current")
    failed = [r for r in results if r["status"] == "failed"]

    print(f"\n{'─' * 40}")
    print(f"Updated: {updated}  Already current: {current}  Failed: {len(failed)}")

    if failed:
        print("\nFailed plugins:")
        for r in failed:
            print(f"  ✗ {r['id']}: {r['message']}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="plugin_manager",
        description="Claude plugin manager — list and update plugins",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List installed plugins")

    up = sub.add_parser("update", help="Update plugin(s)")
    up.add_argument("plugins", nargs="*", metavar="plugin", help="Plugin name(s) to update")
    up.add_argument("--all", action="store_true", help="Update all installed plugins")
    up.add_argument("--parallel", action="store_true", help="Run updates concurrently (useful with --all)")

    args = parser.parse_args()
    if args.command == "list":
        cmd_list(args)
    elif args.command == "update":
        cmd_update(args)


if __name__ == "__main__":
    main()
