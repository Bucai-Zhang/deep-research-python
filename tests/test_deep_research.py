import asyncio
from unittest.mock import patch
from src.deep_research import deep_research



#received_learnings记录每次调用时传入的研究发现。
received_learnings = []
searched_queries = []

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
    searched_queries.append(query)
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

    assert result["learnings"] == [
        "发现A",
        "发现A1",
        "发现B",
        "发现B1"
    ], "depth ==2 最终研究发现汇总错误"

    assert received_learnings == [
        [],
        ["发现A"],
        ["发现B"]
    ], "depth ==2 递归分支隔离测试失败"

    assert result["sources"] == [
        "url_A",
        "url_A1",
        "url_B",
        "url_B1"
    ], "depth ==2 最终研究来源汇总错误"

    assert searched_queries == [
        "A",
        "A1",
        "B",
        "B1"
    ]," depth ==2 搜索查询顺序错误"

    print(result)
    print(received_learnings)

    received_learnings.clear()
    searched_queries.clear()

    result_depth1 = asyncio.run(
        deep_research("AI Agent", breadth=2, depth=1)
    )

    assert result_depth1["learnings"] == [
        "发现A", "发现B"
    ], "depth ==1 最终研究发现汇总错误"

    assert result_depth1["sources"] == [
        "url_A", "url_B"
    ], "depth ==1 最终研究来源汇总错误"

    assert searched_queries == [
        "A",
        "B"
    ]," depth ==1 搜索查询顺序错误"

    assert received_learnings == [
        [],
    ], "depth ==1 递归分支隔离测试失败"

    print(result_depth1)
    print(received_learnings)

    received_learnings.clear()
    searched_queries.clear()

    result_depth0 = asyncio.run(
        deep_research(
            "AI Agent",
            breadth=2,
            depth=0,
            learnings=["已有发现"],
            sources=["已有来源"]
        )
    )

    assert result_depth0["learnings"] ==[
        "已有发现"
    ], "depth ==0 最终研究发现汇总错误"

    assert result_depth0["sources"] == [
        "已有来源"
    ], "depth=0 时研究来源保留错误"

    assert received_learnings == [],"depth ==0 递归分支隔离测试失败"

    assert searched_queries == [],"depth ==0 搜索查询顺序错误"

