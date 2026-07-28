import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import gitbook_to_pdf


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class ImportIsolationTests(unittest.TestCase):
    def test_import_does_not_configure_wkhtmltopdf(self):
        code = """
from unittest.mock import Mock
import pdfkit

pdfkit.configuration = Mock(
    side_effect=AssertionError("pdfkit.configuration called during import")
)
import gitbook_to_pdf
"""

        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )


class WkhtmltopdfResolutionTests(unittest.TestCase):
    def test_explicit_executable_path_takes_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / (
                "wkhtmltopdf.exe" if os.name == "nt" else "wkhtmltopdf"
            )
            executable.write_bytes(b"")
            executable.chmod(executable.stat().st_mode | stat.S_IEXEC)

            with patch("gitbook_to_pdf.shutil.which") as which:
                resolved = gitbook_to_pdf.resolve_wkhtmltopdf(str(executable))

            self.assertEqual(resolved, str(executable.resolve()))
            which.assert_not_called()

    def test_invalid_explicit_path_fails_clearly(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing-wkhtmltopdf"

            with self.assertRaisesRegex(
                FileNotFoundError, "does not point to an executable file"
            ):
                gitbook_to_pdf.resolve_wkhtmltopdf(str(missing))

    @patch(
        "gitbook_to_pdf.shutil.which",
        return_value="/usr/local/bin/wkhtmltopdf",
    )
    def test_path_discovery_is_used_without_override(self, which):
        resolved = gitbook_to_pdf.resolve_wkhtmltopdf()

        self.assertEqual(resolved, "/usr/local/bin/wkhtmltopdf")
        which.assert_called_once_with("wkhtmltopdf")

    @patch("gitbook_to_pdf.shutil.which", return_value=None)
    def test_missing_path_discovery_has_installation_guidance(self, which):
        with self.assertRaisesRegex(
            FileNotFoundError,
            "Install it on PATH or pass --wkhtmltopdf",
        ):
            gitbook_to_pdf.resolve_wkhtmltopdf()

        which.assert_called_once_with("wkhtmltopdf")


if __name__ == "__main__":
    unittest.main()
