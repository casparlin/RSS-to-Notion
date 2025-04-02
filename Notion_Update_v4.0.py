# coding=utf-8

import os
from Util.FeedTool import NotionAPI, parse_rss_entries
import requests


# 从环境变量中获取Notion API信息
NOTION_API_KEY = os.getenv('NOTION_API_KEY')
NOTION_READING_DATABASE_ID = os.getenv('NOTION_READING_DATABASE_ID')
NOTION_URL_DATABASE_ID = os.getenv('NOTION_URL_DATABASE_ID')

def update():

	if NOTION_API_KEY is None:
		print("NOTION_SEC secrets is not set!")
		return

	api = NotionAPI(NOTION_API_KEY, NOTION_READING_DATABASE_ID, NOTION_URL_DATABASE_ID)

	rss_feed_list = api.queryFeed_from_notion()
	print(f"获取到 {len(rss_feed_list)} 个RSS源")

	for rss_feed in rss_feed_list:
		print(f"\n处理RSS源: {rss_feed.get('url')}")
		feeds, entries = parse_rss_entries(rss_feed.get("url"))
		rss_page_id = rss_feed.get("page_id")
		if entries is None or len(entries) == 0:
			print("没有获取到任何条目")
			api.saveFeed_to_notion(feeds, page_id=rss_page_id)
			continue
		
		print(f"解析到 {len(entries)} 条内容")
		
		# Check for Repeat Entries
		url=f"{api.NOTION_API_database}/{api.reader_id}/query"
		payload = {
			"filter": {
				"property": "Source",
				"relation": {"contains": rss_page_id},
			},
		}
		response = requests.post(url=url, headers=api.headers, json=payload)

		current_urls = [x.get("properties").get("URL").get("url") for x in response.json().get("results")]
		print(f"Notion数据库中已存在 {len(current_urls)} 条该源的URL")
		
		# 特定文章检查
		target_title = "当人工智能大展遇到网红文创园 科技文化融合迸发新质生产力"
		target_entries = [e for e in entries if e.get("title") == target_title]
		if target_entries:
			target_entry = target_entries[0]
			target_link = target_entry.get("link")
			print(f"\n特定检查 - 目标文章: {target_title}")
			print(f"特定检查 - 链接: {target_link}")
			print(f"特定检查 - 链接是否已存在: {target_link in current_urls}")
			if target_link in current_urls:
				print(f"特定检查 - 找到的匹配URL: {[url for url in current_urls if target_link in url]}")
		
		repeat_flag = 0
		added_count = 0

		rss_tags = rss_feed.get("tags")
		api.saveFeed_to_notion(feeds, page_id=rss_page_id)
		
		for i, entry in enumerate(entries):
			print(f"\n处理第 {i+1}/{len(entries)} 条: {entry.get('title')}")
			if entry.get("link") not in current_urls:
				print(f"保存到Notion: {entry.get('title')}")
				api.saveEntry_to_notion(entry, rss_page_id, rss_tags)
				current_urls += [entry.get("link")]
				added_count += 1
			else:
				print(f"跳过重复内容: {entry.get('title')}")
				repeat_flag += 1

		print(f"\n读取到 {len(entries)} 篇内容，其中重复 {repeat_flag} 篇，新增 {added_count} 篇。")



if __name__ == "__main__":
	update()