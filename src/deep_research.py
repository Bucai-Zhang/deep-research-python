import asyncio
from firecrawl import CrawlJobTimeoutError

from src.search_queries import generate_search_queries
from src.search import search_web
from src.process_result import process_serp_result
from openai import (
    APIConnectionError, #接口连接错误
    RateLimitError,     #请求限流错误
    InternalServerError #服务器内部错误
)

#AllBranchesFailedError 继承自 RuntimeError，属于更加具体的异常类型
class AllBranchesFailedError(RuntimeError):
    pass

RECOVERABLE_ERRORS = (
    TimeoutError, ConnectionError,
    APIConnectionError, RateLimitError,
    InternalServerError
)

async def deep_research(
        query,
        breadth=4,
        depth = 2,
        learnings = None,
        sources = None,
        search_semaphore = None,
        model_semaphore = None
):
    #必须让所有递归层共享同一个搜索信号量
    if search_semaphore is None:
        search_semaphore = asyncio.Semaphore(2)

    if model_semaphore is None:
        model_semaphore = asyncio.Semaphore(2)

    if learnings is None:
        learnings=[]

    if sources is None:
        sources=[]

    if depth <= 0:
        return {
            "learnings": learnings,
            "sources": sources
        }

    print(f"\nResearch depth remaining: {depth}")
    print(f"Research breadth: {breadth}")

    async with model_semaphore:
        search_queries = await generate_search_queries(
            query,
            breadth,
            learnings=learnings
        )

    base_learnings = learnings.copy()
    all_learnings = learnings.copy()

    base_sources = sources.copy()
    all_sources = sources.copy()

    #将子分支搜索合并成一个函数，方便后续调用
    async def research_branch(item):
        search_query = item["query"]
        research_goal = item["research_goal"]

        branch_learnings = base_learnings.copy()
        branch_sources = base_sources.copy()

        print(f"\nSearching: {search_query}")

        async with search_semaphore:
            search_result = await search_web(search_query)

        #processed_results返回learnings follow_up_questions sources
        async with model_semaphore:
            processed_results = await process_serp_result(
                search_query,
                search_result
            )

        new_learnings = processed_results["learnings"]
        follow_up_questions = processed_results["follow_up_questions"]
        new_sources = processed_results["sources"]

        branch_learnings.extend(new_learnings)
        branch_sources.extend(new_sources)

        #下一层的query是由这一层的research_goal和follow_up_questions组成的
        if depth > 1 and follow_up_questions:
            next_query = (
                f"Previous research goal: {research_goal}\n"
                f"Follow-up questions:\n"
                 + '\n'.join(follow_up_questions)
             )

            next_breadth = max(1,breadth // 2)

            try:
                recursive_result = await deep_research(
                     query = next_query,
                     breadth = next_breadth,
                     depth = depth - 1,
                     learnings = branch_learnings,
                     sources = branch_sources,
                     search_semaphore = search_semaphore,
                    model_semaphore=model_semaphore
                )
            except AllBranchesFailedError:
                print(f"{search_query} 后续研究失败，保留已有发现")
            else:
                branch_learnings = recursive_result["learnings"]
                branch_sources = recursive_result["sources"]

        return {
            "learnings": branch_learnings,
            "sources": branch_sources
        }

    tasks = [
        research_branch(item)
        for item in search_queries
    ]
    #return_exceptions=True 的含义是：把普通任务异常也放入返回结果列表，而不是立刻向外抛出。
    branch_results = await asyncio.gather(
        *tasks,
        return_exceptions=True
    )

    success_count = 0

    for item, result in zip(search_queries, branch_results):
        #取消异常向上传递，普通异常暂时记录并跳过。
        #假设用户主动取消 DeepResearch，但程序却把取消当作普通失败，然后继续执行研究，这通常不是我们想要的行为。
        if isinstance(result, asyncio.CancelledError):
            raise result
        if isinstance(result, Exception):
            if isinstance(result, RECOVERABLE_ERRORS):
                print(f"分支 {item['query']} 失败: {result}")
                continue
            raise result

        success_count += 1
        all_learnings.extend(result["learnings"])
        all_sources.extend(result["sources"])

    if search_queries and success_count == 0:
        raise AllBranchesFailedError("所有研究分支均失败")


    return {
        "learnings": list(dict.fromkeys(all_learnings)),
        "sources": list(dict.fromkeys(all_sources))
    }

