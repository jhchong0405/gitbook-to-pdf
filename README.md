# GitBook to PDF Converter

A Python tool to convert GitBook documentation into a well-formatted PDF file. The tool supports two conversion methods:
1. HTML method (using wkhtmltopdf)
2. Print method (using Chrome's PDF printing)

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
2. For HTML method:
   - wkhtmltopdf (Download from: https://wkhtmltopdf.org/downloads.html)
3. For Print method:
   - Google Chrome browser

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

3. Install wkhtmltopdf (if using HTML method):
   - Windows: Download and install from https://wkhtmltopdf.org/downloads.html
   - Linux: `sudo apt-get install wkhtmltopdf`
   - macOS: `brew install wkhtmltopdf`

## Usage

The tool provides two methods for converting GitBook to PDF:

### 1. HTML Method (Default)
Uses wkhtmltopdf for conversion. Better for custom styling and format control.

```bash
python gitbook_to_pdf.py https://your-gitbook-url.com -o output.pdf
# or explicitly specify the method
python gitbook_to_pdf.py https://your-gitbook-url.com -o output.pdf -m html
```

### 2. Print Method
Uses Chrome's PDF printing. Better for JavaScript-heavy pages and modern web content.

```bash
python gitbook_to_pdf.py https://your-gitbook-url.com -o output.pdf -m print
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

### HTML Method (wkhtmltopdf)
- Pros:
  - Fine-grained control over PDF styling
  - Custom CSS support
  - Better page header/footer control
  - Lighter weight
- Cons:
  - May not handle JavaScript content well
  - Requires wkhtmltopdf installation

### Print Method (Chrome)
- Pros:
  - Better JavaScript support
  - More accurate web rendering
  - Good for modern web pages
  - Handles dynamic content better
- Cons:
  - Less control over styling
  - Requires Chrome browser
  - Heavier resource usage

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
