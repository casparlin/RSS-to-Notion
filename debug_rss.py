import feedparser
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timezone, timedelta
from dateutil import parser
import time
import sys
import traceback
import json

def debug_rss_content_extraction(file_path):
    """专门调试RSS内容提取的问题"""
    try:
        print(f"解析文件: {file_path}")
        
        # 读取文件内容
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # 使用feedparser解析内容
        parsed_feed = feedparser.parse(content)
        
        if len(parsed_feed.entries) > 0:
            first_entry = parsed_feed.entries[0]
            print("\n第一条目基本信息:")
            print(f"标题: {first_entry.get('title')}")
            
            # 检查可能包含完整内容的字段
            print("\n检查RSS条目可能包含主要内容的字段:")
            
            # 1. summary字段
            summary = first_entry.get('summary', '')
            print(f"summary字段长度: {len(summary)}")
            print(f"summary字段前100字符: {summary[:100]}")
            
            # 2. content字段
            if 'content' in first_entry:
                content_field = first_entry.get('content')
                print(f"content字段类型: {type(content_field).__name__}")
                
                if isinstance(content_field, list) and len(content_field) > 0:
                    content_value = content_field[0].get('value', '')
                    print(f"content[0].value字段长度: {len(content_value)}")
                    print(f"content[0].value字段前100字符: {content_value[:100]}")
                else:
                    print(f"content字段结构: {content_field}")
            
            # 3. content:encoded字段 (WordPress常用)
            if 'content:encoded' in first_entry:
                content_encoded = first_entry.get('content:encoded', '')
                print(f"content:encoded字段长度: {len(content_encoded)}")
                print(f"content:encoded字段前100字符: {content_encoded[:100]}")
            
            # 4. description字段
            if 'description' in first_entry:
                description = first_entry.get('description', '')
                print(f"description字段长度: {len(description)}")
                print(f"description字段前100字符: {description[:100]}")
            
            # 模拟FeedTool.py中的处理逻辑
            print("\n模拟FeedTool.py的处理逻辑:")
            
            # 模拟convert_html_to_notion_blocks函数的输入
            html_content = first_entry.get("summary", "")
            
            # 检查这是否是完整的内容
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text().strip()
            print(f"从summary提取的文本内容长度: {len(text_content)}")
            print(f"文本内容前100字符: {text_content[:100]}")
            
            # 分析完整内容的位置
            if 'content' in first_entry:
                content_html = first_entry.get('content')[0].get('value', '')
                content_soup = BeautifulSoup(content_html, 'html.parser')
                content_text = content_soup.get_text().strip()
                print(f"从content提取的文本内容长度: {len(content_text)}")
                
                # 检查summary是否只是content的一小部分
                if len(content_text) > len(text_content) and content_text.startswith(text_content[:50]):
                    print("发现问题: content包含完整内容，但脚本只使用了summary")
                    print(f"summary包含的内容比例: {len(text_content)/len(content_text)*100:.2f}%")
            
            # 显示所有可用字段以供参考
            print("\n所有可用字段:")
            for key in first_entry.keys():
                value = first_entry.get(key)
                print(f"- {key} (类型: {type(value).__name__})")
    
    except Exception as e:
        print(f"调试过程发生错误: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "cdtfeed.txt"
    
    debug_rss_content_extraction(file_path) 