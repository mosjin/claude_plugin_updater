# claude-plugin-updater

Cross-platform Python CLI to simplify Claude plugin management.

## Requirements

- Python 3.8+
- `claude` CLI in PATH (Claude Code)

No external dependencies — stdlib only.

## Usage

```bash
# List all installed plugins (clean table)
python plugin_manager.py list

# Update one plugin (partial name OK)
python plugin_manager.py update caveman

# Update multiple plugins
python plugin_manager.py update caveman ecc eduforge

# Update all plugins (sequential)
python plugin_manager.py update --all

# Update all plugins (parallel, faster)
python plugin_manager.py update --all --parallel
```

## Example output

```
Plugin                     Source                    Version        Scope    Status
───────────────────────────────────────────────────────────────────────────────────
caveman                    caveman                   655b7d9c5431   user     ✔
ecc                        ecc                       2.0.0-rc.1     user     ✔
...

27 plugins installed
```

```
Updating 3 plugins...

[1/3] caveman@caveman... ✔
[2/3] ecc@ecc... ─
[3/3] eduforge@eduforge... ✔

────────────────────────────────────────
Updated: 2  Already current: 1  Failed: 0
```

## Tests

```bash
python -m pytest tests/ -v
```

## Cross-platform

Works on Windows, Linux, macOS. Uses `shutil.which` to locate the `claude` executable.
