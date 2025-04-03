import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from dateutil import parser as date_parser
import sys

def test_fix():
    print("测试修复后的功能...")
    
    # 读取本地文件
    with open('36krfeed.txt', 'rb') as f:
        content = f.read()
    
    # 直接使用feedparser解析内容
    parsed_feed = feedparser.parse(content)
    
    print(f'Feed标题: {parsed_feed.feed.get("title", "未知")}')
    print(f'总条目数: {len(parsed_feed.entries)}')
    
    if len(parsed_feed.entries) > 0:
        entry = parsed_feed.entries[0]
        print(f'\n第一条目标题: {entry.get("title")}')
        
        # 打印所有可用字段
        print("\n所有可用字段及其类型:")
        # 使用遍历字典的方式获取字段
        for key, value in entry.items():
            value_type = type(value).__name__
            try:
                value_len = len(str(value)) if value is not None else 0
                print(f"- {key} (类型: {value_type}, 长度: {value_len})")
            except Exception as e:
                print(f"- {key} (类型: {value_type}, 无法获取长度: {e})")
        
        # 获取完整内容
        html_content = ""
        if entry.get("content"):  # 首先尝试使用content字段
            try:
                html_content = entry.get("content")[0].get("value", "")
                print(f"\n使用content字段作为内容源，长度: {len(html_content)}")
            except (IndexError, KeyError, TypeError) as e:
                print(f"\n从content获取内容失败: {e}")
                # 打印content字段的实际结构
                print(f"content字段的实际结构: {type(entry.get('content')).__name__}")
                print(f"content字段的内容: {entry.get('content')}")
                html_content = ""
        
        if not html_content and entry.get("content:encoded"):  # 然后尝试使用content:encoded字段
            html_content = entry.get("content:encoded")
            print(f"\n使用content:encoded字段作为内容源，长度: {len(html_content)}")
        
        if not html_content:  # 最后才使用summary字段
            html_content = entry.get("summary", "")
            print(f"\n使用summary字段作为内容源，长度: {len(html_content)}")
            print(f"summary字段内容前100字符: {html_content[:100]}")
        
        # 使用BeautifulSoup提取文本内容
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = soup.get_text().strip()
        
        print(f'\n解析出的文本内容长度: {len(text_content)}')
        print(f'文本内容预览(前200字符):\n{text_content[:200]}')
        
        # 验证是否有完整内容
        if len(text_content) > 100:
            print("\n✅ 修复成功！成功提取完整内容")
        else:
            print("\n❌ 修复失败，内容仍然不完整")

if __name__ == "__main__":
    try:
        test_fix()
    except Exception as e:
        import traceback
        print(f"发生错误: {e}")
        traceback.print_exc() 