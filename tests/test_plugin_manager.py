"""Tests for plugin_manager.py — all subprocess calls are mocked."""

import json
import sys
import unittest
from io import StringIO
from unittest.mock import patch, call

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
import plugin_manager


SAMPLE_PLUGINS = [
    {
        "id": "caveman@caveman",
        "version": "655b7d9c5431",
        "scope": "user",
        "enabled": True,
        "installPath": "/home/user/.claude/plugins/cache/caveman/caveman/655b7d9c5431",
        "installedAt": "2026-05-08T02:31:21.418Z",
        "lastUpdated": "2026-05-27T02:56:22.992Z",
    },
    {
        "id": "ecc@ecc",
        "version": "2.0.0-rc.1",
        "scope": "user",
        "enabled": True,
        "installPath": "/home/user/.claude/plugins/cache/ecc/ecc/2.0.0-rc.1",
        "installedAt": "2026-01-01T00:00:00.000Z",
        "lastUpdated": "2026-03-01T00:00:00.000Z",
    },
    {
        "id": "context7@claude-plugins-official",
        "version": "cda114029ef8",
        "scope": "user",
        "enabled": False,
        "installPath": "/home/user/.claude/plugins/cache/claude-plugins-official/context7/cda114029ef8",
        "installedAt": "2026-01-19T03:17:14.825Z",
        "lastUpdated": "2026-05-31T09:14:08.973Z",
    },
]


class TestListPlugins(unittest.TestCase):
    def test_returns_parsed_list(self):
        with patch("plugin_manager.run_claude", return_value=(0, json.dumps(SAMPLE_PLUGINS), "")) as mock:
            result = plugin_manager.list_plugins()
        mock.assert_called_once_with(["plugin", "list", "--json"])
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["id"], "caveman@caveman")

    def test_exits_on_cli_error(self):
        with patch("plugin_manager.run_claude", return_value=(1, "", "some error")):
            with self.assertRaises(SystemExit):
                plugin_manager.list_plugins()


class TestResolvePlugins(unittest.TestCase):
    def test_exact_id_match(self):
        result = plugin_manager.resolve_plugins(["caveman@caveman"], SAMPLE_PLUGINS)
        self.assertEqual(result[0]["id"], "caveman@caveman")

    def test_partial_name_match(self):
        result = plugin_manager.resolve_plugins(["caveman"], SAMPLE_PLUGINS)
        self.assertEqual(result[0]["id"], "caveman@caveman")

    def test_multiple_names(self):
        result = plugin_manager.resolve_plugins(["caveman", "ecc"], SAMPLE_PLUGINS)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "caveman@caveman")
        self.assertEqual(result[1]["id"], "ecc@ecc")

    def test_not_found_exits(self):
        with self.assertRaises(SystemExit):
            plugin_manager.resolve_plugins(["nonexistent"], SAMPLE_PLUGINS)

    def test_empty_names_returns_empty(self):
        result = plugin_manager.resolve_plugins([], SAMPLE_PLUGINS)
        self.assertEqual(result, [])


class TestUpdateOne(unittest.TestCase):
    def test_successful_update(self):
        with patch("plugin_manager.run_claude", return_value=(0, "Plugin updated successfully", "")):
            result = plugin_manager.update_one(SAMPLE_PLUGINS[0])
        self.assertEqual(result["status"], "updated")
        self.assertEqual(result["id"], "caveman@caveman")

    def test_already_current(self):
        with patch("plugin_manager.run_claude", return_value=(0, "Plugin is already up to date", "")):
            result = plugin_manager.update_one(SAMPLE_PLUGINS[0])
        self.assertEqual(result["status"], "current")

    def test_already_current_variant(self):
        with patch("plugin_manager.run_claude", return_value=(0, "already at latest version", "")):
            result = plugin_manager.update_one(SAMPLE_PLUGINS[0])
        self.assertEqual(result["status"], "current")

    def test_failed_update(self):
        with patch("plugin_manager.run_claude", return_value=(1, "", "Failed to update: network error")):
            result = plugin_manager.update_one(SAMPLE_PLUGINS[0])
        self.assertEqual(result["status"], "failed")
        self.assertIn("network error", result["message"])

    def test_calls_with_full_id(self):
        with patch("plugin_manager.run_claude", return_value=(0, "updated", "")) as mock:
            plugin_manager.update_one(SAMPLE_PLUGINS[0])
        mock.assert_called_once_with(["plugin", "update", "caveman@caveman"])


