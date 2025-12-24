import json


NEW_METADATA_OUTPUT_FILE = "result.json"
REWRITE_OUTPUT_FILE = "rewrite.json"
BASE_URL = "https://senjianlu.com"


def main():
    # 读取 result.json
    with open(NEW_METADATA_OUTPUT_FILE, 'r', encoding='utf-8') as f:
        post_id_2_metadata = json.load(f)
    
    # 生成重写字典
    rewrite_dict = {}
    for post_id, metadata in post_id_2_metadata.items():
        origin_url = metadata.get('origin_url', '')
        if not origin_url:
            continue
        category = metadata.get('category', '')
        slug = metadata.get('slug', '')
        alias_urls = [f"{BASE_URL}/{alias}" for alias in metadata.get('alias', [])]
        new_url = f"{BASE_URL}/posts/articles/{category}/{slug}/"
        all_origin_urls = [origin_url] + alias_urls
        for url in all_origin_urls:
            old_uri = url.replace(BASE_URL, '').rstrip('/')
            new_uri = new_url.replace(BASE_URL, '')
            rewrite_dict[old_uri] = {
                "status": 302,
                "destination": new_uri
            }
    
    # 保存到 rewrite.json
    with open(REWRITE_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(rewrite_dict, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()