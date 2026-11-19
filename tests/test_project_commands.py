"""k6 must be able to write reports to a runner-owned Linux bind mount."""
import importlib.util
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("project_cli", ROOT / "scripts/project.py")
project = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(project)


class LoadCommandTests(unittest.TestCase):
    def invoke(self, system):
        with mock.patch.object(project, "init"), mock.patch.object(project, "run") as run, \
             mock.patch.object(project.sys, "argv", ["project.py", "load", "--profile", "smoke"]), \
             mock.patch.object(project.os, "name", system), \
             mock.patch.object(project.os, "getuid", return_value=1001, create=True), \
             mock.patch.object(project.os, "getgid", return_value=127, create=True):
            project.main()
        return run.call_args

    def test_linux_uses_the_host_identity_for_report_permissions(self):
        call = self.invoke("posix")
        self.assertEqual(call.args, ("docker", "compose", "--profile", "load", "run", "--rm",
                                     "--user", "1001:127", "k6"))
        self.assertEqual(call.kwargs["env"]["LOAD_PROFILE"], "smoke")

    def test_windows_preserves_the_image_user(self):
        call = self.invoke("nt")
        self.assertNotIn("--user", call.args)
        self.assertEqual(call.args[-1], "k6")


if __name__ == "__main__":
    unittest.main()
