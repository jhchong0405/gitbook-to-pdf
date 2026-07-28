# Cross-Platform Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix GitHub Issue #1 and remove the codebase's concrete operating-system path and temporary-resource compatibility failures without changing conversion behavior.

**Architecture:** Replace import-time wkhtmltopdf configuration with a small lazy resolver used only by the HTML conversion path. Give each converter an isolated system temporary workspace with explicit lifecycle cleanup, then expose the custom executable path through the existing CLI and document the supported platforms.

**Tech Stack:** Python 3.8+, standard-library `unittest`, `pathlib`, `shutil`, `tempfile`, pdfkit 1.0.0, Selenium 4.16.0, Git, GitHub CLI.

---

## File Map

- Create `tests/__init__.py`: mark the standard-library test package.
- Create `tests/test_gitbook_to_pdf.py`: regression coverage for import isolation,
  executable resolution, method isolation, temporary resources, and CLI flow.
- Modify `gitbook_to_pdf.py`: lazy wkhtmltopdf resolution, temporary workspace
  lifecycle, CLI option, and actionable errors.
- Modify `.gitignore`: ignore the local `.venv` used for verification and remove
  obsolete fixed-artifact entries after the runtime stops creating them.
- Modify `README.md`: correct platform, Python, clone, executable-discovery, and
  temporary-resource guidance.

### Task 1: Establish import-isolation regression coverage

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_gitbook_to_pdf.py`
- Modify: `.gitignore`
- Modify: `gitbook_to_pdf.py:26-28`
- Modify: `gitbook_to_pdf.py:401-425`

- [ ] **Step 1: Ignore the verification environment**

Add this entry under the virtual-environment section of `.gitignore`:

```gitignore
.venv/
```

- [ ] **Step 2: Create and populate a local virtual environment**

Run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Expected: all pinned runtime dependencies install successfully under Python
3.11, and `git status --short` does not list `.venv`.

- [ ] **Step 3: Write the failing import-side-effect test**

Create `tests/__init__.py`:

```python
"""Regression tests for gitbook-to-pdf."""
```

Create `tests/test_gitbook_to_pdf.py`:

```python
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
            msg=f"stdout:\\n{result.stdout}\\nstderr:\\n{result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run the test and verify the reported defect is reproduced**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_gitbook_to_pdf.ImportIsolationTests -v
```

Expected: FAIL because importing `gitbook_to_pdf` calls the mocked
`pdfkit.configuration`.

- [ ] **Step 5: Remove the import-time Windows configuration**

Delete this complete block from `gitbook_to_pdf.py`:

```python
# 配置 wkhtmltopdf 路径
WKHTMLTOPDF_PATH = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
```

Immediately before the HTML conversion `try` block, add:

```python
        pdfkit_config = pdfkit.configuration()
```

Replace the existing `pdfkit.from_file` call with:

```python
            pdfkit.from_file(
                temp_html,
                output_file,
                options=options,
                configuration=pdfkit_config,
            )
```

This preserves PATH-based HTML conversion while moving configuration out of
module import. Task 3 will add the explicit executable override.

- [ ] **Step 6: Run the import test and verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_gitbook_to_pdf.ImportIsolationTests -v
```

Expected: PASS with one test.

- [ ] **Step 7: Commit the import-isolation fix**

```powershell
git add -- .gitignore tests/__init__.py tests/test_gitbook_to_pdf.py gitbook_to_pdf.py
git commit -m "Fix import-time wkhtmltopdf dependency"
```

### Task 2: Resolve wkhtmltopdf portably

**Files:**
- Modify: `tests/test_gitbook_to_pdf.py`
- Modify: `gitbook_to_pdf.py:1-25`
- Modify: `gitbook_to_pdf.py:26`

- [ ] **Step 1: Add failing resolver tests**

Add these imports to `tests/test_gitbook_to_pdf.py`:

```python
import os
import stat
import tempfile
from unittest.mock import patch

import gitbook_to_pdf
```

Add this test class before the `if __name__ == "__main__"` block:

```python
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
```

