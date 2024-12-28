import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import pdfkit
import logging
import re
from datetime import datetime
import base64
import mimetypes
import hashlib
import json
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PyPDF2 import PdfMerger
from selenium.common.exceptions import WebDriverException
import time
import argparse

# 配置 wkhtmltopdf 路径
WKHTMLTOPDF_PATH = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)

def setup_chrome_driver():
    """设置 Chrome 驱动"""
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # 添加 PDF 打印首选项
        chrome_options.add_experimental_option('prefs', {
            'printing.print_preview_sticky_settings.appState': json.dumps({
                'recentDestinations': [{
                    'id': 'Save as PDF',
                    'origin': 'local',
                    'account': ''
                }],
                'selectedDestinationId': 'Save as PDF',
                'version': 2,
                'isHeaderFooterEnabled': False,
                'isLandscapeEnabled': False,
            })
        })

        try:
            driver = webdriver.Chrome(options=chrome_options)
        except WebDriverException:
            print("正在安装 ChromeDriver...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        
        return driver
    except Exception as e:
        print(f"设置 Chrome 驱动时出错: {str(e)}")
        print("请确保系统已安装 Google Chrome。")
        sys.exit(1)

class GitbookToPDF:
    def __init__(self, base_url, method='html'):
        self.base_url = base_url
        self.visited_urls = set()
        self.all_content = []
        self.session = requests.Session()
        self.css_files = set()
        self.title = ""
        self.images = {}
        self.image_dir = "images"
        self.method = method
        self.temp_dir = "temp_pdfs"
        
        # 创建必要的目录
        for directory in [self.image_dir, self.temp_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        # 如果使用 selenium 方法，初始化 driver
        if self.method == 'print':
            self.driver = setup_chrome_driver()
    
    def print_to_pdf(self, url, index):
        """使用 Chrome 打印方式生成 PDF"""
        try:
            self.driver.get(url)
            time.sleep(2)
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            pdf_data = self.driver.execute_cdp_cmd("Page.printToPDF", {
                "printBackground": True,
                "paperWidth": 8.27,
                "paperHeight": 11.69,
                "marginTop": 0.4,
                "marginBottom": 0.4,
                "marginLeft": 0.4,
                "marginRight": 0.4,
                "scale": 1,
            })
            
            filename = f"page_{index:03d}.pdf"
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(pdf_data['data']))
            
            print(f"已保存 {filename}")
            return filepath
        except Exception as e:
            print(f"处理 {url} 时出错: {str(e)}")
            return None

    def merge_pdfs(self, pdf_files, output_file):
        """合并多个 PDF 文件"""
        merger = PdfMerger()
        
        for pdf in pdf_files:
            if pdf and os.path.exists(pdf):
                try:
                    merger.append(pdf)
                except Exception as e:
                    print(f"合并 {pdf} 时出错: {str(e)}")
        
        merger.write(output_file)
        merger.close()

        # 清理临时文件
        for pdf in pdf_files:
            try:
                os.remove(pdf)
            except:
                pass

    def download_image(self, img_url):
        """下载图片并转换为base64或保存到本地"""
        try:
            img_hash = hashlib.md5(img_url.encode()).hexdigest()
            extension = os.path.splitext(urlparse(img_url).path)[1]
            if not extension:
                response = requests.head(img_url)
                content_type = response.headers.get('content-type', '')
                extension = mimetypes.guess_extension(content_type) or '.jpg'
            
            img_filename = f"{img_hash}{extension}"
            img_path = os.path.join(self.image_dir, img_filename)
            
            if os.path.exists(img_path):
                return img_path
            
            response = self.session.get(img_url, stream=True)
            response.raise_for_status()
            
            with open(img_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return img_path
            
        except Exception as e:
            logging.error(f"Error downloading image {img_url}: {str(e)}")
            return img_url

    def process_images(self, soup, base_url):
        """处理页面中的所有图片"""
        for img in soup.find_all('img'):
            if img.get('src'):
                img_url = urljoin(base_url, img.get('src'))
                img_path = self.download_image(img_url)
                if img_path:
                    img['src'] = os.path.abspath(img_path)

    def is_same_domain(self, url):
        """检查URL是否属于同一个域名"""
        base_domain = urlparse(self.base_url).netloc
        url_domain = urlparse(url).netloc
        return base_domain == url_domain

    def get_page_content(self, url):
        """获取页面内容并解析"""
        if self.method == 'print':
            return self.print_to_pdf(url, len(self.visited_urls))

        try:
            print(f"Processing: {url}")
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            if not self.title and soup.title:
                self.title = soup.title.string
            
            for css_link in soup.find_all('link', rel='stylesheet'):
                if css_link.get('href'):
                    css_url = urljoin(url, css_link.get('href'))
                    self.css_files.add(css_url)
            
            self.process_images(soup, url)
            
            content = soup.find('article') or soup.find('main') or soup.find('div', class_='page-inner')
            if content:
                title = soup.title.string if soup.title else "Untitled"
                self.all_content.append(f'<div class="page-break"></div><h1>{title}</h1>')
                self.all_content.append(str(content))
            
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

    def get_all_links(self, url):
        """获取页面中的所有链接"""
        try:
            self.driver.get(url)
            time.sleep(2)  # 等待页面加载
            
            # 等待内容加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 获取所有链接
            links = self.driver.find_elements(By.TAG_NAME, "a")
            urls = []
            for link in links:
                href = link.get_attribute('href')
                if href and self.is_same_domain(href) and href not in self.visited_urls:
                    urls.append(href)
            
            return list(set(urls))  # 去重
        except Exception as e:
            print(f"获取链接时出错: {str(e)}")
            return []

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
        if self.method == 'print':
            pdf_files = []
            self.visited_urls.add(self.base_url)
            
            # 处理主页
            print(f"处理主页: {self.base_url}")
            main_pdf = self.print_to_pdf(self.base_url, 0)
            if main_pdf:
                pdf_files.append(main_pdf)
            
            # 获取所有链接
            urls = self.get_all_links(self.base_url)
            print(f"找到 {len(urls)} 个子页面")
            
            # 处理每个子页面
            for i, url in enumerate(urls, 1):
                if url not in self.visited_urls:
                    print(f"处理页面 {i}/{len(urls)}: {url}")
                    self.visited_urls.add(url)
                    pdf_file = self.print_to_pdf(url, i)
                    if pdf_file:
                        pdf_files.append(pdf_file)
                    time.sleep(1)  # 避免请求过快
            
            if pdf_files:
                print(f"合并 {len(pdf_files)} 个 PDF 文件...")
                self.merge_pdfs(pdf_files, output_file)
                print(f"PDF 生成完成: {output_file}")
            
            self.driver.quit()
            return

        # HTML 方法
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
        
        temp_html = 'temp.html'
        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
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
        
        try:
            pdfkit.from_file(temp_html, output_file, options=options, configuration=config)
            print(f"PDF has been generated: {output_file}")
        except Exception as e:
            print(f"Error generating PDF: {str(e)}")
            print("Please make sure wkhtmltopdf is installed on your system.")
            print("You can download it from: https://wkhtmltopdf.org/downloads.html")
        finally:
            if os.path.exists(temp_html):
                os.remove(temp_html)

def main():
    parser = argparse.ArgumentParser(description='Convert GitBook to PDF')
    parser.add_argument('url', help='The URL of the GitBook main page')
    parser.add_argument('--output', '-o', default='output.pdf', help='Output PDF file name')
    parser.add_argument('--method', '-m', choices=['html', 'print'], default='html',
                      help='Conversion method: html (using wkhtmltopdf) or print (using Chrome print)')
    args = parser.parse_args()

    converter = GitbookToPDF(args.url, method=args.method)
    print("Starting to crawl the GitBook...")
    if args.method == 'html':
        converter.get_page_content(args.url)
    print("Generating PDF...")
    converter.generate_pdf(args.output)

if __name__ == '__main__':
    main()
