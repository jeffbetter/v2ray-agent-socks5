"""Check that the short launcher preserves the installer on failed downloads."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class LauncherTests(unittest.TestCase):
    def launch(self, payload, download_status=0):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "install.sh").write_text("existing installer\n")
            (root / "payload").write_text(payload)
            binary = root / "bin"
            binary.mkdir()
            for name, source in {
                "id": "#!/bin/sh\necho 0\n",
                "curl": '#!/bin/sh\nwhile [ "$1" != -o ]; do shift; done\ncp "$LAUNCH_ROOT/payload" "$2"\nexit "$DOWNLOAD_STATUS"\n',
            }.items():
                target = binary / name
                target.write_text(source)
                target.chmod(0o700)
            source = (Path(__file__).parent / "start.sh").read_text()
            source = source.replace("/root/", str(root) + "/")
            result = subprocess.run(["sh", "-c", source], capture_output=True, text=True,
                                    env={**os.environ, "PATH": str(binary) + os.pathsep + os.environ["PATH"],
                                         "LAUNCH_ROOT": directory, "DOWNLOAD_STATUS": str(download_status)})
            return result, (root / "install.sh").read_text(), list(root.glob(".v2ray-agent-install.*"))

    def test_complete_script_is_saved_and_executed(self):
        payload = '#!/bin/bash\nprintf "LAUNCHED\\n"\n'
        result, saved, leftovers = self.launch(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(saved, payload)
        self.assertEqual(result.stdout, "LAUNCHED\n")
        self.assertEqual(leftovers, [])

    def test_failed_empty_or_invalid_download_preserves_existing_installer(self):
        for payload, status in (("partial download", 22), ("", 0), ("if then\n", 0)):
            with self.subTest(payload=payload):
                result, saved, leftovers = self.launch(payload, status)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(saved, "existing installer\n")
                self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