- [ ] **Step 2: Run the resolver tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_gitbook_to_pdf.WkhtmltopdfResolutionTests -v
```

Expected: ERROR because `resolve_wkhtmltopdf` and the new imports do not exist
yet.

- [ ] **Step 3: Implement the resolver**

Add these imports to `gitbook_to_pdf.py`:

```python
from pathlib import Path
import shutil
```

Add this helper after the imports:

```python
def resolve_wkhtmltopdf(explicit_path=None):
    """Return a validated wkhtmltopdf executable path."""
    if explicit_path:
        candidate = Path(explicit_path).expanduser().resolve()
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            raise FileNotFoundError(
                f"wkhtmltopdf path '{explicit_path}' does not point to "
                "an executable file."
            )
        return str(candidate)

    discovered = shutil.which("wkhtmltopdf")
    if discovered:
        return discovered

    raise FileNotFoundError(
        "wkhtmltopdf was not found. Install it on PATH or pass "
        "--wkhtmltopdf with the executable path."
    )
```

- [ ] **Step 4: Run the resolver and import tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_gitbook_to_pdf.ImportIsolationTests `
  tests.test_gitbook_to_pdf.WkhtmltopdfResolutionTests -v
```

Expected: PASS with five tests.

- [ ] **Step 5: Commit portable executable discovery**

```powershell
git add -- tests/test_gitbook_to_pdf.py gitbook_to_pdf.py
git commit -m "Add portable wkhtmltopdf discovery"
```

### Task 3: Keep HTML configuration lazy and print mode independent

**Files:**
- Modify: `tests/test_gitbook_to_pdf.py`
- Modify: `gitbook_to_pdf.py:69-88`
- Modify: `gitbook_to_pdf.py:294-428`

- [ ] **Step 1: Add a temporary working-directory helper and failing method tests**

Add this import to `tests/test_gitbook_to_pdf.py`:

```python
from contextlib import contextmanager
from unittest.mock import Mock
```

Add this helper after `REPOSITORY_ROOT`:

```python
@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)
```

Add this test class:

```python
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
```

- [ ] **Step 2: Run the method-isolation tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_gitbook_to_pdf.ConversionMethodIsolationTests -v
```

Expected: ERROR because `GitbookToPDF.__init__` does not accept
`wkhtmltopdf_path`, and HTML generation does not resolve the requested
executable path.

- [ ] **Step 3: Store the optional executable path without resolving it**

Replace the constructor signature and method assignment with:

```python
class GitbookToPDF:
    def __init__(self, base_url, method='html', wkhtmltopdf_path=None):
        self.base_url = base_url
        self.visited_urls = set()
        self.all_content = []
        self.session = requests.Session()
        self.css_files = set()
        self.title = ""
        self.images = {}
        self.image_dir = "images"
        self.method = method
        self.wkhtmltopdf_path = wkhtmltopdf_path
        self.temp_dir = "temp_pdfs"
```

- [ ] **Step 4: Configure pdfkit inside the HTML branch**

Immediately before the HTML method creates `temp_html`, add:

```python
        wkhtmltopdf_executable = resolve_wkhtmltopdf(
            self.wkhtmltopdf_path
        )
        pdfkit_config = pdfkit.configuration(
            wkhtmltopdf=wkhtmltopdf_executable
        )
```

Replace the `pdfkit.from_file` call with:

```python
            pdfkit.from_file(
                temp_html,
                output_file,
                options=options,
                configuration=pdfkit_config,
            )
```

- [ ] **Step 5: Run all tests and verify lazy isolation**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: PASS with seven tests.

- [ ] **Step 6: Commit method isolation**

```powershell
git add -- tests/test_gitbook_to_pdf.py gitbook_to_pdf.py
git commit -m "Keep PDF backends isolated"
```

### Task 4: Isolate and clean temporary resources

**Files:**
- Modify: `tests/test_gitbook_to_pdf.py`
- Modify: `gitbook_to_pdf.py:1-25`
- Modify: `gitbook_to_pdf.py:69-136`
- Modify: `gitbook_to_pdf.py:294-433`

- [ ] **Step 1: Add failing workspace lifecycle tests**

Add this test class:

```python
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
```

