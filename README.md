# GitBook to PDF Converter

A Python tool to convert GitBook documentation into a well-formatted PDF file. The tool supports two conversion methods:
1. HTML method (using wkhtmltopdf)
2. Print method (using Chrome's PDF printing) - Recommended for most users

## Features

- Scrapes GitBook pages recursively from a starting URL
- Downloads and includes images in the PDF
- Maintains proper formatting and styling
- Supports page headers and footers
- Handles internal links
- Two conversion methods to choose from based on your needs
- Beautiful typography and layout

## Prerequisites

1. Python 3.6 or higher
2. For HTML method (optional):
   - wkhtmltopdf (Download from: https://wkhtmltopdf.org/downloads.html)
3. For Print method (recommended):
   - Google Chrome browser (already installed on most systems)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/gitbook-to-pdf.git
cd gitbook-to-pdf
```

2. Install required Python packages:
```bash
pip install -r requirements.txt
```

3. Additional setup:
   - For HTML method: Install wkhtmltopdf from https://wkhtmltopdf.org/downloads.html
   - For Print method: No additional setup needed if Chrome is installed

## Usage

The tool provides two methods for converting GitBook to PDF:

### 1. Print Method (Recommended)
Uses Chrome's PDF printing. Better for JavaScript-heavy pages and modern web content. No additional software required.

```bash
python gitbook_to_pdf.py https://your-gitbook-url.com -o output.pdf -m print
```

### 2. HTML Method
Uses wkhtmltopdf for conversion. Better for custom styling and format control. Requires wkhtmltopdf installation.

```bash
python gitbook_to_pdf.py https://your-gitbook-url.com -o output.pdf
# or explicitly specify the method
python gitbook_to_pdf.py https://your-gitbook-url.com -o output.pdf -m html
```

### Command Line Arguments

- `url`: The URL of the GitBook main page (required)
- `-o, --output`: Output PDF file name (default: output.pdf)
- `-m, --method`: Conversion method: 'html' or 'print' (default: html)

## Output Format

The generated PDF includes:
- Cover page with title
- Table of contents
- All pages from the GitBook
- Images and code blocks
- Page numbers
- Headers with document title
- Footers with page number and generation date

## Method Comparison

### Print Method (Chrome) - Recommended
- Pros:
  - No additional software required
  - Better JavaScript support
  - More accurate web rendering
  - Good for modern web pages
  - Handles dynamic content better
- Cons:
  - Less control over styling
  - Requires Chrome browser (but usually pre-installed)
  - Heavier resource usage

### HTML Method (wkhtmltopdf)
- Pros:
  - Fine-grained control over PDF styling
  - Custom CSS support
  - Better page header/footer control
  - Lighter weight
- Cons:
  - Requires wkhtmltopdf installation
  - May not handle JavaScript content well
  - Additional setup step

## Directory Structure

```
gitbook-to-pdf/
├── gitbook_to_pdf.py     # Main script
├── requirements.txt      # Python dependencies
├── README.md            # Documentation
├── .gitignore           # Git ignore file
├── images/              # Downloaded images directory
└── temp_pdfs/           # Temporary PDF files (for print method)
```

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details.
