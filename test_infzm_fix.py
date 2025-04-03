import feedparser
from bs4 import BeautifulSoup, Comment
import json
from Util.FeedTool import convert_html_to_notion_blocks

def test_infzm_rss():
    """测试南方周末RSS内容提取修复"""
    print("开始测试南方周末RSS内容提取修复...")
    
    # 读取文件内容
    with open('infzm.rss', 'rb') as f:
        content = f.read()
    
    # 使用feedparser解析内容
    parsed_feed = feedparser.parse(content)
    
    if len(parsed_feed.entries) > 0:
        first_entry = parsed_feed.entries[0]
        print(f"\n第一条目基本信息:")
        print(f"标题: {first_entry.get('title')}")
        
        # 获取HTML内容
        html_content = first_entry.get("description", "")
        print(f"HTML内容长度: {len(html_content)}")
        print(f"HTML内容前100字符: {html_content[:100]}")
        
        # 检测南方周末特殊结构
        soup = BeautifulSoup(html_content, 'html.parser')
        nfzm_fulltext = soup.find('div', class_='nfzm-content__fulltext')
        if nfzm_fulltext:
            print(f"\n检测到南方周末(infzm)特殊内容结构")
            print(f"nfzm-content__fulltext内容长度: {len(str(nfzm_fulltext))}")
            print(f"fulltext前200字符: {str(nfzm_fulltext)[:200]}")
        else:
            print(f"\n未检测到南方周末特殊内容结构!")
        
        # 使用修改后的转换函数
        print("\n使用修改后的转换函数:")
        blocks = convert_html_to_notion_blocks(html_content)
        
        # 显示转换后的块数量
        print(f"生成了 {len(blocks)} 个内容块")
        
        # 显示前5个块的内容
        print("\n前5个内容块:")
        for i, block in enumerate(blocks[:5]):
            if i >= 5:
                break
                
            block_type = list(block.keys())[1]  # 第二个键是块类型
            if block_type == "paragraph":
                text = block[block_type]["rich_text"][0]["text"]["content"]
                print(f"块 {i+1} ({block_type}): {text[:100]}..." if len(text) > 100 else f"块 {i+1} ({block_type}): {text}")
            elif block_type in ["heading_1", "heading_2", "heading_3"]:
                text = block[block_type]["rich_text"][0]["text"]["content"]
                print(f"块 {i+1} ({block_type}): {text}")
            elif block_type == "image":
                url = block[block_type]["external"]["url"]
                print(f"块 {i+1} ({block_type}): {url}")
            elif block_type == "bulleted_list_item":
                text = block[block_type]["rich_text"][0]["text"]["content"]
                print(f"块 {i+1} ({block_type}): {text[:100]}..." if len(text) > 100 else f"块 {i+1} ({block_type}): {text}")
        
        # 检查是否有"vote components in top start"等特殊标记
        special_markers = ["vote components in top start", "vote components in top end", 
                          "播客文章", "2024 newyear hack", "vote components in bottom start", "校对："]
        
        print("\n检查是否含有特殊标记:")
        found_any = False
        for marker in special_markers:
            found = False
            for block in blocks:
                block_type = list(block.keys())[1]
                if block_type == "paragraph" or block_type in ["heading_1", "heading_2", "heading_3", "bulleted_list_item"]:
                    try:
                        text = block[block_type]["rich_text"][0]["text"]["content"]
                        if marker in text:
                            found = True
                            found_any = True
                            print(f"发现标记 '{marker}' 在块中: {text[:50]}...")
                            break
                    except (IndexError, KeyError):
                        continue
            if not found:
                print(f"未发现标记 '{marker}'")
        
        # 总结
        print("\n测试结论:")
        if len(blocks) > 0:
            print("✓ 成功从南方周末RSS中提取内容")
            print(f"✓ 生成了 {len(blocks)} 个内容块")
            
            # 检查是否含有特殊标记
            if not found_any:
                print("✓ 内容中不含有特殊标记")
            else:
                print("✗ 内容中仍然含有特殊标记")
        else:
            print("✗ 未能从南方周末RSS中提取内容")
    else:
        print("RSS文件中没有条目")

if __name__ == "__main__":
    test_infzm_rss() 