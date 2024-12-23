# GitBook to PDF Converter

A Python tool that converts GitBook documentation into a well-formatted PDF file.

## Features

- Automatically crawls all pages from a GitBook website
- Maintains original styling and formatting
- Includes CSS styles and images
- Generates a professional PDF with:
  - Page numbers
  - Headers and footers
  - Table of contents
  - Proper page breaks
  - Clean typography

## Prerequisites

- Python 3.6+
- wkhtmltopdf (Download from: https://wkhtmltopdf.org/downloads.html)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/gitbook-to-pdf.git
cd gitbook-to-pdf
```

2. Install the required Python packages:
```bash
pip install -r requirements.txt
```

3. Install wkhtmltopdf from https://wkhtmltopdf.org/downloads.html

## Usage

```bash
python gitbook_to_pdf.py <gitbook-url> -o output.pdf
```

Example:
```bash
python gitbook_to_pdf.py https://docs.example.com/gitbook -o documentation.pdf
```

## Output Format

The generated PDF includes:
- A4 page size
- Professional margins
- Page numbers
- Headers with document title
- Footers with date
- Clean typography and styling
- Proper handling of code blocks and tables

## License

MIT License
