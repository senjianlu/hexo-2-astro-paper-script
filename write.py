import re
import os
import json
import yaml


PATH = "./blog-posts-master/posts/"
NEW_PATH = "../src/data/blog/articles/"
NEW_METADATA_OUTPUT_FILE = "result.json"
DESC_FILE = "desc.json"


def main():
    # 读取已有的元数据和描述数据
    post_id_2_metadata = {}
    post_id_2_desc = {}
    with open(NEW_METADATA_OUTPUT_FILE, 'r', encoding='utf-8') as f:
        post_id_2_metadata = json.load(f)
    with open(DESC_FILE, 'r', encoding='utf-8') as f:
        post_id_2_desc = json.load(f)

    # 遍历文章，写入新的 Astro 文章文件
    for post_id, metadata in post_id_2_metadata.items():
        slug = metadata.get("slug", '')
        file_path = os.path.join(PATH, metadata.get("category", ""), f"{post_id}.md")
        new_file_path = os.path.join(NEW_PATH, metadata.get("category", ""), f"{slug}.md")
        if not os.path.exists(file_path):
            print(f"文章文件 {file_path} 不存在，跳过写入。")
            continue
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        article_metadata = metadata.copy()
        article_metadata["description"] = post_id_2_desc.get(post_id, "")
        # 读取原文章中出了 metadata 之外的内容
        if '---' in content and content.count('---') >= 2:
            content_parts = content.split('---', 2)
            body_content = content_parts[2].lstrip('\n')
            metadata_content = yaml.safe_dump(article_metadata, allow_unicode=True)
            # 去掉 pubDatetime 和 updateDatetime 字段的值的引号，值的两边不能有引号，使用正则替换
            metadata_content = re.sub(r'^(pubDatetime|updateDatetime):\s*[\'"](.+?)[\'"]\s*$', r'\1: \2', metadata_content, flags=re.MULTILINE)
            # 去掉 desc 后的双引号
            # metadata_content = re.sub(r'^(description):\s*"(.*)"\s*$', lambda m: f'{m.group(1)}: {m.group(2)}', metadata_content, flags=re.MULTILINE)
            # 构造新的 Astro 文章内容
            new_article_content = f"---\n{metadata_content}\n---\n\n{body_content}"
            # 确保目录存在
            os.makedirs(os.path.dirname(new_file_path), exist_ok=True)
            # 写入新的文章文件
            with open(new_file_path, 'w', encoding='utf-8') as new_f:
                new_f.write(new_article_content)
            print(f"文章文件 {new_file_path} 写入完成。")
        else:
            print(f"文章文件 {file_path} 格式异常，跳过写入。")


if __name__ == "__main__":
    main()