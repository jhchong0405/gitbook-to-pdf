import io
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr
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
                converter.close()

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
                converter.close()

        configuration.assert_not_called()
        setup_driver.return_value.quit.assert_called_once_with()


class TemporaryWorkspaceTests(unittest.TestCase):
    def test_workspaces_are_unique_and_do_not_pollute_the_caller(self):
        with tempfile.TemporaryDirectory() as caller_directory:
            with working_directory(caller_directory):
                first = gitbook_to_pdf.GitbookToPDF(
                    "https://example.com",
                    method="html",
                )
                second = gitbook_to_pdf.GitbookToPDF(
                    "https://example.com",
                    method="html",
                )
                first_workspace = Path(first.workspace_dir)
                second_workspace = Path(second.workspace_dir)

                self.assertNotEqual(first_workspace, second_workspace)
                self.assertTrue(Path(first.image_dir).is_dir())
                self.assertTrue(Path(first.temp_dir).is_dir())
                self.assertFalse(Path("images").exists())
                self.assertFalse(Path("temp_pdfs").exists())

                first.close()
                second.close()

                self.assertFalse(first_workspace.exists())
                self.assertFalse(second_workspace.exists())

    @patch("gitbook_to_pdf.setup_chrome_driver")
    def test_close_quits_driver_once_and_is_idempotent(self, setup_driver):
        converter = gitbook_to_pdf.GitbookToPDF(
            "https://example.com",
            method="print",
        )
        workspace = Path(converter.workspace_dir)

        converter.close()
        converter.close()

        setup_driver.return_value.quit.assert_called_once_with()
        self.assertFalse(workspace.exists())

    @patch("gitbook_to_pdf.setup_chrome_driver")
    def test_context_manager_cleans_after_an_exception(self, setup_driver):
        with self.assertRaisesRegex(RuntimeError, "conversion failed"):
            with gitbook_to_pdf.GitbookToPDF(
                "https://example.com",
                method="print",
            ) as converter:
                workspace = Path(converter.workspace_dir)
                raise RuntimeError("conversion failed")

        setup_driver.return_value.quit.assert_called_once_with()
        self.assertFalse(workspace.exists())

    @patch("gitbook_to_pdf.setup_chrome_driver")
    def test_close_cleans_workspace_when_driver_quit_fails(
        self,
        setup_driver,
    ):
        setup_driver.return_value.quit.side_effect = RuntimeError(
            "quit failed"
        )
        converter = gitbook_to_pdf.GitbookToPDF(
            "https://example.com",
            method="print",
        )
        workspace = Path(converter.workspace_dir)

        with self.assertRaisesRegex(RuntimeError, "quit failed"):
            converter.close()

        self.assertFalse(workspace.exists())


class CommandLineTests(unittest.TestCase):
    @patch("gitbook_to_pdf.GitbookToPDF")
    def test_wkhtmltopdf_override_is_forwarded(self, converter_class):
        converter = converter_class.return_value.__enter__.return_value

        gitbook_to_pdf.main(
            [
                "https://example.com",
                "--method",
                "html",
                "--output",
                "book.pdf",
                "--wkhtmltopdf",
                "/custom/wkhtmltopdf",
            ]
        )

        converter_class.assert_called_once_with(
            "https://example.com",
            method="html",
            wkhtmltopdf_path="/custom/wkhtmltopdf",
        )
        converter.get_page_content.assert_called_once_with(
            "https://example.com"
        )
        converter.generate_pdf.assert_called_once_with("book.pdf")

    @patch("gitbook_to_pdf.GitbookToPDF")
    def test_missing_executable_exits_nonzero_without_traceback(
        self,
        converter_class,
    ):
        converter = converter_class.return_value.__enter__.return_value
        converter.generate_pdf.side_effect = FileNotFoundError(
            "wkhtmltopdf was not found"
        )
        error_output = io.StringIO()

        with redirect_stderr(error_output):
            with self.assertRaises(SystemExit) as raised:
                gitbook_to_pdf.main(["https://example.com"])

        self.assertEqual(raised.exception.code, 1)
        self.assertIn(
            "Error: wkhtmltopdf was not found",
            error_output.getvalue(),
        )
        self.assertNotIn("Traceback", error_output.getvalue())


if __name__ == "__main__":
    unittest.main()
