import subprocess
import sys
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
