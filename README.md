# claude-plugin-updater

Cross-platform Python CLI to simplify Claude plugin management.

## Requirements

- Python 3.8+
- `claude` CLI in PATH (Claude Code)

No external dependencies — stdlib only.

## Commands

### list

Show all installed plugins in a compact table.

```bash
python plugin_manager.py list
```

```
Plugin                     Source                    Version        Scope    Status
───────────────────────────────────────────────────────────────────────────────────
caveman                    caveman                   655b7d9c5431   user     ✔
ecc                        ecc                       2.0.0-rc.1     user     ✔
context7                   claude-plugins-official   cda114029ef8   user     ✗
...

27 plugins installed
```

### update

Update one, multiple, or all plugins. Partial plugin names are accepted (no need to type `caveman@caveman`).

```bash
# Single plugin
python plugin_manager.py update caveman

# Multiple plugins
python plugin_manager.py update caveman ecc eduforge

# All plugins (sequential)
python plugin_manager.py update --all

# All plugins (parallel — faster for many plugins)
python plugin_manager.py update --all --parallel
```

```
Updating 3 plugins...

[1/3] caveman@caveman... ✔
[2/3] ecc@ecc... ─
[3/3] eduforge@eduforge... ✔

────────────────────────────────────────
Updated: 2  Already current: 1  Failed: 0
```

Icons: `✔` updated · `─` already current · `✗` failed

### uninstall / remove

Remove one or more plugins. Prompts for confirmation unless `-y` is passed.

```bash
# Single plugin (with confirmation prompt)
python plugin_manager.py uninstall caveman

# Skip prompt
python plugin_manager.py uninstall caveman -y

# Multiple plugins
python plugin_manager.py uninstall caveman ecc -y

# Preserve plugin data directory
python plugin_manager.py uninstall caveman -y --keep-data

# Remove unused auto-installed dependencies
python plugin_manager.py uninstall caveman -y --prune

# 'remove' is an alias
python plugin_manager.py remove caveman -y
```

## Tests

```bash
python -m pytest tests/ -v
```

36 tests, all subprocess calls mocked — no real plugins are modified during testing.

## Cross-platform

Works on Windows, Linux, macOS. Uses `shutil.which` to locate `claude`/`claude.cmd`/`claude.exe`.
