import feedparser
from bs4 import BeautifulSoup

import re
import json
import requests
from datetime import datetime, timezone, timedelta
from dateutil import parser
import time
import io
from urllib.parse import urlparse
import base64

now = datetime.now(timezone.utc)
load_time = 60  # 导入60天内的内容

def download_and_encode_image(image_url):
	"""
	下载图片并转换为 base64 编码
	"""
	print(f"\n开始处理图片: {image_url}")
	try:
		response = requests.get(image_url, timeout=10)
		print(f"图片下载状态码: {response.status_code}")
		if response.status_code == 200:
			# 获取图片的 MIME 类型
			content_type = response.headers.get('content-type', 'image/jpeg')
			print(f"图片类型: {content_type}")
			# 将图片内容转换为 base64
			image_data = base64.b64encode(response.content).decode('utf-8')
			print(f"图片大小: {len(image_data)} bytes")
			return {
				'type': 'file',
				'file': {
					'url': f'data:{content_type};base64,{image_data}'
				}
			}
		else:
			print(f"图片下载失败，状态码: {response.status_code}")
	except Exception as e:
		print(f"下载图片失败: {image_url}, 错误: {str(e)}")
	return None

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
					published_time = parser.parse(entry.get("published"))
				else:
					published_time = datetime.now(timezone.utc)
				if not published_time.tzinfo:
					published_time = published_time.replace(tzinfo=timezone(timedelta(hours=8)))
				if now - published_time < timedelta(days=load_time):
					# 处理HTML内容
					content = BeautifulSoup(entry.get("summary"), 'html.parser')
					
					# 处理HTML实体
					content_text = content.get_text()
					content_text = content_text.replace('&nbsp;', ' ')
					
					# 将HTML标签转换为换行
					for tag in content.find_all(['p', 'div', 'br']):
						tag.replace_with(tag.get_text() + '\n\n')
					
					# 获取处理后的文本
					formatted_content = content.get_text()
					
					# 清理多余的空白字符，但保留段落间的换行
					formatted_content = re.sub(r'\n\s*\n\s*\n', '\n\n', formatted_content)
					formatted_content = formatted_content.strip()
					
					# 处理图片
					cover_list = content.find_all('img')
					print(f"\n找到 {len(cover_list)} 个图片标签")
					src = None
					if cover_list:
						img_src = cover_list[0].get('src', '')
						print(f"原始图片链接: {img_src}")
						# 处理相对路径
						if img_src.startswith('//'):
							img_src = 'https:' + img_src
							print(f"处理协议相对路径后的链接: {img_src}")
						elif img_src.startswith('/'):
							# 从 entry.link 中提取域名
							parsed_url = urlparse(entry.get("link", ""))
							base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
							img_src = base_url + img_src
							print(f"处理根相对路径后的链接: {img_src}")
						
						# 下载并编码图片
						src = download_and_encode_image(img_src)
						if src:
							print("图片处理成功")
						else:
							print("图片处理失败")
					else:
						print("未找到图片标签")
					
					entries.append(
						{
							"title": entry.get("title"),
							"link": entry.get("link"),
							"time": published_time.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S%z"),
							"summary": formatted_content[:2000],
							"content": entry.get("content"),
							"cover": src
						}
					)

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

		params: entry("title", "link", "time", "summary"), page_id

		return:
		api response from notion
		"""
		# 构建基本属性
		payload = {
			"parent": {"database_id": self.reader_id},
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
				}
			},
			"children": [
				{
					"type": "paragraph",
					"paragraph": {
						"rich_text": [
							{
								"type": "text",
								"text": {"content": entry.get("summary")},
							}
						]
					},
				}
			],
		}

		# 如果有封面图片，添加封面属性
		cover_data = entry.get("cover")
		if cover_data:
			payload["cover"] = cover_data

		res = requests.post(url=self.NOTION_API_pages, headers=self.headers, json=payload)
		print(res.status_code)
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
	
