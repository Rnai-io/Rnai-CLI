# -*- coding: utf-8 -*-
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from typer.testing import CliRunner

import rnai_cli.config as cfg
import rnai_cli.history as hist
import rnai_cli.templates as tpl
import rnai_cli.worker as wrk
import rnai_cli.tools as tools
import rnai_cli.research_tools as rtools
from rnai_cli.main import app

runner = CliRunner()


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / ".rnai"
        self.config_path = self.config_dir / "config.json"

        self.patcher_dir = patch.object(cfg, "CONFIG_DIR", self.config_dir)
        self.patcher_path = patch.object(cfg, "CONFIG_PATH", self.config_path)
        self.patcher_dir.start()
        self.patcher_path.start()

    def tearDown(self):
        self.patcher_path.stop()
        self.patcher_dir.stop()
        shutil.rmtree(self.temp_dir)

    def test_load_defaults(self):
        loaded = cfg.load()
        self.assertEqual(loaded["RNAI_MODEL"], "rnai-llm")
        self.assertEqual(loaded["AGENT_PLANNER"], "groq")

    def test_set_and_save(self):
        cfg.set_value("GROQ_API_KEY", "gsk_test123")
        loaded = cfg.load()
        self.assertEqual(loaded["GROQ_API_KEY"], "gsk_test123")
        self.assertEqual(cfg.get("GROQ_API_KEY"), "gsk_test123")


class TestHistory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.hist_dir = Path(self.temp_dir) / "history"

        self.patcher_hist = patch.object(hist, "HIST_DIR", self.hist_dir)
        self.patcher_hist.start()

    def tearDown(self):
        self.patcher_hist.stop()
        shutil.rmtree(self.temp_dir)

    def test_session_lifecycle(self):
        # Create session
        sid = hist.new_session(title="Test Session", model="rnai")
        self.assertTrue(sid)
        
        # Load session
        data = hist.load(sid)
        self.assertIsNotNone(data)
        self.assertEqual(data["title"], "Test Session")
        self.assertEqual(len(data["messages"]), 0)

        # Append messages
        hist.append(sid, "user", "Hello AI", model="user")
        hist.append(sid, "assistant", "Hello User", model="rnai")

        data_updated = hist.load(sid)
        self.assertEqual(len(data_updated["messages"]), 2)
        self.assertEqual(data_updated["messages"][0]["content"], "Hello AI")
        self.assertEqual(data_updated["messages"][1]["content"], "Hello User")

        # List sessions
        sessions = hist.list_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["id"], sid)

        # Delete session
        deleted = hist.delete(sid)
        self.assertTrue(deleted)
        self.assertIsNone(hist.load(sid))


class TestTemplates(unittest.TestCase):
    def test_templates_integrity(self):
        self.assertGreater(len(tpl.TEMPLATES), 0)
        for item in tpl.TEMPLATES:
            self.assertIn("id", item)
            self.assertIn("title", item)
            self.assertIn("prompt", item)
            self.assertIn("type", item)
            self.assertIn("cat", item)

    def test_get_template(self):
        t_id = tpl.TEMPLATES[0]["id"]
        found = tpl.get(t_id)
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], t_id)
        self.assertIsNone(tpl.get("non-existent-template-xyz"))

    def test_fill_placeholders(self):
        text = "Hello {name}, your role is {role}."
        res = tpl.fill_placeholders(text, lambda k: "World" if k == "name" else "Tester")
        self.assertEqual(res, "Hello World, your role is Tester.")


class TestWorker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_path = Path(self.temp_dir) / "tasks.json"

        self.patcher_tasks = patch.object(wrk, "TASKS_PATH", self.tasks_path)
        self.patcher_tasks.start()

    def tearDown(self):
        self.patcher_tasks.stop()
        shutil.rmtree(self.temp_dir)

    def test_task_operations(self):
        # Empty tasks
        self.assertEqual(wrk.load_tasks(), [])

        # Add daily task
        t1 = wrk.add_task("Summary news", daily="08:00")
        self.assertEqual(t1["prompt"], "Summary news")
        self.assertEqual(t1["schedule"]["type"], "daily")
        self.assertIn("ทุกวัน 08:00", wrk.describe_schedule(t1["schedule"]))

        # Add interval task
        t2 = wrk.add_task("Check status", every=15)
        self.assertEqual(t2["schedule"]["type"], "every")
        self.assertIn("ทุก 15 นาที", wrk.describe_schedule(t2["schedule"]))

        tasks = wrk.load_tasks()
        self.assertEqual(len(tasks), 2)

        # Remove task
        removed = wrk.remove_task(t1["id"])
        self.assertTrue(removed)
        remaining = wrk.load_tasks()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["id"], t2["id"])