- [ ] **Step 2: Run the workspace tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_gitbook_to_pdf.TemporaryWorkspaceTests -v
```

Expected: ERROR because `workspace_dir`, `close`, and context-manager methods do
not exist; the current implementation also creates fixed caller directories.

- [ ] **Step 3: Create an isolated workspace during construction**

Add this import to `gitbook_to_pdf.py`:

```python
import tempfile
```

Replace the constructor's fixed-directory and driver setup section with:

```python
        self.method = method
        self.wkhtmltopdf_path = wkhtmltopdf_path
        self.driver = None
        self._temporary_directory = tempfile.TemporaryDirectory(
            prefix="gitbook-to-pdf-"
        )
        self.workspace_dir = Path(self._temporary_directory.name)
        self.image_dir = self.workspace_dir / "images"
        self.temp_dir = self.workspace_dir / "pages"
        self.image_dir.mkdir()
        self.temp_dir.mkdir()

        try:
            if self.method == 'print':
                self.driver = setup_chrome_driver()
        except Exception:
            self._temporary_directory.cleanup()
            self._temporary_directory = None
            raise
```

- [ ] **Step 4: Add deterministic lifecycle methods**

Add these methods immediately after `__init__`:

```python
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    def close(self):
        """Release browser and temporary workspace resources."""
        if self.driver is not None:
            driver = self.driver
            self.driver = None
            driver.quit()

        if self._temporary_directory is not None:
            temporary_directory = self._temporary_directory
            self._temporary_directory = None
            temporary_directory.cleanup()
```

- [ ] **Step 5: Put the HTML document inside the workspace**

Replace:

```python
        temp_html = 'temp.html'
```

with:

```python
        temp_html = str(self.workspace_dir / "document.html")
```

Remove this cleanup block because workspace cleanup owns the file:

```python
        finally:
            if os.path.exists(temp_html):
                os.remove(temp_html)
```

Retain the HTML conversion `try`/`except` block without a `finally` clause.

- [ ] **Step 6: Leave driver shutdown to `close()`**

Delete this line from the print branch of `generate_pdf`:

```python
            self.driver.quit()
```

Update the print-method isolation test by adding:

```python
                converter.close()
```

immediately after `converter.generate_pdf("output.pdf")`.

- [ ] **Step 7: Run the full test suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: PASS with ten tests and no `images`, `temp_pdfs`, or `temp.html`
created in the repository.

- [ ] **Step 8: Commit temporary-resource isolation**

```powershell
git add -- tests/test_gitbook_to_pdf.py gitbook_to_pdf.py
git commit -m "Isolate temporary conversion resources"
```

### Task 5: Expose the override and return actionable CLI errors

**Files:**
- Modify: `tests/test_gitbook_to_pdf.py`
- Modify: `gitbook_to_pdf.py:30-67`
- Modify: `gitbook_to_pdf.py:435-451`

- [ ] **Step 1: Add failing CLI tests**

Add these imports to `tests/test_gitbook_to_pdf.py`:

```python
import io
from contextlib import redirect_stderr
```

Add this test class:

```python
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
```

- [ ] **Step 2: Run the CLI tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_gitbook_to_pdf.CommandLineTests -v
```

Expected: ERROR because `main` does not accept an argument list, does not expose
`--wkhtmltopdf`, and does not use the converter as a context manager.

- [ ] **Step 3: Make Chrome setup raise an exception instead of exiting**

Replace the outer exception handler in `setup_chrome_driver` with:

```python
    except Exception as error:
        raise RuntimeError(
            "Could not start Chrome. Ensure Google Chrome is installed."
        ) from error
```

Remove the now-unused `import sys`.

- [ ] **Step 4: Extract parser construction and update `main`**

Replace the complete existing `main` function with:

```python
def build_parser():
    parser = argparse.ArgumentParser(
        description='Convert GitBook to PDF'
    )
    parser.add_argument(
        'url',
        help='The URL of the GitBook main page',
    )
    parser.add_argument(
        '--output',
        '-o',
        default='output.pdf',
        help='Output PDF file name',
    )
    parser.add_argument(
        '--method',
        '-m',
        choices=['html', 'print'],
        default='html',
        help='Conversion method: html (wkhtmltopdf) or print (Chrome)',
    )
    parser.add_argument(
        '--wkhtmltopdf',
        metavar='PATH',
        help='Path to wkhtmltopdf for the html method; defaults to PATH',
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        with GitbookToPDF(
            args.url,
            method=args.method,
            wkhtmltopdf_path=args.wkhtmltopdf,
        ) as converter:
            print("Starting to crawl the GitBook...")
            if args.method == 'html':
                converter.get_page_content(args.url)
            print("Generating PDF...")
            converter.generate_pdf(args.output)
    except (FileNotFoundError, RuntimeError) as error:
        parser.exit(1, f"Error: {error}\n")
```

