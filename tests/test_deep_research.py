import asyncio
from unittest.mock import patch
from src.deep_research import deep_research



#received_learnings记录每次调用时传入的研究发现。
received_learnings = []

async def fake_generate_search_queries(query, breadth, learnings=None):
    received_learnings.append(learnings.copy())

    if query == "AI Agent":
        return [
            {"query": "A", "research_goal": "研究A"},
            {"query": "B", "research_goal": "研究B"}
        ][:breadth]

    elif "研究A" in query :
        return [
            {"query": "A1", "research_goal": "研究A1"},
        ][:breadth]

    elif "研究B" in query :
        return [
            {"query": "B1", "research_goal": "研究B1"},
        ][:breadth]



#避免模拟函数在输入错误时悄悄返回 None
    else:
        raise ValueError(f"Unexpected research query: {query}")

"""
        breadth=1：只返回搜索词 A。
        breadth=2：返回搜索词 A 和 B。
        
"""



async def fake_search_web(query):
    return {"query": query}



async def fake_process_serp_result(
        search_query,
        search_result
):
    if search_query == "A":
        return {
            "learnings": ["发现A"]    ,
            "follow_up_questions": ["深入研究A的问题"],
            "sources": ["url_A"]
        }
    if search_query == "B":
        return {
            "learnings": ["发现B"],
            "follow_up_questions": ["深入研究B的问题"],
            "sources": ["url_B"]
        }

    if search_query == "A1":
        return {
            "learnings": ["发现A1"],
            "follow_up_questions": [],
            "sources": ["url_A1"]
        }

    if search_query == "B1":
        return {
            "learnings": ["发现B1"],
            "follow_up_questions": [],
            "sources": ["url_B1"]
        }

    raise ValueError(
        f"Unexpected search query: {search_query}"
    )


with (
    patch("src.deep_research.generate_search_queries", new=fake_generate_search_queries),
    patch("src.deep_research.search_web", new=fake_search_web),
    patch("src.deep_research.process_serp_result", new=fake_process_serp_result)
):
    result = asyncio.run(
        deep_research("AI Agent", breadth=2, depth=2)
    )

    print(result)
    print(received_learnings)
