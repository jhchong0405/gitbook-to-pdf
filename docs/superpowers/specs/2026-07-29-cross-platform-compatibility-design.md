# Cross-Platform Compatibility Design

## Context

GitHub Issue #1 reports that importing `gitbook_to_pdf.py` immediately
configures `pdfkit` with a Windows-only path:
`C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe`. That import-time side
effect breaks Linux and macOS, and it also breaks the Chrome print method even
though that method does not use wkhtmltopdf.

The repository contains one Python program, one dependency file, and a README.
The compatibility audit also found fixed working-directory artifacts
(`images/`, `temp_pdfs/`, and `temp.html`) and documentation that claims Python
3.6 support even though the pinned Selenium and urllib3 releases require
Python 3.8 or newer.

## Goals

- Support Windows, macOS, and Linux with Python 3.8 or newer.
- Ensure the print method never discovers or configures wkhtmltopdf.
- Let the HTML method use either an explicit executable path or a
  `wkhtmltopdf` executable available on `PATH`.
- Keep generated intermediate files isolated from the caller's working
  directory and clean them up on success and failure.
- Preserve the existing conversion behavior, output defaults, dependency
  versions, and public class entry point.
- Add automated regression coverage for executable discovery, method
  isolation, temporary-workspace cleanup, and CLI argument forwarding.
- Correct compatibility and installation guidance in the README.

## Non-Goals

- Rewriting the crawler, changing page traversal, or altering PDF styling.
- Upgrading or unpinning third-party dependencies.
- Making paper size, margins, delays, and browser flags user-configurable.
  These values are conversion-policy constants rather than operating-system
  paths or resource locations.
- Adding support for browsers other than Chrome.
- Performing live website-to-PDF integration tests in the unit-test suite.

## Approaches Considered

### 1. Remove the explicit configuration

Call `pdfkit.from_file` without a configuration and rely on pdfkit to locate
wkhtmltopdf.

This is the smallest Issue #1 fix, but it provides no explicit override for
non-standard installations and does not address fixed temporary paths or
resource cleanup.

### 2. Add a focused portability layer

Resolve wkhtmltopdf only when the HTML method runs, with precedence:
`--wkhtmltopdf PATH`, then the system `PATH`. Give missing or invalid
executables a concise error. Use a per-converter system temporary directory
and deterministic cleanup. Test these boundaries with the standard library
`unittest` framework.

This is the selected approach because it fixes the reported failure, supports
standard and custom installations across operating systems, and addresses the
other concrete path-related compatibility risks without redesigning the
converter.

### 3. Modernize the whole project

Package the tool, replace pdfkit/wkhtmltopdf, upgrade dependencies, add a new
configuration system, and restructure the crawler.

This could improve long-term maintenance, but it is much broader than the
reported defect and would introduce unrelated behavior and dependency risk.

## Design

### Executable discovery

Add a small helper that resolves wkhtmltopdf:

1. If an explicit path is supplied, expand the user component and require an
   existing executable file.
2. Otherwise, use `shutil.which("wkhtmltopdf")`.
3. If neither succeeds, raise a clear error that explains both installation
   choices.

Remove the module-level Windows path and `pdfkit.configuration` call.
`GitbookToPDF` stores the optional path but does not resolve it during
construction. The HTML branch of `generate_pdf` resolves it immediately before
calling `pdfkit.from_file`. The print branch never calls the resolver or
`pdfkit.configuration`.

Add `--wkhtmltopdf PATH` to the CLI. It is optional and only affects the HTML
method. The default method remains `html` to preserve the existing interface.

### Temporary resources

Each `GitbookToPDF` instance owns one `tempfile.TemporaryDirectory` workspace.
Downloaded images, per-page print PDFs, and the combined HTML file live under
that workspace instead of fixed paths in the process working directory.

The converter exposes context-manager cleanup through `__enter__` and
`__exit__`, backed by an idempotent `close()` method. `close()` quits an
initialized Chrome driver and removes the temporary workspace. `main()` uses
the converter as a context manager so cleanup occurs on normal completion and
exceptions. Initialization also cleans the workspace if Chrome setup fails.

The requested final output remains at the user-provided path and is never
removed by workspace cleanup.

### Error handling

Invalid explicit wkhtmltopdf paths and missing `PATH` discoveries produce
actionable messages instead of a Windows-specific import error. CLI execution
reports the message and exits non-zero. Print-mode Chrome setup retains its
existing fallback from Selenium Manager to webdriver-manager, while lifecycle
cleanup prevents a started driver from being left open by later failures.

### Documentation

Update the README to:

- state Python 3.8+ because that is the minimum imposed by pinned dependencies;
- use the real repository clone URL;
- explain PATH-based discovery and `--wkhtmltopdf PATH` examples;
- state explicitly that print mode does not initialize wkhtmltopdf;
- remove fixed intermediate directories from the documented repository tree;
- describe automatic temporary-resource cleanup.

The missing `LICENSE` file claim is outside this compatibility change and will
not be altered without a separate licensing decision.

## Testing

Use `unittest` and `unittest.mock`, adding no test dependency.

Regression tests will prove:

- importing the module has no wkhtmltopdf configuration side effect;
- explicit executable paths are accepted and invalid paths fail clearly;
- PATH discovery is used when no explicit path is supplied;
- print-mode construction and generation do not configure wkhtmltopdf;
- two converter instances receive different temporary workspaces;
- closing a converter quits its driver at most once and removes its workspace;
- CLI parsing forwards `--wkhtmltopdf` to the converter;
- HTML conversion passes the lazily created configuration to pdfkit.

Tests will mock external browsers, network access, and PDF generation only at
those process boundaries. They will exercise real path and cleanup behavior in
temporary directories.

## Verification

Before publication:

1. Run the complete unit-test suite.
2. Compile the Python source.
3. Run CLI help to verify the new option without external executables.
4. Run static searches for absolute Windows/POSIX executable paths and the old
   fixed intermediate names.
5. Run `git diff --check` and review the complete branch diff.
6. Push the branch and verify the remote commit.
7. Reply to Issue #1 with the root cause, behavior change, tests, and commit or
   pull-request link, then close it as completed.