Keep this module entry point unchanged:

```python
if __name__ == '__main__':
    main()
```

- [ ] **Step 5: Run the CLI and full tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe gitbook_to_pdf.py --help
```

Expected: twelve tests pass, and help contains
`[--wkhtmltopdf PATH]`.

- [ ] **Step 6: Commit the CLI compatibility behavior**

```powershell
git add -- tests/test_gitbook_to_pdf.py gitbook_to_pdf.py
git commit -m "Add wkhtmltopdf CLI override"
```

### Task 6: Correct compatibility documentation

**Files:**
- Modify: `README.md`
- Modify: `.gitignore`

- [ ] **Step 1: Update prerequisites and clone instructions**

Set the Python prerequisite to:

```markdown
1. Python 3.8 or higher
```

Replace the clone command with:

```bash
git clone https://github.com/jhchong0405/gitbook-to-pdf.git
cd gitbook-to-pdf
```

- [ ] **Step 2: Document wkhtmltopdf discovery and overrides**

Add this text to the HTML method section:

````markdown
The HTML method looks for `wkhtmltopdf` on your system `PATH`. If it is
installed elsewhere, provide its executable explicitly:

```bash
# Linux or macOS
python gitbook_to_pdf.py https://your-gitbook-url.com -m html \
  --wkhtmltopdf /opt/wkhtmltopdf/bin/wkhtmltopdf

# Windows PowerShell
python gitbook_to_pdf.py https://your-gitbook-url.com -m html `
  --wkhtmltopdf "C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
```
````

Add this command-line argument:

```markdown
- `--wkhtmltopdf PATH`: Optional wkhtmltopdf executable path for the HTML
  method; when omitted, the executable is discovered from `PATH`
```

State in the print section:

```markdown
Print mode does not discover, configure, or require wkhtmltopdf.
```

- [ ] **Step 3: Document temporary-resource cleanup**

Replace the directory tree with only tracked repository files:

```text
gitbook-to-pdf/
├── gitbook_to_pdf.py
├── requirements.txt
├── tests/
├── docs/
├── README.md
└── .gitignore
```

Add:

```markdown
Downloaded images, per-page PDFs, and intermediate HTML are created in an
isolated system temporary directory and removed automatically. Only the final
output PDF is retained.
```

- [ ] **Step 4: Remove obsolete ignore entries**

Remove these fixed runtime artifacts from `.gitignore`:

```gitignore
temp.html
images/
```

Keep `*.pdf` so generated output files are not committed accidentally.

- [ ] **Step 5: Verify the documentation claims**

Run:

```powershell
rg -n "Python 3\.8|jhchong0405/gitbook-to-pdf|--wkhtmltopdf|does not .*require wkhtmltopdf|temporary directory" README.md
rg -n "Python 3\.6|yourusername|temp_pdfs" README.md
```

Expected: the first command finds every new compatibility claim; the second
command returns no matches.

- [ ] **Step 6: Commit documentation**

```powershell
git add -- README.md .gitignore
git commit -m "Document cross-platform setup"
```

### Task 7: Verify, publish, merge, and resolve Issue #1

**Files:**
- Verify all changed files
- No new production files

- [ ] **Step 1: Run complete local verification**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m py_compile gitbook_to_pdf.py tests/test_gitbook_to_pdf.py
.\.venv\Scripts\python.exe gitbook_to_pdf.py --help
git diff main...HEAD --check
git status -sb
```

Expected:

- twelve tests pass with zero failures or errors;
- compilation exits zero;
- CLI help includes `--wkhtmltopdf PATH`;
- the diff check prints no errors;
- only the intended branch is reported, with no untracked or modified files.

