#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown转HTML转换工具

功能：
- 将Markdown文件转换为HTML文件
- 支持命令行参数
- 自动添加美观的CSS样式
- 支持批量转换目录中的所有md文件

使用方法：
python md_to_html.py input.md output.html
python md_to_html.py --dir input_dir --output output_dir
python md_to_html.py --help

依赖：
- markdown: Markdown解析库
- pygments: 代码语法高亮（可选）
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

import markdown


# 美观的CSS样式
CSS_STYLES = """
<style>
:root {
    --primary-color: #3498db;
    --secondary-color: #2c3e50;
    --background-color: #f8f9fa;
    --text-color: #333;
    --border-color: #bdc3c7;
    --code-bg: #f4f4f4;
    --pre-bg: #2c3e50;
    --pre-text: #ecf0f1;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: var(--text-color);
    max-width: 900px;
    margin: 0 auto;
    padding: 20px;
    background-color: var(--background-color);
    width: 100%;
    min-width: 0;
}

.container {
    background-color: white;
    padding: 40px;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    margin-bottom: 20px;
}

.metadata {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 15px 20px;
    border-radius: 8px;
    margin-bottom: 30px;
    font-size: 0.9em;
}

.metadata strong {
    color: #fff;
}

h1, h2, h3, h4, h5, h6 {
    color: var(--secondary-color);
    margin-top: 1.8em;
    margin-bottom: 0.8em;
    font-weight: 600;
}

h1 {
    border-bottom: 3px solid var(--primary-color);
    padding-bottom: 15px;
    color: var(--primary-color);
    font-size: 2.2em;
    margin-top: 0;
}

h2 {
    border-bottom: 2px solid var(--border-color);
    padding-bottom: 8px;
    font-size: 1.6em;
}

h3 { font-size: 1.4em; }
h4 { font-size: 1.2em; }

p {
    margin-bottom: 1em;
}

code {
    background-color: var(--code-bg);
    padding: 3px 6px;
    border-radius: 4px;
    font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 0.85em;
    color: #c7254e;
}

pre {
    background-color: var(--pre-bg);
    color: var(--pre-text);
    padding: 20px;
    border-radius: 8px;
    overflow-x: auto;
    font-family: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 0.9em;
    line-height: 1.5;
    margin: 1.5em 0;
    border: 1px solid var(--border-color);
}

pre code {
    background-color: transparent;
    padding: 0;
    color: inherit;
    border-radius: 0;
}

blockquote {
    border-left: 5px solid var(--primary-color);
    padding-left: 20px;
    margin-left: 0;
    margin: 1.5em 0;
    color: #666;
    font-style: italic;
    background-color: #f8f9fa;
    padding: 15px 20px;
    border-radius: 0 8px 8px 0;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1.5em 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    border-radius: 8px;
    overflow: hidden;
    display: block;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}

th, td {
    border: 1px solid var(--border-color);
    padding: 12px 16px;
    text-align: left;
    vertical-align: top;
}

th {
    background: linear-gradient(135deg, var(--primary-color), #5dade2);
    color: white;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.85em;
    letter-spacing: 0.5px;
}

tr:nth-child(even) {
    background-color: #fafbfc;
}

tr:hover {
    background-color: #e8f4fd;
    transition: background-color 0.2s ease;
}

ul, ol {
    padding-left: 25px;
    margin: 1em 0;
}

li {
    margin: 8px 0;
    line-height: 1.6;
}

a {
    color: var(--primary-color);
    text-decoration: none;
    transition: all 0.2s ease;
    border-bottom: 1px solid transparent;
}

a:hover {
    color: #2980b9;
    border-bottom-color: var(--primary-color);
}

hr {
    border: none;
    border-top: 2px solid var(--border-color);
    margin: 2.5em 0;
    opacity: 0.6;
}

img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1.5em auto;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.footer {
    text-align: center;
    margin-top: 50px;
    padding-top: 25px;
    border-top: 1px solid var(--border-color);
    color: #95a5a6;
    font-size: 0.9em;
}

.footer p {
    margin: 0;
}

/* 平板设备 (768px - 1024px) */
@media (max-width: 1024px) {
    body {
        padding: 15px;
    }

    .container {
        padding: 25px;
    }

    h1 {
        font-size: 1.8em;
    }

    h2 {
        font-size: 1.4em;
    }

    h3 {
        font-size: 1.2em;
    }
}

/* 手机设备 (最大768px) */
@media (max-width: 768px) {
    body {
        padding: 10px;
        max-width: 100%;
    }

    .container {
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }

    .metadata {
        padding: 12px 15px;
        font-size: 0.85em;
        margin-bottom: 20px;
    }

    h1 {
        font-size: 1.6em;
        padding-bottom: 10px;
        margin-top: 0;
    }

    h2 {
        font-size: 1.3em;
        padding-bottom: 6px;
    }

    h3 {
        font-size: 1.1em;
    }

    h4 {
        font-size: 1.05em;
    }

    p {
        margin-bottom: 0.8em;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }

    code {
        font-size: 0.8em;
        padding: 2px 4px;
        word-break: break-word;
    }

    pre {
        font-size: 0.75em;
        padding: 12px;
        margin: 1em 0;
        border-radius: 6px;
        -webkit-overflow-scrolling: touch;
    }

    blockquote {
        padding: 12px 15px;
        margin: 1em 0;
        font-size: 0.95em;
    }

    table {
        font-size: 0.85em;
        display: block;
        width: 100%;
        min-width: 100%;
    }

    th, td {
        padding: 8px 10px;
        font-size: 0.9em;
        white-space: nowrap;
    }

    ul, ol {
        padding-left: 20px;
    }

    li {
        margin: 6px 0;
    }

    .footer {
        margin-top: 30px;
        padding-top: 20px;
        font-size: 0.85em;
    }

    img {
        max-width: 100%;
        height: auto;
    }
}

/* 小屏手机设备 (最大480px) */
@media (max-width: 480px) {
    body {
        padding: 8px;
    }

    .container {
        padding: 12px;
    }

    .metadata {
        padding: 10px 12px;
        font-size: 0.8em;
    }

    h1 {
        font-size: 1.4em;
    }

    h2 {
        font-size: 1.2em;
    }

    h3 {
        font-size: 1.05em;
    }

    pre {
        font-size: 0.7em;
        padding: 10px;
    }

    table {
        font-size: 0.8em;
    }

    th, td {
        padding: 6px 8px;
        font-size: 0.85em;
    }
}
</style>
"""

