import os
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch

import gitbook_to_pdf


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


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


class ConversionMethodIsolationTests(unittest.TestCase):
    @patch("gitbook_to_pdf.pdfkit.from_file")
    @patch("gitbook_to_pdf.pdfkit.configuration")
    @patch(
        "gitbook_to_pdf.resolve_wkhtmltopdf",
        return_value="/custom/wkhtmltopdf",
    )
    def test_html_method_configures_only_when_generating(
        self,
        resolve,
        configuration,
        from_file,
    ):
        configuration.return_value = object()

        with tempfile.TemporaryDirectory() as directory:
            with working_directory(directory):
                converter = gitbook_to_pdf.GitbookToPDF(
                    "https://example.com",
                    method="html",
                    wkhtmltopdf_path="/custom/wkhtmltopdf",
                )
                converter.download_css = Mock(return_value="")
                converter.generate_pdf("output.pdf")

        resolve.assert_called_once_with("/custom/wkhtmltopdf")
        configuration.assert_called_once_with(
            wkhtmltopdf="/custom/wkhtmltopdf"
        )
        self.assertEqual(from_file.call_count, 1)
        self.assertIs(
            from_file.call_args.kwargs["configuration"],
            configuration.return_value,
        )

    @patch("gitbook_to_pdf.pdfkit.configuration")
    @patch("gitbook_to_pdf.setup_chrome_driver")
    def test_print_method_never_configures_wkhtmltopdf(
        self,
        setup_driver,
        configuration,
    ):
        with tempfile.TemporaryDirectory() as directory:
            with working_directory(directory):
                converter = gitbook_to_pdf.GitbookToPDF(
                    "https://example.com",
                    method="print",
                )
                converter.print_to_pdf = Mock(return_value=None)
                converter.get_all_links = Mock(return_value=[])
                converter.generate_pdf("output.pdf")

        configuration.assert_not_called()
        setup_driver.return_value.quit.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
