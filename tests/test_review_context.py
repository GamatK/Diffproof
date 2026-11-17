"""Tests for skills/review-playbook/scripts/review_context.py.

Each test builds a throwaway git repository, makes a change, and checks the report.
Run with:  python3 -m unittest discover -s tests -v
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "review-playbook" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import review_context as rc  # noqa: E402


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


class RepoTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        run(["git", "init", "-q", "-b", "main"], self.root)
        run(["git", "config", "user.email", "test@example.com"], self.root)
        run(["git", "config", "user.name", "Test"], self.root)
        self.write("README.md", "# demo\n")
        self.commit("initial")

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, msg):
        run(["git", "add", "-A"], self.root)
        run(["git", "commit", "-q", "-m", msg], self.root)

    def report(self, base="HEAD"):
        return rc.analyse(self.root, base)


class TestClassification(unittest.TestCase):
    def test_areas(self):
        self.assertEqual(rc.classify("src/app.py"), ["code"])
        self.assertIn("ui", rc.classify("Sources/Views/ProfileView.swift"))
        self.assertIn("ui", rc.classify("web/styles.css"))
        self.assertIn("backend", rc.classify("api/routes/users.ts"))
        self.assertIn("backend", rc.classify("supabase/migrations/001_init.sql"))
        self.assertEqual(rc.classify("docs/guide.md"), ["writing"])
        self.assertEqual(rc.classify("data/sales.csv"), ["data"])

    def test_dependency_and_requirements_are_not_writing_or_data(self):
        self.assertNotIn("writing", rc.classify("requirements.txt"))
        self.assertNotIn("data", rc.classify("package.json"))


class TestDiffParsing(unittest.TestCase):
    def test_line_numbers_follow_hunks(self):
        diff = (
            "diff --git a/a.py b/a.py\n"
            "--- a/a.py\n+++ b/a.py\n"
            "@@ -10,0 +11,2 @@\n+first\n+second\n"
            "@@ -20,1 +22,1 @@\n-old\n+new\n"
        )
        added, n_add, n_del = rc.parse_diff(diff)
        self.assertEqual(added["a.py"], [(11, "first"), (12, "second"), (22, "new")])
        self.assertEqual((n_add, n_del), (3, 1))


class TestRisk(RepoTestCase):
    def test_small_doc_change_is_low(self):
        self.write("README.md", "# demo\n\nOne more line.\n")
        r = self.report()
        self.assertEqual(r.risk, "low")
        self.assertEqual(r.checklists, ["references/writing.md"])

    def test_auth_path_is_high(self):
        self.write("src/auth/login.py", "def login(user):\n    return True\n")
        r = self.report()
        self.assertEqual(r.risk, "high")
        self.assertIn("touches authentication", r.risk_reasons)

    def test_migration_is_high_and_uses_backend_checklist(self):
        self.write("supabase/migrations/002_orders.sql", "alter table orders add column note text;\n")
        r = self.report()
        self.assertEqual(r.risk, "high")
        self.assertIn("references/backend.md", r.checklists)

    def test_code_without_tests_gets_a_note(self):
        self.write("src/math_utils.py", "def add(a, b):\n    return a + b\n")
        r = self.report()
        self.assertTrue(any("no test files changed" in n for n in r.notes))

    def test_code_with_tests_has_no_missing_test_note(self):
        self.write("src/math_utils.py", "def add(a, b):\n    return a + b\n")
        self.write("tests/test_math_utils.py", "def test_add():\n    assert 1 + 1 == 2\n")
        r = self.report()
        self.assertFalse(any("no test files changed" in n for n in r.notes))


class TestWarnings(RepoTestCase):
    def messages(self, report):
        return {(w.severity, w.message) for w in report.warnings}

    def test_secret_is_blocker_and_masked(self):
        key = "sk-" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4"
        self.write("src/client.py", f'API = "{key}"\n')
        r = self.report()
        blockers = [w for w in r.warnings if w.severity == "blocker"]
        self.assertTrue(blockers)
        self.assertNotIn(key, blockers[0].excerpt)
        self.assertEqual(r.risk, "high")

    def test_env_lookup_is_not_a_secret(self):
        self.write("src/client.py", 'API_KEY = os.environ["API_KEY"]\n')
        r = self.report()
        self.assertFalse([w for w in r.warnings if w.severity == "blocker"])

    def test_skipped_test_and_disabled_lint(self):
        self.write("web/app.test.js", "it.skip('works', () => {});\n")
        self.write("web/app.js", "// eslint-disable-next-line\nconst x = 1;\n")
        msgs = self.messages(self.report())
        self.assertIn(("major", "test skipped or focused (.only)"), msgs)
        self.assertIn(("major", "lint or type check disabled"), msgs)

    def test_empty_catch_and_eval(self):
        self.write("src/run.py", "try:\n    eval(user_input)\nexcept:\n    pass\n")
        msgs = self.messages(self.report())
        self.assertIn(("major", "dynamic code execution or unsafe HTML/deserialization"), msgs)
        self.assertIn(("major", "error swallowed by an empty catch"), msgs)

    def test_common_false_positives_are_not_flagged(self):
        self.write("src/store.py", "import json\njson.dump(data, f)\n")
        self.write("web/list.js", "list.innerHTML = \"\";\n")
        msgs = self.messages(self.report())
        self.assertNotIn(("minor", "debug output left in"), msgs)
        self.assertNotIn(("major", "dynamic code execution or unsafe HTML/deserialization"), msgs)

    def test_innerhtml_with_interpolation_is_flagged(self):
        self.write("web/list.js", "sel.innerHTML = `<option>${name}</option>`;\n")
        msgs = self.messages(self.report())
        self.assertIn(("major", "dynamic code execution or unsafe HTML/deserialization"), msgs)

    def test_json_config_does_not_load_research_checklist(self):
        self.write("config/settings.json", "{}\n")
        self.assertNotIn("references/research.md", self.report().checklists)

    def test_warning_line_numbers_are_real(self):
        self.write("src/a.py", "x = 1\ny = 2\n# TODO tidy\n")
        r = self.report()
        todo = [w for w in r.warnings if "TODO" in w.message]
        self.assertEqual(todo[0].line, 3)

    def test_debug_print_ignored_in_tests(self):
        self.write("tests/test_x.py", "print('debugging')\n")
        msgs = self.messages(self.report())
        self.assertNotIn(("minor", "debug output left in"), msgs)

    def test_committed_changes_on_a_branch_are_included(self):
        run(["git", "checkout", "-q", "-b", "feature"], self.root)
        self.write("src/feature.py", "def f():\n    return 1  # FIXME\n")
        self.commit("feature")
        r = rc.analyse(self.root, rc.default_base(self.root))
        self.assertIn("src/feature.py", r.files_changed)


class TestCommands(RepoTestCase):
    def test_package_json_scripts(self):
        self.write("package.json", json.dumps({"scripts": {"test": "vitest", "lint": "eslint .", "build": "vite build"}}))
        cmds = rc.detect_commands(self.root)
        self.assertEqual(cmds["test"], "npm run test")
        self.assertEqual(cmds["lint"], "npm run lint")

    def test_swift_package(self):
        self.write("Package.swift", "// swift-tools-version:5.9\n")
        self.assertEqual(rc.detect_commands(self.root)["test"], "swift test")


class TestCli(RepoTestCase):
    def test_json_output_and_exit_code(self):
        self.write("src/ok.py", "def ok():\n    return 1\n")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "review_context.py"), "--json", "--base", "HEAD"],
            cwd=self.root, capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertIn("src/ok.py", data["files_changed"])

    def test_outside_git_repo(self):
        with tempfile.TemporaryDirectory() as d:
            proc = subprocess.run([sys.executable, str(SCRIPT_DIR / "review_context.py")],
                                  cwd=d, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
