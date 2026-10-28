#文本处理模块

import jieba.analyse


def split_text(text,chunk_size= 2000,overlap = 200):
    chunks=[]

    if not 0 <= overlap < chunk_size:
        raise ValueError("Overlap must be between 0 and chunk_size")

    for i in range(0,len(text),chunk_size - overlap):
        chunks.append(text[i:i+chunk_size])
    return chunks


def score_chunk(chunk,keywords):
    score = 0

    # 遍历 keywords
    # 统计每个关键词在 chunk 中出现的次数
    # 将次数累加到 score
    for keyword in keywords:
        score += chunk.count(keyword)

    return score



#该函数作用是根据评分来选出最终需要的文档快
def select_chunks(chunks,keywords,max_chunks=3):
#这里对下标进行排序，不对chunk进行排序，目的是防止打乱原文顺序序
        ranked_indices = sorted(
            range(len(chunks)),
            key=lambda i: score_chunk(chunks[i], keywords),
            reverse=True
        )
#这里又进行了一次排序，目的是恢复原来的文章顺序
        selected_indices = sorted(ranked_indices[:max_chunks])

        return [chunks[i] for i in selected_indices]


def extract_keywords(query, top_k=5):
    keywords = jieba.analyse.extract_tags(query, topK=top_k,withWeight=True)
    stopwords = {"哪些", "什么", "如何", "领域", "方面"}
    return [word for word,weight in keywords if word not in stopwords]


#实现了创建候选块并且对每个块补充信息
def build_candidates(text,url,keywords):
    candidates = []
    for i,item in enumerate(split_text(text)):
        candidate = {
            "index": i,
            "text": item,
            "url": url,
            "score": score_chunk(item, keywords)
        }
        candidates.append(candidate)

    return candidates


#对所有网页进行全局筛选，并且分轮挑选，第一轮不能挑选重复网址保证结果能遍及到尽量多的网址，剩下的可以重复网址，保证结果的质量
def select_global_candidates(candidates, max_chars=6000):

    ranked = sorted(
        candidates,
        key=lambda c: c["score"],
        reverse=True
    )

    selected = []
    used_chars = 0
    selected_urls = set()

#第一轮筛选，保证同一个网址下的candidate块不能出现两次，保证结果广泛性
    for candidate in ranked:
        size = len(candidate["text"])
        url = candidate["url"]

        if used_chars + size <= max_chars and url not in selected_urls:
            selected.append(candidate)
            selected_urls.add(url)
            used_chars += size

#第二轮筛选，分高者被选
    for candidate in ranked:
        size = len(candidate["text"])

        if candidate not in selected and used_chars + size <= max_chars:
            selected.append(candidate)
            used_chars += size

    return selected




if __name__=="__main__":
    """
    query = "人工智能在医疗领域有哪些风险？"
    text = "人工智能提高效率。误诊风险需要注意。患者隐私存在风险。"
    chunks = split_text(text,12,2)
    keywords = extract_keywords(query, 5)
    print("关键词：", keywords)
    print("分块：", chunks)
    print("排序：", select_chunks(chunks, keywords, 2))

"""
    candidates = [
        {"text": "A" * 2000, "score": 10, "url": "A", "index": 0},
        {"text": "A" * 2000, "score": 9, "url": "A", "index": 1},
        {"text": "B" * 2000, "score": 8, "url": "B", "index": 0},
        {"text": "C" * 2000, "score": 7, "url": "C", "index": 0},
    ]

    selected = select_global_candidates(candidates, 6000)

    for item in selected:
        print(item["url"], item["score"], len(item["text"]))