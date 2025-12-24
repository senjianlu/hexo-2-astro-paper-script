import os
import json
import yaml
import requests
from xml.etree import ElementTree as ET


PATH = "./blog-posts-master/posts/"
ERROR_POSTS_FILE = "error.log"
ORIGIN_BLOG_SITEMAP_URL = "https://senjianlu.com/sitemap.xml"
NEW_METADATA_OUTPUT_FILE = "result.json"


def _load_origin_hexo_article_metadata(file_path) -> dict | None:
    """
    加载文章的元数据 (Front Matter)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # 检查是否有 Front Matter
    if not content.startswith('---\n'):
        return None
    # 找到第二个 --- 的位置
    try:
        end_index = content.index('\n---', 4)
        yaml_content = content[4:end_index]
        # 使用 yaml.safe_load 解析（比 yaml.load 更安全）
        metadata = yaml.safe_load(yaml_content)
        return metadata if metadata else None
    except ValueError:
        # 没有找到结束的 ---
        print(f"无法找到结束的 --- in {file_path}")
        # print(content)
        return None
    except yaml.YAMLError as e:
        print(f"YAML 解析错误 in {file_path}: {e}")
        return None

def _generate_new_astro_article_metadata(old_metadata: dict, category: str, post_id: str) -> dict:
    """
    根据旧的 Hexo 文章元数据生成新的 Astro 文章元数据
    """
    new_metadata = {}
    # 文章标题
    if 'title' in old_metadata:
        new_metadata['title'] = old_metadata['title']
    # 文章发布时间
    if 'date' in old_metadata:
        if isinstance(old_metadata['date'], str):
            new_metadata['pubDatetime'] = old_metadata['date']
        else:
            # 东八区
            new_metadata['pubDatetime'] = old_metadata['date'].strftime('%Y-%m-%d %H:%M:%S')
    # 文章最后修改时间
    if 'updated' in old_metadata and old_metadata['updated']:
        if isinstance(old_metadata['updated'], str):
            new_metadata['updateDatetime'] = old_metadata['updated']
        else:
            # 东八区
            new_metadata['updateDatetime'] = old_metadata['updated'].strftime('%Y-%m-%d %H:%M:%S')
    else:
        # 如果没有更新日期，则使用发布时间作为最后修改时间
        new_metadata['updateDatetime'] = new_metadata.get('pubDatetime', '')
    # 文章标签
    if 'tags' in old_metadata:
        new_metadata['tags'] = old_metadata['tags']
    # 文章分类
    if 'categories' in old_metadata:
        new_metadata['categories'] = old_metadata['categories']
    # 文章目录显示
    if 'toc' in old_metadata:
        new_metadata['toc'] = old_metadata['toc']
    # 文章缩略图
    if 'thumbnail' in old_metadata:
        new_metadata['thumbnail'] = old_metadata['thumbnail']
    # 文章别名
    if 'alias' in old_metadata:
        new_metadata['alias'] = old_metadata['alias']
    # 文章链接别名
    new_metadata['slug'] = post_id.replace('_', '-')
    # 文章作者
    new_metadata['author'] = 'Kyo'
    # 文章语言
    new_metadata['lang'] = 'zh-CN'
    # 文章描述
    new_metadata['description'] = ""
    # 文章是否置顶
    new_metadata['isTop'] = False
    # 文章是否为草稿
    if 'published' in old_metadata:
        new_metadata['draft'] = not old_metadata['published']
    # 文章分类（目录结构）
    new_metadata['category'] = category
    return new_metadata


def main():
    # 1. 读取 PATH 下的 .md 文件
    markdown_file_paths = []
    for root, dirs, files in os.walk(PATH):
        # 只处理 PATH 本身和它的直接子目录
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                markdown_file_paths.append(file_path)
    
    # 2. 处理每个 Markdown 文件
    new_post_id_2_metadata = {}
    # 清空错误日志文件
    with open(ERROR_POSTS_FILE, 'w', encoding='utf-8') as error_file:
        error_file.write("")
    # 遍历所有 Markdown 文件
    for file_path in markdown_file_paths:
        if os.path.isfile(file_path):
            category = os.path.relpath(os.path.dirname(file_path), PATH)
            file_name = os.path.basename(file_path)
            # print(f"分类: {category}, 文件名: {file_name}")
            old_metadata = _load_origin_hexo_article_metadata(file_path)
            # 3. 生成新的 Astro 文章元数据
            if not old_metadata:
                with open(ERROR_POSTS_FILE, 'a', encoding='utf-8') as error_file:
                    error_file.write(f"无法解析元数据: {file_path}\n")
                continue
            else:
                post_id = file_name.replace('.md', '')
                new_metadata = _generate_new_astro_article_metadata(
                    old_metadata,
                    category=category,
                    post_id=post_id
                )
                if not new_metadata:
                    with open(ERROR_POSTS_FILE, 'a', encoding='utf-8') as error_file:
                        error_file.write(f"无法生成新元数据: {file_path}\n")
                    continue
                if post_id in new_post_id_2_metadata:
                    with open(ERROR_POSTS_FILE, 'a', encoding='utf-8') as error_file:
                        error_file.write(f"重复的文章 ID: {post_id}, 文件路径: {file_path}\n")
                    continue
                else:
                    new_post_id_2_metadata[post_id] = new_metadata
    
    # 3. 读取旧博客的 sitemap.xml，获取所有文章的 URL 列表
    old_post_id_2_url = {}
    response = requests.get(ORIGIN_BLOG_SITEMAP_URL)
    if response.status_code != 200:
        print(f"无法获取 sitemap.xml: {response.status_code}")
        return
    sitemap_content = response.text
    # 解析 sitemap.xml，提取所有文章 URL
    from xml.etree import ElementTree as ET
    root = ET.fromstring(sitemap_content)
    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    url_elements = root.findall('ns:url', namespace)
    origin_article_urls = [url_elem.find('ns:loc', namespace).text for url_elem in url_elements]
    # 如果包含 404.html、index.html、/categories/、/tags/ 等非文章页面，则过滤掉
    origin_article_urls = [url for url in origin_article_urls if all(x not in url for x in ['404.html', 'index.html', '/categories/', '/tags/'])]
    origin_article_urls = [url for url in origin_article_urls if len(url.split('/')) > 4]  # 过滤掉非文章页面
    origin_article_urls_set = set(origin_article_urls)
    for origin_article_url in origin_article_urls_set:
        post_id = origin_article_url.rstrip('/').split('/')[-1]
        old_post_id_2_url[post_id] = origin_article_url
    
    # 4. 相匹配的有多少个
    print(f"总共找到 {len(new_post_id_2_metadata)} 篇迁移文章元数据。")
    print(f"总共找到 {len(old_post_id_2_url)} 篇旧博客文章 URL。")
    matched_count = 0
    for post_id in old_post_id_2_url.keys():
        if post_id in new_post_id_2_metadata:
            matched_count += 1
    print(f"成功匹配到 {matched_count} 篇文章元数据。")
    print(f"未匹配到 {len(old_post_id_2_url) - matched_count} 篇文章元数据。")
    for post_id in old_post_id_2_url.keys():
        if post_id not in new_post_id_2_metadata:
            with open(ERROR_POSTS_FILE, 'a', encoding='utf-8') as error_file:
                error_file.write(f"未匹配到文章元数据: {post_id}, URL: {old_post_id_2_url[post_id]}\n")
    # 不匹配的不发布
    for post_id in new_post_id_2_metadata.keys():
        if post_id not in old_post_id_2_url:
            new_post_id_2_metadata[post_id]['draft'] = True
        else:
            new_post_id_2_metadata[post_id]['draft'] = False
            new_post_id_2_metadata[post_id]['origin_url'] = old_post_id_2_url[post_id]
            if new_post_id_2_metadata[post_id]['category'].startswith('_'):
                print(f"警告: 文章分类以 _ 开头: {post_id}, 分类: {new_post_id_2_metadata[post_id]['category']}")
    
    # 5. 输出新的文章元数据到文件
    with open(NEW_METADATA_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_post_id_2_metadata, f, ensure_ascii=False, indent=4)
                


if __name__ == "__main__":
    main()