# HTML模板
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <title>{title}</title>
    {css}
</head>
<body>
    <div class="container">
        <div class="metadata">
            <strong>📄 原文件:</strong> {filename}<br>
            <strong>⏰ 转换时间:</strong> {timestamp}<br>
            <strong>🔧 生成工具:</strong> Markdown转HTML转换器 v2.0
        </div>
        {content}
        <div class="footer">
            <p>✨ Generated by Markdown to HTML Converter | Powered by Python & Markdown</p>
        </div>
    </div>
</body>
</html>"""


class MarkdownToHTMLConverter:
    """
    Markdown转HTML转换器

    使用Python Markdown库提供完整的Markdown解析功能，
    包括表格、代码高亮、TOC等高级特性。
    """

    def __init__(self):
        """初始化转换器"""
        self.markdown_extensions = [
            'extra',           # 包含表格、代码块等额外功能
            'codehilite',      # 代码高亮
            'toc',            # 目录
            'meta',           # 元数据
            'nl2br',          # 换行转换为<br>
            'sane_lists',     # 更合理的列表处理
            'admonition',     # 警告框
            'footnotes',      # 脚注
            'attr_list',      # 属性列表
        ]

    def convert_file(self, input_path: str, output_path: Optional[str] = None) -> bool:
        """
        转换单个Markdown文件为HTML

        Args:
            input_path: 输入Markdown文件路径
            output_path: 输出HTML文件路径，如果为None则自动生成

        Returns:
            bool: 转换是否成功
        """
        try:
            # 验证输入文件
            input_path = Path(input_path)
            if not input_path.exists():
                print(f"❌ 错误: 输入文件 '{input_path}' 不存在")
                return False

            if input_path.suffix.lower() != '.md':
                print(f"⚠️  警告: 输入文件 '{input_path}' 不是Markdown文件(.md)，但将继续转换")

            # 生成输出文件路径
            if output_path is None:
                output_path = input_path.with_suffix('.html')

            # 读取并转换文件
            markdown_content = input_path.read_text(encoding='utf-8')
            html_content = self._convert_markdown_to_html(markdown_content)

            # 生成完整HTML页面
            title = self._extract_title(markdown_content) or "Markdown文档"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            full_html = HTML_TEMPLATE.format(
                title=title,
                css=CSS_STYLES,
                filename=input_path.name,
                timestamp=timestamp,
                content=html_content
            )

            # 写入HTML文件
            Path(output_path).write_text(full_html, encoding='utf-8')

            print(f"✅ 转换成功: {input_path} -> {output_path}")
            return True

        except Exception as e:
            print(f"❌ 转换失败 '{input_path}': {str(e)}")
            return False

    def convert_directory(self, input_dir: str, output_dir: str, recursive: bool = False) -> int:
        """
        转换目录中的所有Markdown文件

        Args:
            input_dir: 输入目录路径
            output_dir: 输出目录路径
            recursive: 是否递归处理子目录

        Returns:
            int: 成功转换的文件数量
        """
        try:
            # 检查输入目录是否存在
            if not os.path.exists(input_dir):
                print(f"错误: 输入目录 '{input_dir}' 不存在")
                return 0

            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)

            # 查找所有Markdown文件
            pattern = "**/*.md" if recursive else "*.md"
            input_path_obj = Path(input_dir)
            md_files = list(input_path_obj.glob(pattern))

            if not md_files:
                print(f"在目录 '{input_dir}' 中未找到Markdown文件")
                return 0

            print(f"找到 {len(md_files)} 个Markdown文件待转换")

            success_count = 0
            for md_file in md_files:
                # 构建输出文件路径
                relative_path = md_file.relative_to(input_path_obj)
                output_file = Path(output_dir) / relative_path.with_suffix('.html')

                # 确保输出文件的目录存在
                output_file.parent.mkdir(parents=True, exist_ok=True)

                # 转换文件
                if self.convert_file(str(md_file), str(output_file)):
                    success_count += 1

            print(f"转换完成: {success_count}/{len(md_files)} 个文件成功转换")
            return success_count

        except Exception as e:
            print(f"❌ 目录转换失败: {str(e)}")
            return 0

    def _convert_markdown_to_html(self, markdown_content: str) -> str:
        """
        将Markdown内容转换为HTML

        Args:
            markdown_content: Markdown文本内容

        Returns:
            str: HTML内容
        """
        # 创建Markdown实例并配置扩展
        md = markdown.Markdown(
            extensions=self.markdown_extensions,
            extension_configs={
                'codehilite': {
                    'linenums': False,  # 不显示行号
                    'guess_lang': True,  # 自动检测语言
                    'css_class': 'highlight'  # CSS类名
                },
                'toc': {
                    'marker': '[TOC]',  # TOC标记
                    'title': '目录'  # TOC标题
                }
            }
        )

        # 转换Markdown为HTML
        html_content = md.convert(markdown_content)
        return html_content


    def _extract_title(self, markdown_content: str) -> Optional[str]:
        """
        从Markdown内容中提取标题

        Args:
            markdown_content: Markdown文本内容

        Returns:
            Optional[str]: 提取到的标题，如果没有则返回None
        """
        lines = markdown_content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        return None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='将Markdown文件转换为HTML文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python md_to_html.py input.md                    # 转换单个文件
  python md_to_html.py input.md output.html        # 指定输出文件
  python md_to_html.py --dir ./docs --output ./html  # 转换目录
  python md_to_html.py --dir ./docs --output ./html --recursive  # 递归转换
        """
    )

    parser.add_argument('input', nargs='?', help='输入Markdown文件路径')
    parser.add_argument('output', nargs='?', help='输出HTML文件路径（可选）')

    parser.add_argument('--dir', '-d', help='输入目录路径（批量转换）')
    parser.add_argument('--output-dir', '-o', help='输出目录路径（与--dir配合使用）')
    parser.add_argument('--recursive', '-r', action='store_true',
                       help='递归处理子目录（与--dir配合使用）')

    args = parser.parse_args()

    # 创建转换器
    converter = MarkdownToHTMLConverter()

    # 处理命令行参数
    if args.dir:
        # 目录转换模式
        if not args.output_dir:
            print("错误: 使用--dir参数时必须指定--output-dir参数")
            return 1

        success_count = converter.convert_directory(args.dir, args.output_dir, args.recursive)
        return 0 if success_count > 0 else 1

    elif args.input:
        # 单文件转换模式
        success = converter.convert_file(args.input, args.output)
        return 0 if success else 1

    else:
        # 显示帮助信息
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