class TestCmdList(unittest.TestCase):
    def test_output_contains_plugin_names(self):
        with patch("plugin_manager.list_plugins", return_value=SAMPLE_PLUGINS):
            with patch("sys.stdout", new_callable=StringIO) as mock_out:
                plugin_manager.cmd_list(None)
                output = mock_out.getvalue()
        self.assertIn("caveman", output)
        self.assertIn("ecc", output)
        self.assertIn("context7", output)

    def test_output_shows_disabled_status(self):
        with patch("plugin_manager.list_plugins", return_value=SAMPLE_PLUGINS):
            with patch("sys.stdout", new_callable=StringIO) as mock_out:
                plugin_manager.cmd_list(None)
                output = mock_out.getvalue()
        self.assertIn("✗", output)  # context7 is disabled

    def test_output_shows_plugin_count(self):
        with patch("plugin_manager.list_plugins", return_value=SAMPLE_PLUGINS):
            with patch("sys.stdout", new_callable=StringIO) as mock_out:
                plugin_manager.cmd_list(None)
                output = mock_out.getvalue()
        self.assertIn("3 plugins", output)


class TestCmdUpdate(unittest.TestCase):
    def _make_args(self, plugins=None, all_=False, parallel=False):
        class Args:
            pass
        a = Args()
        a.plugins = plugins or []
        a.all = all_
        a.parallel = parallel
        return a

    def test_update_single_by_partial_name(self):
        with patch("plugin_manager.list_plugins", return_value=SAMPLE_PLUGINS):
            with patch("plugin_manager.update_one", return_value={"id": "caveman@caveman", "status": "updated", "message": "ok"}) as mock_update:
                with patch("sys.stdout", new_callable=StringIO):
                    plugin_manager.cmd_update(self._make_args(plugins=["caveman"]))
        mock_update.assert_called_once()
        self.assertEqual(mock_update.call_args[0][0]["id"], "caveman@caveman")

    def test_update_all(self):
        with patch("plugin_manager.list_plugins", return_value=SAMPLE_PLUGINS):
            with patch("plugin_manager.update_one", return_value={"id": "x", "status": "updated", "message": "ok"}) as mock_update:
                with patch("sys.stdout", new_callable=StringIO):
                    plugin_manager.cmd_update(self._make_args(all_=True))
        self.assertEqual(mock_update.call_count, 3)

    def test_update_all_continues_on_failure(self):
        """One failure must not abort remaining updates."""
        def side_effect(plugin):
            if plugin["id"] == "ecc@ecc":
                return {"id": "ecc@ecc", "status": "failed", "message": "network error"}
            return {"id": plugin["id"], "status": "updated", "message": "ok"}

        with patch("plugin_manager.list_plugins", return_value=SAMPLE_PLUGINS):
            with patch("plugin_manager.update_one", side_effect=side_effect):
                with patch("sys.stdout", new_callable=StringIO):
                    with self.assertRaises(SystemExit) as ctx:
                        plugin_manager.cmd_update(self._make_args(all_=True))
        self.assertEqual(ctx.exception.code, 1)

    def test_summary_shows_counts(self):
        def side_effect(plugin):
            if plugin["id"] == "caveman@caveman":
                return {"id": "caveman@caveman", "status": "updated", "message": "ok"}
            if plugin["id"] == "ecc@ecc":
                return {"id": "ecc@ecc", "status": "current", "message": "already up to date"}
            return {"id": plugin["id"], "status": "failed", "message": "error"}

        with patch("plugin_manager.list_plugins", return_value=SAMPLE_PLUGINS):
            with patch("plugin_manager.update_one", side_effect=side_effect):
                with patch("sys.stdout", new_callable=StringIO) as mock_out:
                    with self.assertRaises(SystemExit):
                        plugin_manager.cmd_update(self._make_args(all_=True))
                    output = mock_out.getvalue()
        self.assertIn("1", output)   # updated count
        self.assertIn("1", output)   # current count
        self.assertIn("Failed", output)

    def test_no_plugins_and_no_all_exits(self):
        """Calling update with no args should error."""
        with patch("plugin_manager.list_plugins", return_value=SAMPLE_PLUGINS):
            with patch("sys.stdout", new_callable=StringIO):
                with self.assertRaises(SystemExit):
                    plugin_manager.cmd_update(self._make_args(plugins=[], all_=False))


class TestRunClaude(unittest.TestCase):
    def test_finds_claude_executable(self):
        with patch("plugin_manager.shutil.which", return_value="/usr/bin/claude"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = type("R", (), {"returncode": 0, "stdout": "[]", "stderr": ""})()
                code, out, err = plugin_manager.run_claude(["plugin", "list", "--json"])
        self.assertEqual(code, 0)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "/usr/bin/claude")
        self.assertIn("plugin", args)

    def test_exits_if_claude_not_in_path(self):
        with patch("plugin_manager.shutil.which", return_value=None):
            with self.assertRaises(SystemExit):
                plugin_manager.run_claude(["plugin", "list", "--json"])


if __name__ == "__main__":
    unittest.main()
