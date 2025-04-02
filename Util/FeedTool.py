import feedparser
from bs4 import BeautifulSoup

import re
import json
import requests
from datetime import datetime, timezone, timedelta
from dateutil import parser
import time

now = datetime.now(timezone.utc)
load_time = 15  # 导入60天内的内容

def count_chinese_chars(text):
	"""计算文本中的中文字符数"""
	return len(re.findall(r'[\u4e00-\u9fff]', text))

def get_content_type(text):
	"""根据中文字符数判断内容类型"""
	chinese_count = count_chinese_chars(text)
	return "长文" if chinese_count > 300 else "简报"

def convert_html_to_notion_blocks(html_content):
	"""将HTML内容转换为Notion块格式"""
	soup = BeautifulSoup(html_content, 'html.parser')
	blocks = []
	
	print(f"开始转换HTML - 内容长度: {len(html_content)}")
	print(f"HTML内容前200字符: {html_content[:200]}")
	
	for element in soup.children:
		if element.name is None:  # 纯文本
			if element.strip():
				blocks.append({
					"type": "paragraph",
					"paragraph": {
						"rich_text": [{"type": "text", "text": {"content": element.strip()}}]
					}
				})
		elif element.name == 'p':
			# 处理图片包装器
			if element.get('class') and 'image-wrapper' in element.get('class'):
				img = element.find('img')
				if img and img.get('src'):
					# 处理图片URL，去除?后面的参数
					img_url = img['src'].split('?')[0]
					# 检查URL是否以.jpg, .png, .gif等结尾
					if not any(img_url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
						# 如果URL不以常见图片扩展名结尾，添加.jpg扩展名
						if '_img_jpg' in img_url:
							img_url = img_url + '.jpg'
						elif '_img_png' in img_url:
							img_url = img_url + '.png'
						elif '_img_gif' in img_url:
							img_url = img_url + '.gif'
					
					# 使用处理后的URL
					try:
						blocks.append({
							"type": "paragraph",
							"paragraph": {
								"rich_text": [{"type": "text", "text": {"content": "[图片]"}}]
							}
						})
					except Exception as e:
						print(f"添加图片块失败: {e}")
						blocks.append({
							"type": "paragraph",
							"paragraph": {
								"rich_text": [{"type": "text", "text": {"content": "[图片]"}}]
							}
						})
			# 处理图片描述
			elif element.get('class') and 'img-desc' in element.get('class'):
				blocks.append({
					"type": "paragraph",
					"paragraph": {
						"rich_text": [{"type": "text", "text": {"content": element.get_text()}}]
					}
				})
			# 处理普通段落
			else:
				blocks.append({
					"type": "paragraph",
					"paragraph": {
						"rich_text": [{"type": "text", "text": {"content": element.get_text()}}]
					}
				})
		elif element.name == 'h1':
			blocks.append({
				"type": "heading_1",
				"heading_1": {
					"rich_text": [{"type": "text", "text": {"content": element.get_text()}}]
				}
			})
		elif element.name == 'h2':
			blocks.append({
				"type": "heading_2",
				"heading_2": {
					"rich_text": [{"type": "text", "text": {"content": element.get_text()}}]
				}
			})
		elif element.name == 'h3':
			blocks.append({
				"type": "heading_3",
				"heading_3": {
					"rich_text": [{"type": "text", "text": {"content": element.get_text()}}]
				}
			})
		elif element.name == 'ul':
			for li in element.find_all('li'):
				blocks.append({
					"type": "bulleted_list_item",
					"bulleted_list_item": {
						"rich_text": [{"type": "text", "text": {"content": li.get_text()}}]
					}
				})
		elif element.name == 'figure':
			img = element.find('img')
			if img and img.get('src'):
				# 使用段落替代图片
				blocks.append({
					"type": "paragraph",
					"paragraph": {
						"rich_text": [{"type": "text", "text": {"content": "[图片]"}}]
					}
				})
			figcaption = element.find('figcaption')
			if figcaption:
				blocks.append({
					"type": "paragraph",
					"paragraph": {
						"rich_text": [{"type": "text", "text": {"content": figcaption.get_text()}}]
					}
				})
		elif element.name == 'img' and element.get('src'):
			# 使用段落替代图片
			blocks.append({
				"type": "paragraph",
				"paragraph": {
					"rich_text": [{"type": "text", "text": {"content": "[图片]"}}]
				}
			})
	
	print(f"转换完成，生成了 {len(blocks)} 个块")
	if len(blocks) == 0:
		print("警告: 没有生成任何块! 尝试替代方法...")
		# 如果没有生成任何块，尝试使用替代方法
		try:
			# 直接使用整个soup对象
			text_content = soup.get_text().strip()
			if text_content:
				blocks.append({
					"type": "paragraph",
					"paragraph": {
						"rich_text": [{"type": "text", "text": {"content": text_content[:2000]}}]
					}
				})
				print(f"使用替代方法生成了1个文本块，长度: {len(text_content[:2000])}")
		except Exception as e:
			print(f"替代方法也失败了: {e}")
	
	# 限制内容块数量不超过300个
	if len(blocks) > 300:
		print(f"内容块数量({len(blocks)})超过Notion限制(300)，将截断内容")
		blocks = blocks[:300]
	
	return blocks

def parse_rss_entries(url, retries=3):
	entries = []
	feeds = []
	for attempt in range(retries):
		try:
			res = requests.get(
				url=url,
				headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.55 Safari/537.36 Edg/96.0.1054.34"},
			)
			error_code = 0
		except requests.exceptions.ProxyError as e:
			print(f"Load {url} Error, Attempt {attempt + 1} failed: {e}")
			time.sleep(1)  # 等待1秒后重试
			error_code = 1
		except requests.exceptions.ConnectTimeout as e:
			print(f"Load {url} Timeout, Attempt {attempt + 1} failed: {e}")
			time.sleep(1)  # 等待1秒后重试
			error_code = 1

		if error_code == 0:
			parsed_feed = feedparser.parse(res.content)
			soup = BeautifulSoup(res.content, 'xml')

			## Update RSS Feed Status
			feed_title = soup.find('title').text if soup.find('title') else 'No title available'
			feeds = {
				"title": feed_title,
				"link": url,
				"status": "Active"
			}

			for entry in parsed_feed.entries:
				if entry.get("published"):
					try:
						# 清理时间字符串中的多余空格
						published_time_str = ' '.join(entry.get("published").split())
						published_time = parser.parse(published_time_str)
					except Exception as e:
						print(f"时间解析错误: {entry.get('published')}, 错误信息: {e}")
						published_time = datetime.now(timezone.utc)
				else:
					published_time = datetime.now(timezone.utc)
				
				# 确保时间有时区信息
				if not published_time.tzinfo:
					published_time = published_time.replace(tzinfo=timezone(timedelta(hours=8)))
				
				# 验证时间是否有效
				if published_time > datetime.now(timezone.utc):
					print(f"警告：发现未来时间 {published_time}，将使用当前时间")
					published_time = datetime.now(timezone.utc)
				
				# 打印每个条目的标题和发布时间
				print(f"解析条目: {entry.get('title')} - 发布时间: {published_time}")
				
				if now - published_time < timedelta(days=load_time):
					# 获取所有图片
					cover = BeautifulSoup(entry.get("summary"),'html.parser')
					all_images = cover.find_all('img')
					
					# 选择最合适的封面图片
					cover_image = "https://www.notion.so/images/page-cover/rijksmuseum_avercamp_1620.jpg"
					if all_images:
						# 优先选择image-wrapper中的图片
						image_wrapper = cover.find('p', class_='image-wrapper')
						if image_wrapper:
							img = image_wrapper.find('img')
							if img and img.get('src'):
								# 使用默认封面图片
								print(f"检测到原始图片URL: {img['src']}，但使用默认图片替代")
						else:
							# 如果没有image-wrapper中的图片，使用第一张图片
							print(f"检测到原始图片URL: {all_images[0]['src']}，但使用默认图片替代")
					
					# 转换HTML内容为Notion块
					notion_blocks = convert_html_to_notion_blocks(entry.get("summary"))
					
					# 计算内容类型
					content_type = get_content_type(entry.get("summary", ""))
					
					entries.append(
						{
							"title": entry.get("title"),
							"link": entry.get("link"),
							"time": published_time.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S%z"),
							"summary": entry.get("summary"),  # 保留原始HTML内容
							"content": entry.get("content"),
							"cover": cover_image,
							"notion_blocks": notion_blocks,  # 添加转换后的Notion块
							"content_type": content_type  # 添加内容类型
						}
					)

			# 打印排序前的条目数量
			print(f"排序前条目数量: {len(entries)}")
			
			# 对 entries 按发布时间进行排序（最新的在前）
			try:
				entries = sorted(entries, key=lambda x: parser.parse(x['time']), reverse=True)
				# 打印排序后的条目标题
				for i, entry in enumerate(entries):
					print(f"排序后条目 {i+1}: {entry['title']} - 发布时间: {entry['time']}")
			except Exception as e:
				print(f"排序时发生错误: {e}")
				# 如果排序失败，保持原始顺序
				pass
			
			# 打印最终返回的条目数量
			print(f"最终返回条目数量: {len(entries[:50])}")
			
			return feeds, entries[:50]
			# return feeds, entries[:3]	
		
	feeds = {
		"title": "Unknown",
		"link": url,
		"status": "Error"
	}

		
	return feeds, None


class NotionAPI:
	NOTION_API_pages = "https://api.notion.com/v1/pages"
	NOTION_API_database = "https://api.notion.com/v1/databases"


	def __init__(self, secret, read, feed) -> None:
		self.reader_id = read
		self.feeds_id = feed
		self.headers = {
			"Authorization": f"Bearer {secret}",
			"Notion-Version": "2022-06-28",
			"Content-Type": "application/json",
		}
		# self.delete_rss()

	def queryFeed_from_notion(self):
		"""
		从URL Database里读取url和page_id

		return:
		dict with "url" and "page_id"
		"""
		rss_feed_list = []
		url=f"{self.NOTION_API_database}/{self.feeds_id}/query"
		payload = {
			"page_size": 100,
			"filter": {
				"property": "Disabled",
				"checkbox": {"equals": False},
			}
		}
		response = requests.post(url, headers=self.headers, json=payload)

		# Check Status
		if response.status_code != 200:
			raise Exception(f"Failed to query Notion database: {response.text}")
		
		# Grab requests
		data = response.json()

		# Dump the requested JSON file for test
		# with open('db.json', 'w', encoding='utf8') as f:
		# 	json.dump(data, f, ensure_ascii=False, indent=4)

		rss_feed_list = []
		for page in data['results']:
			props = page["properties"]
			multi_select = props["Tag"]["multi_select"]
			name_color_pairs = [(item['name'], item['color']) for item in multi_select]
			rss_feed_list.append(
				{
					"url": props["URL"]["url"],
					"page_id": page.get("id"),
					"tags": name_color_pairs
				}
			)

		return rss_feed_list

	def saveEntry_to_notion(self, entry, page_id, tags):
		"""
		Save entry lists into reading database

		params: entry("title", "link", "time", "summary", "notion_blocks", "content_type"), page_id

		return:
		api response from notion
		"""
		# 打印详细信息
		print(f"尝试保存到Notion - 标题: {entry.get('title')}")
		print(f"链接: {entry.get('link')}")
		
		# 封面图片使用默认图片
		cover_image = "https://www.notion.so/images/page-cover/rijksmuseum_avercamp_1620.jpg"
		print(f"封面图片: {cover_image}")
		
		# 检查notion_blocks
		blocks = entry.get("notion_blocks", [])
		print(f"内容块数量: {len(blocks)}")
		if len(blocks) == 0:
			print("警告: 没有内容块!")
		
		# 首先创建页面
		payload = {
			"parent": {"database_id": self.reader_id},
			"cover": {
				"type": "external",
				"external": {"url": cover_image}
			},
			"properties": {
				"Name": {
					"title": [
						{
							"type": "text",
							"text": {"content": entry.get("title")},
						}
					]
				},
				"URL": {"url": entry.get("link")},
				"Published": {"date": {"start": entry.get("time")}},
				"Source":{
					"relation": [{"id": page_id}]
				},
				"Tag": {
					"multi_select": [{"name": tag[0], "color": tag[1]} for tag in tags]
				},
				"Content Type": {
					"select": {
						"name": entry.get("content_type", "简报")
					}
				}
			},
			"children": entry.get("notion_blocks", [])  # 使用转换后的Notion块
		}
		
		res = requests.post(url=self.NOTION_API_pages, headers=self.headers, json=payload)
		print(f"保存结果: 状态码 {res.status_code}")
		if res.status_code != 200:
			print(f"保存失败: {res.text}")
		return res
	
	def saveFeed_to_notion(self, prop, page_id):
		"""
		Update feed info into URL database

		params: prop("title", "status"), page_id

		return:
		api response from notion
		"""

		# Update to Notion
		url = f"{self.NOTION_API_pages}/{page_id}"
		payload = {
			"parent": {"database_id": self.feeds_id},
			"properties": {
				"Feed Name": {
					"title": [
						{
							"type": "text",
							"text": {"content": prop.get("title")},
						}
					]
				},
				"Status":{
					"select":{
						"name": prop.get("status"),
						"color": "red" if prop.get("status") == "Error" else "green"
					}
					
				}
			},
		}

		res = requests.patch(url=url, headers=self.headers, json=payload)
		print(res.status_code)
		return res

	## Todo: figure out deleting process
	# def delete_rss(self):
	# 	filter_json = {
	# 		"filter": {
	# 			"and": [
	# 				{
	# 					"property": "Check",
	# 					"checkbox": {"equals": True},
	# 				},
	# 				{
	# 					"property": "Published",
	# 					"date": {"before": delete_time.strftime("%Y-%m-%dT%H:%M:%S%z")},
	# 				},
	# 			]
	# 		}
	# 	}
	# 	results = requests.request("POST", url=f"{self.NOTION_API_database}/{self.reader_id}/query", headers=self.headers, json=filter_json).json().get("results")
	# 	responses = []
	# 	if len(results) != 0:
	# 		for result in results:
	# 			url = f"https://api.notion.com/v1/blocks/{result.get('id')}"
	# 			responses += [requests.delete(url, headers=self.headers)]
	# 	return responses
	
