"""Ported from the SNES harness (2026-11-24): inbox triage --to lesson links an existing lesson or runs lessons.py add."""
import contextlib
import io
import pathlib
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest import mock


SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import kb  # noqa: E402


class InboxLessonTriageTests(unittest.TestCase):
    def setUp(self):
        self.item = {
            "id": "ib-test",
            "date": "2026-10-25",
            "status": "new",
            "kind": "lesson",
            "text": "Hallazgo ya documentado.",
            "source": "test",
        }

    @staticmethod
    def args(ref):
        return SimpleNamespace(
            icmd="triage", id="ib-test", to="lesson", ref=ref,
            text=None, topics=None, roles=None, area=None, bkind=None, priority=2,
        )

    def test_existing_lesson_is_linked_without_running_lessons_add(self):
        saved = []

        with (
            mock.patch.object(kb.inbox_hook, "load_inbox", return_value=[self.item]),
            mock.patch.object(kb.lessons_db, "load", return_value=[{"id": "existing-lesson"}]),
            mock.patch.object(kb.lessons_db, "save") as lesson_save,
            mock.patch.object(kb, "inbox_save", side_effect=lambda items: saved.extend(items)),
            mock.patch("subprocess.run") as run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            kb.cmd_inbox(self.args("existing-lesson"))

        run.assert_not_called()
        lesson_save.assert_not_called()
        self.assertEqual("triaged", saved[0]["status"])
        self.assertEqual("lesson", saved[0]["to"])
        self.assertEqual("existing-lesson", saved[0]["ref"])

    def test_new_lesson_keeps_the_lessons_add_path(self):
        completed = subprocess.CompletedProcess([], 0, "added new-lesson\n", "")
        saved = []

        with (
            mock.patch.object(kb.inbox_hook, "load_inbox", return_value=[self.item]),
            mock.patch.object(kb.lessons_db, "load", return_value=[]),
            mock.patch.object(kb, "inbox_save", side_effect=lambda items: saved.extend(items)),
            mock.patch("subprocess.run", return_value=completed) as run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            kb.cmd_inbox(self.args("new-lesson"))

        run.assert_called_once()
        command = run.call_args.args[0]
        self.assertIn("add", command)
        self.assertEqual("new-lesson", command[command.index("--id") + 1])
        self.assertEqual("new-lesson", saved[0]["ref"])

    def test_lesson_without_reference_is_rejected_without_writes(self):
        with (
            mock.patch.object(kb.inbox_hook, "load_inbox", return_value=[self.item]),
            mock.patch.object(kb, "inbox_save") as inbox_save,
            self.assertRaisesRegex(SystemExit, "needs --ref LESSON_ID"),
        ):
            kb.cmd_inbox(self.args(None))

        inbox_save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