class TestTools(unittest.TestCase):
    def test_tool_schemas(self):
        names = [t["function"]["name"] for t in tools.TOOL_SCHEMAS]
        self.assertIn("web_search", names)
        self.assertIn("list_dir", names)
        self.assertIn("read_file", names)
        self.assertIn("write_file", names)
        self.assertIn("run_command", names)
        self.assertIn("rnai_skill", names)

    def test_resolve_path(self):
        with patch.object(tools, "workspace_dir", return_value=Path("/tmp/workspace")):
            p_rel = tools.resolve_path("subfolder/file.txt")
            self.assertEqual(str(p_rel), "/tmp/workspace/subfolder/file.txt")

            p_abs = tools.resolve_path("/etc/config")
            self.assertEqual(str(p_abs), "/etc/config")


class TestResearchTools(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_dir = Path(self.temp_dir) / "research"
        self.state_path = self.state_dir / "learner_state.json"
        self.log_path = self.state_dir / "tool_calls.jsonl"

        self.patcher_sdir = patch.object(rtools, "STATE_DIR", self.state_dir)
        self.patcher_spath = patch.object(rtools, "STATE_PATH", self.state_path)
        self.patcher_lpath = patch.object(rtools, "LOG_PATH", self.log_path)
        self.patcher_sdir.start()
        self.patcher_spath.start()
        self.patcher_lpath.start()

    def tearDown(self):
        self.patcher_lpath.stop()
        self.patcher_spath.stop()
        self.patcher_sdir.stop()
        shutil.rmtree(self.temp_dir)

    def test_state_lifecycle(self):
        st = rtools.load_state()
        self.assertEqual(st["week"], 1)
        self.assertEqual(st["fading_level"], "L1")

        st["week"] = 2
        st["fading_level"] = "L2"
        rtools.save_state(st)

        st_loaded = rtools.load_state()
        self.assertEqual(st_loaded["week"], 2)
        self.assertEqual(st_loaded["fading_level"], "L2")

    def test_logging(self):
        rtools._log("test_tool", {"rationale": "testing"}, True)
        self.assertTrue(self.log_path.exists())
        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry["tool"], "test_tool")
        self.assertTrue(entry["accepted"])


class TestCLI(unittest.TestCase):
    def test_help_command(self):
        result = runner.invoke(app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Rnai-CLI", result.output)

    def test_ui_help_command(self):
        result = runner.invoke(app, ["ui", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--remote", result.output)
        self.assertIn("--host", result.output)

    def test_templates_command(self):
        result = runner.invoke(app, ["templates"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("คลัง Templates", result.output)

    def test_folder_command(self):
        result = runner.invoke(app, ["folder"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("โฟลเดอร์ทำงานปัจจุบัน", result.output)

    def test_task_list_command(self):
        result = runner.invoke(app, ["task", "list"])
        self.assertEqual(result.exit_code, 0)

    def test_config_list_command(self):
        result = runner.invoke(app, ["config", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("config —", result.output)


class TestWebApp(unittest.TestCase):
    def test_lan_ip_detection(self):
        import rnai_cli.ui as ui
        ip = ui.get_lan_ip()
        self.assertIsInstance(ip, str)
        self.assertTrue(len(ip) > 0)

    def test_manifest_and_sw(self):
        import rnai_cli.ui as ui
        manifest = json.loads(ui.MANIFEST_JSON)
        self.assertEqual(manifest["short_name"], "Rnai")
        self.assertEqual(manifest["display"], "standalone")
        self.assertIn("rnai-pwa-v1", ui.SW_JS)


if __name__ == "__main__":
    unittest.main()
