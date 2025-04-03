import feedparser
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timezone, timedelta
from dateutil import parser
import time
import sys
import traceback

def test_parse_rss(file_path):
    try:
        print(f"解析文件: {file_path}")
        
        # 检查文件是否存在
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                print(f"文件大小: {len(content)} 字节")
                print(f"文件前100字节: {content[:100]}")
        except Exception as e:
            print(f"读取文件错误: {e}")
            traceback.print_exc()
            return
        
        # 使用feedparser解析内容
        try:
            parsed_feed = feedparser.parse(content)
            print(f"Feed解析完成")
        except Exception as e:
            print(f"解析RSS错误: {e}")
            traceback.print_exc()
            return
        
        # 打印基本Feed信息
        try:
            print(f"Feed版本: {parsed_feed.get('version', 'Unknown')}")
            print(f"Feed标题: {parsed_feed.feed.get('title', 'No title')}")
            print(f"条目数量: {len(parsed_feed.entries)}")
        except Exception as e:
            print(f"获取Feed基本信息错误: {e}")
            traceback.print_exc()
        
        # 分析第一个条目(如果存在)
        if len(parsed_feed.entries) > 0:
            try:
                first_entry = parsed_feed.entries[0]
                print("\n第一条目信息:")
                print(f"标题: {first_entry.get('title', 'No title')}")
                print(f"链接: {first_entry.get('link', 'No link')}")
                
                # 检查summary字段
                summary = first_entry.get('summary', '')
                print(f"摘要长度: {len(summary)}")
                print(f"摘要前200字符: {summary[:200]}")
                
                # 检查content字段 (有些RSS格式使用此字段存储完整内容)
                if 'content' in first_entry:
                    try:
                        content = first_entry.get('content')[0].get('value', '')
                        print(f"\ncontent字段长度: {len(content)}")
                        print(f"content字段前200字符: {content[:200]}")
                    except:
                        print("提取content字段出错")
                        content_raw = first_entry.get('content')
                        print(f"原始content字段: {content_raw}")
                
                # 检查content:encoded字段 (WordPress RSS格式特有)
                if 'content:encoded' in first_entry:
                    content_encoded = first_entry.get('content:encoded', '')
                    print(f"\ncontent:encoded字段长度: {len(content_encoded)}")
                    print(f"content:encoded字段前200字符: {content_encoded[:200]}")
                
                # 列出所有可用字段
                print("\n可用字段:")
                for key in first_entry.keys():
                    value = first_entry.get(key)
                    value_type = type(value).__name__
                    value_len = len(str(value))
                    print(f"- {key} (类型: {value_type}, 大小: {value_len})")
            except Exception as e:
                print(f"分析条目错误: {e}")
                traceback.print_exc()
    except Exception as e:
        print(f"整体测试异常: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "cdtfeed.txt"
    
    test_parse_rss(file_path) 