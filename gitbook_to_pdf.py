import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import pdfkit
import logging
import re
from datetime import datetime

# 配置 wkhtmltopdf 路径
WKHTMLTOPDF_PATH = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)

class GitbookToPDF:
    def __init__(self, base_url):
        self.base_url = base_url
        self.visited_urls = set()
        self.all_content = []
        self.session = requests.Session()
        self.css_files = set()
        self.title = ""
        
    def is_same_domain(self, url):
        """检查URL是否属于同一个域名"""
        base_domain = urlparse(self.base_url).netloc
        url_domain = urlparse(url).netloc
        return base_domain == url_domain

    def get_page_content(self, url):
        """获取页面内容并解析"""
        try:
            print(f"Processing: {url}")
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取网站标题
            if not self.title and soup.title:
                self.title = soup.title.string
            
            # 提取CSS文件
            for css_link in soup.find_all('link', rel='stylesheet'):
                if css_link.get('href'):
                    css_url = urljoin(url, css_link.get('href'))
                    self.css_files.add(css_url)
            
            # 获取主要内容
            content = soup.find('article') or soup.find('main') or soup.find('div', class_='page-inner')
            if content:
                title = soup.title.string if soup.title else "Untitled"
                self.all_content.append(f'<div class="page-break"></div><h1>{title}</h1>')
                self.all_content.append(str(content))
            
            # 查找所有链接
            links = soup.find_all('a', href=True)
            for link in links:
                next_url = urljoin(url, link['href'])
                if (next_url not in self.visited_urls and 
                    self.is_same_domain(next_url) and 
                    not next_url.startswith('#') and
                    not next_url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.pdf'))):
                    self.visited_urls.add(next_url)
                    self.get_page_content(next_url)
                    
        except Exception as e:
            logging.error(f"Error processing {url}: {str(e)}")

    def download_css(self):
        """下载所有CSS文件的内容"""
        css_content = []
        for css_url in self.css_files:
            try:
                css_response = self.session.get(css_url)
                css_response.raise_for_status()
                css_content.append(css_response.text)
            except Exception as e:
                logging.error(f"Error downloading CSS from {css_url}: {str(e)}")
        return '\n'.join(css_content)

    def generate_pdf(self, output_file='output.pdf'):
        """生成PDF文件"""
        # 创建完整的HTML文档
        current_date = datetime.now().strftime("%Y-%m-%d")
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{self.title}</title>
            <style>
                {self.download_css()}
                @page {{
                    size: A4;
                    margin: 2cm 2.5cm;
                    @top-right {{
                        content: "{self.title}";
                        font-size: 9pt;
                        color: #666;
                    }}
                    @bottom-center {{
                        content: counter(page);
                        font-size: 10pt;
                    }}
                    @bottom-right {{
                        content: "{current_date}";
                        font-size: 9pt;
                        color: #666;
                    }}
                }}
                body {{
                    font-family: "Arial", sans-serif;
                    font-size: 11pt;
                    line-height: 1.6;
                    max-width: 100%;
                }}
                h1 {{
                    font-size: 20pt;
                    color: #333;
                    margin-top: 2em;
                    page-break-before: always;
                }}
                h2 {{
                    font-size: 16pt;
                    color: #444;
                    margin-top: 1.5em;
                }}
                h3 {{
                    font-size: 14pt;
                    color: #555;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                    margin: 1em 0;
                }}
                code {{
                    font-family: "Consolas", monospace;
                    background-color: #f5f5f5;
                    padding: 2px 4px;
                    border-radius: 3px;
                }}
                pre {{
                    background-color: #f5f5f5;
                    padding: 1em;
                    border-radius: 5px;
                    overflow-x: auto;
                    font-size: 10pt;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 1em 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f5f5f5;
                }}
                .page-break {{
                    page-break-before: always;
                }}
                a {{
                    color: #0366d6;
                    text-decoration: none;
                }}
                blockquote {{
                    border-left: 4px solid #ddd;
                    margin: 1em 0;
                    padding-left: 1em;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <h1 class="cover-title">{self.title}</h1>
            <div class="generation-date">Generated on {current_date}</div>
            {''.join(self.all_content)}
        </body>
        </html>
        """
        
        # 保存为临时HTML文件
        temp_html = 'temp.html'
        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 配置pdfkit选项
        options = {
            'encoding': 'UTF-8',
            'page-size': 'A4',
            'margin-top': '2cm',
            'margin-right': '2.5cm',
            'margin-bottom': '2cm',
            'margin-left': '2.5cm',
            'header-right': '[title]',
            'header-font-size': '9',
            'header-spacing': '10',
            'footer-center': '[page]',
            'footer-font-size': '10',
            'footer-right': current_date,
            'footer-spacing': '10',
            'zoom': '1.2',
            'enable-local-file-access': None,
            'quiet': ''
        }
        
        # 转换为PDF
        try:
            pdfkit.from_file(temp_html, output_file, options=options, configuration=config)
            print(f"PDF has been generated: {output_file}")
        except Exception as e:
            print(f"Error generating PDF: {str(e)}")
            print("Please make sure wkhtmltopdf is installed on your system.")
            print("You can download it from: https://wkhtmltopdf.org/downloads.html")
        finally:
            # 删除临时文件
            if os.path.exists(temp_html):
                os.remove(temp_html)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Convert Gitbook to PDF')
    parser.add_argument('url', help='The URL of the Gitbook main page')
    parser.add_argument('--output', '-o', default='output.pdf', help='Output PDF file name')
    args = parser.parse_args()

    converter = GitbookToPDF(args.url)
    print("Starting to crawl the Gitbook...")
    converter.get_page_content(args.url)
    print("Generating PDF...")
    converter.generate_pdf(args.output)

if __name__ == '__main__':
    main()
