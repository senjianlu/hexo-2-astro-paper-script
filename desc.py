# Please install OpenAI SDK first: `pip3 install openai`
import os
import json
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI


PATH = "./blog-posts-master/posts/"
DEEPSEEK_API_KEY = "sk-0e8ec0713d7f4xxxxxxxxxxxxxxxxx"
NEW_METADATA_OUTPUT_FILE = "result.json"
DESC_FILE = "desc.json"
MAX_WORKERS = 10  # 默认线程数

# 线程锁，用于保护文件写入
file_lock = threading.Lock()
# 进度计数器
progress_lock = threading.Lock()
completed_count = 0
total_count = 0


def load_desc_data():
    """加载已有的描述数据"""
    if not os.path.exists(DESC_FILE):
        with open(DESC_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        return {}
    with open(DESC_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_desc_data(post_id, description):
    """保存描述数据到文件（线程安全）"""
    global completed_count
    with file_lock:
        post_id_2_desc = load_desc_data()
        post_id_2_desc[post_id] = description
        with open(DESC_FILE, 'w', encoding='utf-8') as f:
            json.dump(post_id_2_desc, f, ensure_ascii=False, indent=4)
    
    # 更新进度
    with progress_lock:
        completed_count += 1
        print(f"进度: {completed_count}/{total_count} - 文章 {post_id} 描述生成完成")


def generate_description(post_id, metadata, client):
    """为单篇文章生成描述"""
    try:
        # 检查是否为草稿
        if metadata.get("draft", False):
            print(f"文章 {post_id} 为草稿，跳过描述生成。")
            return None
        
        # 获取文章内容
        title = metadata.get('title', '')
        content_file_path = os.path.join(PATH, metadata.get("category", ""), f"{post_id}.md")
        
        if not os.path.exists(content_file_path):
            print(f"文章文件 {content_file_path} 不存在，跳过描述生成。")
            return None
        
        with open(content_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 调用 DeepSeek API 生成描述
        prompt = """请你为下面的文章生成描述，需求：
1. 50 ~ 80 个汉字
2. 以第一人称（我）来描述文章内容和初衷，但是不要使用“我”字眼
3. 措辞谦逊，不要使用类似详细讲解、全面介绍、深度剖析等过于自信的词汇
4. 不要和标题的内容重复，描述要补充标题没有提到的信息（例如如果是每日练习，就不要说这是哪天的练习了）
5. 符合中英文书写的最佳实践（空格、符号和大小写等）绝对注意汉字与英文、数字之间要有空格
6. SEO 友好
"""
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的内容摘要生成助手。"
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\n标题: {title}\n\n内容: {content}"
                }
            ],
            stream=False
        )
        
        description = response.choices[0].message.content.strip()
        print(f"文章 {post_id}: {description}")
        
        # 保存描述
        save_desc_data(post_id, description)
        return description
        
    except Exception as e:
        print(f"生成文章 {post_id} 描述时出错: {str(e)}")
        return None


def main():
    global total_count, completed_count
    
    # 1. 遍历 result.json，读取每篇文章的数据
    if not os.path.exists(NEW_METADATA_OUTPUT_FILE):
        print(f"{NEW_METADATA_OUTPUT_FILE} 不存在，请先运行迁移脚本生成该文件。")
        return
    
    with open(NEW_METADATA_OUTPUT_FILE, 'r', encoding='utf-8') as f:
        new_post_id_2_metadata = json.load(f)
    
    # 2. 加载已生成的描述
    existing_desc = load_desc_data()
    
    # 3. 筛选需要生成描述的文章
    pending_posts = []
    for post_id, metadata in new_post_id_2_metadata.items():
        if post_id not in existing_desc:
            pending_posts.append((post_id, metadata))
    
    total_count = len(pending_posts)
    
    if total_count == 0:
        print("所有文章的描述已生成完成，无需重新生成。")
        return
    
    print(f"共有 {total_count} 篇文章待生成描述，使用 {MAX_WORKERS} 个线程并发处理...\n")
    
    # 4. 初始化 OpenAI 客户端（每个线程一个）
    def create_client():
        return OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
    
    # 5. 使用线程池并发生成描述
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 为每个任务创建独立的客户端
        futures = {
            executor.submit(generate_description, post_id, metadata, create_client()): post_id 
            for post_id, metadata in pending_posts
        }
        
        # 等待所有任务完成
        for future in as_completed(futures):
            post_id = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"处理文章 {post_id} 时发生异常: {str(e)}")
    
    print(f"\n所有文章描述生成完成！共处理 {completed_count}/{total_count} 篇文章。")


if __name__ == "__main__":
    main()