- [ ] **Step 2: Re-run the hard-coded path audit**

Run:

```powershell
rg -n "Program Files|WKHTMLTOPDF_PATH|pdfkit\.configuration" gitbook_to_pdf.py
rg -n "temp\.html|temp_pdfs|image_dir = \"images\"" gitbook_to_pdf.py README.md
```

Expected:

- no absolute Windows executable or module-level configuration remains;
- the only `pdfkit.configuration` match is inside HTML generation;
- no caller-working-directory artifact assignments remain.

- [ ] **Step 3: Review the complete change**

Run:

```powershell
git log --oneline main..HEAD
git diff --stat main...HEAD
git diff main...HEAD
```

Expected: the diff contains only the approved design, tests, portability
changes, and README/.gitignore corrections.

- [ ] **Step 4: Push the feature branch**

Run:

```powershell
git push -u origin codex/fix-cross-platform-compatibility
```

Expected: the remote branch is created and tracks `origin`.

- [ ] **Step 5: Open a ready pull request**

Create a pull request from `codex/fix-cross-platform-compatibility` to `main`
with this title:

```text
Fix cross-platform wkhtmltopdf handling
```

Use this body:

```markdown
## Summary

- remove the import-time Windows-only wkhtmltopdf path
- resolve wkhtmltopdf lazily from `--wkhtmltopdf` or `PATH`
- keep Chrome print mode independent from wkhtmltopdf
- isolate and clean intermediate conversion files
- add regression tests and correct compatibility documentation

## Root cause

`pdfkit.configuration` ran during module import with a hard-coded Windows
executable. This failed before the selected conversion method could run.

## Validation

- `python -m unittest discover -s tests -v`
- `python -m py_compile gitbook_to_pdf.py tests/test_gitbook_to_pdf.py`
- `python gitbook_to_pdf.py --help`
- `git diff main...HEAD --check`

References #1
```

Create it as ready for review, not draft.

- [ ] **Step 6: Merge the verified pull request**

Merge the pull request into `main` without deleting the feature branch.

Expected: the pull request reports `MERGED`, and the remote `main` head contains
all compatibility commits.

- [ ] **Step 7: Verify the remote main branch**

Run:

```powershell
gh repo view jhchong0405/gitbook-to-pdf --json defaultBranchRef
gh api repos/jhchong0405/gitbook-to-pdf/commits/main --jq '.sha'
```

Expected: the default branch is `main`, and the returned SHA matches the merged
pull request head or merge commit.

- [ ] **Step 8: Reply to Issue #1**

Read the merged pull-request metadata and construct the comment from those live
values:

```powershell
$pullRequest = gh pr view codex/fix-cross-platform-compatibility `
  --json number,url,mergeCommit | ConvertFrom-Json
$issueComment = @"
Fixed and merged.

The root cause was the module-level ``pdfkit.configuration`` call using a
Windows-only executable path. The converter now:

- does not initialize wkhtmltopdf when using ``-m print``;
- discovers wkhtmltopdf from ``PATH`` for ``-m html``;
- supports custom installations through ``--wkhtmltopdf PATH``;
- uses isolated, automatically cleaned temporary files; and
- documents Python 3.8+ and Windows/macOS/Linux setup.

Regression tests cover import isolation, executable discovery, backend
isolation, cleanup, and CLI error handling.

Pull request: $($pullRequest.url)
Merged commit: ``$($pullRequest.mergeCommit.oid)``
"@
gh issue comment 1 --repo jhchong0405/gitbook-to-pdf --body $issueComment
```

Expected: GitHub returns the URL of the new Issue #1 comment.

- [ ] **Step 9: Close Issue #1 as completed**

Close `jhchong0405/gitbook-to-pdf#1` with the completed reason, then read it
back and verify that the final state is `CLOSED` and the comment is present.

Run:

```powershell
gh issue close 1 --repo jhchong0405/gitbook-to-pdf --reason completed
gh issue view 1 --repo jhchong0405/gitbook-to-pdf `
  --json state,comments `
  --jq '{state: .state, lastComment: .comments[-1].body}'
```

Expected: state is `CLOSED`, and the last comment starts with
`Fixed and merged.`
